#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"
npm --prefix frontend install
npm --prefix frontend run dev -- --host 0.0.0.0
