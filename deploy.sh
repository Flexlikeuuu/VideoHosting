#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  echo "[deploy] .env not found, copying from .env.example..."
  cp .env.example .env
fi

echo "[deploy] Building and starting services..."
docker compose up -d --build

echo "[deploy] Waiting for services to become healthy..."
for i in $(seq 1 30); do
  if docker compose ps --format json | grep -q '"Health":"healthy"'; then
    if curl -fsS "http://localhost:${APP_PORT:-80}/api/v1/health" >/dev/null 2>&1; then
      echo "[deploy] System is healthy!"
      echo "  - App:     http://localhost:${APP_PORT:-80}"
      echo "  - Swagger: http://localhost:${APP_PORT:-80}/docs"
      echo "  - Health:  http://localhost:${APP_PORT:-80}/api/v1/health"
      exit 0
    fi
  fi
  sleep 2
done

echo "[deploy] Timed out waiting for healthy status. Current containers:"
docker compose ps
exit 1
