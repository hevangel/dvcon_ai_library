#!/usr/bin/env bash
set -euo pipefail

if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose)
else
    echo "Docker Compose is not installed." >&2
    exit 1
fi

"${COMPOSE_CMD[@]}" up -d grobid
uv run --project backend python scripts/wait_for_http.py \
    --url "http://127.0.0.1:${GROBID_PORT:-8070}/api/isalive" \
    --contains "true" \
    --timeout 300
