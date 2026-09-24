$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"
$backendHost = if ($env:QDNA_BACKEND_HOST) { $env:QDNA_BACKEND_HOST } else { "127.0.0.1" }
$backendPort = if ($env:QDNA_BACKEND_PORT) { $env:QDNA_BACKEND_PORT } else { "8001" }
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Run scripts\setup.ps1 first."
}

Push-Location $repoRoot
try {
    Write-Host "Starting portal backend on http://${backendHost}:${backendPort}"
    & $pythonPath -m uvicorn quantum_search_api.app:app --reload --host $backendHost --port $backendPort
}
finally {
    Pop-Location
}
