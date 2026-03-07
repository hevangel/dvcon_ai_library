$ErrorActionPreference = "Stop"

$root_dir = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root_dir

& (Join-Path $root_dir "scripts\start_grobid.ps1")
uv sync --project backend
uv run --project backend backend
