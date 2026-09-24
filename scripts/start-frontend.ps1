$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$frontendHost = if ($env:QDNA_FRONTEND_HOST) { $env:QDNA_FRONTEND_HOST } else { "127.0.0.1" }
$frontendPort = if ($env:QDNA_FRONTEND_PORT) { $env:QDNA_FRONTEND_PORT } else { "8081" }
Push-Location $repoRoot
try {
    Write-Host "Starting portal frontend on http://${frontendHost}:${frontendPort}"
    bun run dev -- --host $frontendHost --port $frontendPort --strictPort
}
finally {
    Pop-Location
}
