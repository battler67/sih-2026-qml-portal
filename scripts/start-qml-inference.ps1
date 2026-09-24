$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonPath = Join-Path $repoRoot ".venv-qml\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Create the Python 3.12 QML environment first; see the README QML setup section."
}

$pythonVersion = (& $pythonPath -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
if ($pythonVersion -ne "3.12") {
    throw "The QML service requires Python 3.12; .venv-qml uses Python $pythonVersion."
}

if (-not $env:QML_HOST) {
    $env:QML_HOST = "127.0.0.1"
}
if (-not $env:QML_PORT) {
    $env:QML_PORT = "8010"
}
if (-not $env:QML_CORS_ORIGINS) {
    $env:QML_CORS_ORIGINS = "http://127.0.0.1:8081,http://localhost:8081"
}

$existingListener = Get-NetTCPConnection -State Listen -LocalPort ([int]$env:QML_PORT) -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($existingListener) {
    $existingProcess = Get-Process -Id $existingListener.OwningProcess -ErrorAction SilentlyContinue
    $processLabel = if ($existingProcess) {
        "$($existingProcess.ProcessName) (PID $($existingProcess.Id))"
    }
    else {
        "PID $($existingListener.OwningProcess)"
    }
    throw "QML port $env:QML_PORT is already in use by $processLabel. Stop the existing service before starting another instance."
}

Push-Location $repoRoot
try {
    Write-Host "Starting QML inference on http://${env:QML_HOST}:${env:QML_PORT}"
    Write-Host "Allowed frontend origins: $env:QML_CORS_ORIGINS"
    & $pythonPath -m qml_inference.server
}
finally {
    Pop-Location
}
