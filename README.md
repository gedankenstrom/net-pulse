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

## Settings password protection

The settings menu (gear icon) is protected by a password. Set it through the
`NET_PULSE_SETTINGS_PASSWORD` environment variable; do not commit the password
to this repository. For Docker Compose, create a `.env` file next to the compose
file containing:

```env
NET_PULSE_SETTINGS_PASSWORD=choose-a-long-unique-password
```

After redeploying, the settings menu requires the password. The authorization
expires after 10 minutes. Host creation and deletion are also protected by the
server-side session. Use HTTPS when accessing Net Pulse outside a trusted local
network.

## Docker image

The container image is published to:

- `ghcr.io/gedankenstrom/net-pulse:latest`

## Portainer Stack / Docker Compose

Use this compose file and make sure you redeploy/pull the latest image after updates:

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
