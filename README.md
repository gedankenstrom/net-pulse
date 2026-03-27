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

## Docker image

The container image is published to:

- `ghcr.io/gedankenstrom/net-pulse:latest`

## Portainer Stack / Docker Compose

```yaml
services:
  net-pulse:
    image: ghcr.io/gedankenstrom/net-pulse:latest
    container_name: net-pulse
    restart: unless-stopped
    ports:
      - "9301:9301"
    environment:
      - HOSTS_FILE=/app/data/hosts.json
    volumes:
      - net-pulse-data:/app/data

volumes:
  net-pulse-data:
```
