#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() {
    if [[ -n "${BACKEND_PID:-}" ]]; then
        kill "$BACKEND_PID" >/dev/null 2>&1 || true
    fi
}

trap cleanup EXIT

cd "$ROOT_DIR"
./scripts/start_grobid.sh
uv sync --project backend
npm --prefix frontend install

uv run --project backend backend &
BACKEND_PID=$!

npm --prefix frontend run dev -- --host 0.0.0.0
