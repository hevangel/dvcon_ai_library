# Start the DVCon MCP server (stdio transport).
#
# The MCP server exposes the corpus search, paper detail, markdown, graph,
# stats, and grounded chat tools to MCP-compatible agent clients. It reuses
# the same .env and data/ corpus as the HTTP backend. GROBID and the OpenAI
# keys are only required for the chat tool; the read tools work standalone.
$ErrorActionPreference = "Stop"

$root_dir = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root_dir

uv run --project backend dvcon-mcp
