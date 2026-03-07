$ErrorActionPreference = "Stop"

$root_dir = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root_dir

npm --prefix frontend install
npm --prefix frontend run dev -- --host 0.0.0.0
