#!/usr/bin/env python3
import concurrent.futures
import json
import os
import hmac
import secrets
import subprocess
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('HOSTS_FILE', str(BASE / 'hosts.json')))
INDEX = BASE / 'index.html'
HOST = '0.0.0.0'
PORT = 9301
SETTINGS_PASSWORD = os.environ.get('SETTINGS_PASSWORD', '')
SESSION_TTL = 600
SESSIONS = {}
INTERNET_TARGETS = [
    {'name': 'Cloudflare DNS', 'target': '1.1.1.1'},
    {'name': 'Google DNS', 'target': '8.8.8.8'},
]


def ensure_data_file():
    DATA.parent.mkdir(parents=True, exist_ok=True)
    if not DATA.exists():
        DATA.write_text('[]\n', encoding='utf-8')


def load_hosts():
    ensure_data_file()
    try:
        data = json.loads(DATA.read_text(encoding='utf-8'))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_hosts(hosts):
    ensure_data_file()
    DATA.write_text(json.dumps(hosts, ensure_ascii=False, indent=2), encoding='utf-8')


def ping_target(target):
    start = time.time()
    proc = subprocess.run(['ping', '-c', '1', '-W', '1', target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    latency = round((time.time() - start) * 1000)
    return proc.returncode == 0, latency


def enrich_hosts(hosts):
    def check(h):
        online, latency = ping_target(h['target'])
        return {
            **h,
            'online': online,
            'latencyMs': latency if online else None,
            'checkedAt': int(time.time())
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
        return list(ex.map(check, hosts))


def get_internet_status():
    checks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(INTERNET_TARGETS)) as ex:
        futures = {ex.submit(ping_target, item['target']): item for item in INTERNET_TARGETS}
        for future, item in futures.items():
            online, latency = future.result()
            checks.append({
                'name': item['name'],
                'target': item['target'],
                'online': online,
                'latencyMs': latency if online else None,
            })

    return {
        'online': any(item['online'] for item in checks),
        'checkedAt': int(time.time()),
        'checks': checks,
    }


def valid_settings_session(handler):
    cookie = handler.headers.get('Cookie', '')
    token = ''
    for part in cookie.split(';'):
        key, _, value = part.strip().partition('=')
        if key == 'net_pulse_settings':
            token = value
            break
    expires = SESSIONS.get(token)
    if not expires:
        return False
    if expires < time.time():
        SESSIONS.pop(token, None)
        return False
    return True


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, code=200):
        raw = json.dumps(payload).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path in ['/', '/index.html']:
            raw = INDEX.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(raw)
            return
        if self.path == '/icon.svg':
            raw = (BASE / 'icon.svg').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'image/svg+xml')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if self.path == '/apple-touch-icon.png':
            raw = (BASE / 'apple-touch-icon.png').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if self.path == '/api/settings/status':
            self.send_json({'unlocked': valid_settings_session(self)})
            return
        if self.path == '/api/hosts':
            self.send_json({'hosts': enrich_hosts(load_hosts())})
            return
        if self.path == '/api/internet':
            self.send_json(get_internet_status())
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/settings/unlock':
            if not SETTINGS_PASSWORD:
                self.send_json({'error': 'Settings password is not configured'}, 503)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                data = json.loads(self.rfile.read(length).decode('utf-8'))
                supplied = str(data.get('password', ''))
            except Exception:
                supplied = ''
            if not hmac.compare_digest(supplied.encode('utf-8'), SETTINGS_PASSWORD.encode('utf-8')):
                self.send_json({'error': 'Invalid password'}, 401)
                return
            token = secrets.token_urlsafe(32)
            SESSIONS[token] = time.time() + SESSION_TTL
            secure = '; Secure' if self.headers.get('X-Forwarded-Proto', '').lower() == 'https' else ''
            raw = json.dumps({'ok': True, 'expiresIn': SESSION_TTL}).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Set-Cookie', f'net_pulse_settings={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}' + secure)
            self.end_headers()
            self.wfile.write(raw)
            return
        if self.path == '/api/settings/lock':
            cookie = self.headers.get('Cookie', '')
            for part in cookie.split(';'):
                key, _, value = part.strip().partition('=')
                if key == 'net_pulse_settings':
                    SESSIONS.pop(value, None)
            raw = json.dumps({'ok': True}).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Set-Cookie', 'net_pulse_settings=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
            self.end_headers()
            self.wfile.write(raw)
            return
        if self.path not in ['/api/hosts', '/api/hosts/reorder']:
            self.send_response(404)
            self.end_headers()
            return
        if not valid_settings_session(self):
            self.send_json({'error': 'Settings authorization required'}, 401)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body)
            if self.path == '/api/hosts/reorder':
                order = data.get('order', [])
                hosts = load_hosts()
                by_id = {str(host.get('id')): host for host in hosts}
                if not isinstance(order, list) or len(order) != len(hosts) or set(order) != set(by_id):
                    self.send_json({'error': 'Invalid host order'}, 400)
                    return
                save_hosts([by_id[host_id] for host_id in order])
                self.send_json({'ok': True})
                return
            name = str(data.get('name', '')).strip()
            target = str(data.get('target', '')).strip()
            if not target:
                self.send_json({'error': 'target required'}, 400)
                return
            hosts = load_hosts()
            hosts.append({'id': uuid.uuid4().hex[:10], 'name': name or target, 'target': target})
            save_hosts(hosts)
            self.send_json({'ok': True})
        except Exception as e:
            self.send_json({'error': str(e)}, 500)

    def do_DELETE(self):
        if not self.path.startswith('/api/hosts/'):
            self.send_response(404)
            self.end_headers()
            return
        if not valid_settings_session(self):
            self.send_json({'error': 'Settings authorization required'}, 401)
            return
        host_id = self.path.rsplit('/', 1)[-1]
        hosts = load_hosts()
        hosts = [h for h in hosts if h.get('id') != host_id]
        save_hosts(hosts)
        self.send_json({'ok': True})

    def log_message(self, fmt, *args):
        return


if __name__ == '__main__':
    ensure_data_file()
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f'Listening on http://{HOST}:{PORT}')
    httpd.serve_forever()
