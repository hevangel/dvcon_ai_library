#!/usr/bin/env bash
# Start the DVCon MCP server (stdio transport).
#
# The MCP server exposes the corpus search, paper detail, markdown, graph,
# stats, and grounded chat tools to MCP-compatible agent clients. It reuses
# the same .env and data/ corpus as the HTTP backend. GROBID and the OpenAI
# keys are only required for the chat tool; the read tools work standalone.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

uv run --project backend dvcon-mcp
