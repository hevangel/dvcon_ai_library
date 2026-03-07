$ErrorActionPreference = "Stop"

$root_dir = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root_dir

& (Join-Path $root_dir "scripts\start_grobid.ps1")
uv sync --project backend
npm --prefix frontend install

$backend_job = Start-Job -ScriptBlock {
    param($path)
    Set-Location $path
    uv run --project backend backend
} -ArgumentList $root_dir

try {
    npm --prefix frontend run dev -- --host 0.0.0.0
} finally {
    Stop-Job $backend_job -ErrorAction SilentlyContinue
    Remove-Job $backend_job -ErrorAction SilentlyContinue
}
