#!/usr/bin/env bash
# Validate compose.yaml parses and all env-var references resolve.
#
# This is a static check (no containers start, no images pull, no network).
# It catches YAML errors, malformed service definitions, and unresolved
# ${VAR} substitutions. Requires Docker Compose to be installed.
set -euo pipefail

if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose)
else
    echo "Docker Compose is not installed." >&2
    exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

"${COMPOSE_CMD[@]}" config --quiet
echo "compose.yaml is valid."
