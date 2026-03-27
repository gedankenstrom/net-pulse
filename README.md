# Net Pulse

Net Pulse is a clean local web app for checking whether hosts are online via ping.

## Features

- add hosts by IP or hostname
- live online/offline status
- latency display
- light/dark mode
- clean minimal UI
- local JSON storage
- Docker / Portainer ready

## Local Python run

```bash
python3 app.py
```

## Docker Compose

```bash
docker compose up -d --build
```

Then open:

- `http://<host>:9301`

## Portainer

Use this repository as a stack with:

- Branch: `main`
- Compose path: `docker-compose.yml`
