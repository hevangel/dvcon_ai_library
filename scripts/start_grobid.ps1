$ErrorActionPreference = "Stop"

try {
    docker compose version *> $null
    $compose_command = "docker compose"
} catch {
    $docker_compose = Get-Command docker-compose -ErrorAction SilentlyContinue
    if (-not $docker_compose) {
        throw "Docker Compose is not installed."
    }
    $compose_command = "docker-compose"
}

Invoke-Expression "$compose_command up -d grobid"
if ($env:GROBID_PORT) {
    $grobid_port = $env:GROBID_PORT
} else {
    $grobid_port = "8070"
}
uv run --project backend python scripts/wait_for_http.py --url "http://127.0.0.1:$grobid_port/api/isalive" --contains "true" --timeout 300
