#!/usr/bin/env bash
set -euo pipefail
cd /app
if [ ! -f "${HOSTS_FILE:-/app/data/hosts.json}" ]; then
  mkdir -p "$(dirname "${HOSTS_FILE:-/app/data/hosts.json}")"
  echo '[]' > "${HOSTS_FILE:-/app/data/hosts.json}"
fi
exec python3 app.py
