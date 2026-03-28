FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app.py /app/app.py
COPY index.html /app/index.html
COPY icon.svg /app/icon.svg
COPY apple-touch-icon.png /app/apple-touch-icon.png

RUN mkdir -p /app/data

ENV HOSTS_FILE=/app/data/hosts.json
EXPOSE 9301

CMD ["python3", "/app/app.py"]
