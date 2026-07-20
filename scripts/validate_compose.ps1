# Validate compose.yaml parses and all env-var references resolve.
#
# This is a static check (no containers start, no images pull, no network).
# It catches YAML errors, malformed service definitions, and unresolved
# ${VAR} substitutions. Requires Docker Compose to be installed.
$ErrorActionPreference = "Stop"

$root_dir = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root_dir

$compose = $null
$composeArgs = $null
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $testCompose = & docker compose version 2>$null
    if ($LASTEXITCODE -eq 0) {
        $compose = "docker"
        $composeArgs = @("compose")
    }
}
if (-not $compose) {
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        $compose = "docker-compose"
        $composeArgs = @()
    } else {
        Write-Error "Docker Compose is not installed."
        exit 1
    }
}

& $compose @composeArgs config --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Output "compose.yaml is valid."
} else {
    exit $LASTEXITCODE
}
