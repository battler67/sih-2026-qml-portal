$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot
try {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python is required. Install Python 3.13 and run this script again."
    }
    if (-not (Get-Command bun -ErrorAction SilentlyContinue)) {
        throw "Bun is required. Install Bun 1.3 and run this script again."
    }

    if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
        python -m venv .venv
    }

    & ".venv\Scripts\python.exe" -m pip install --upgrade pip
    & ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    bun install --frozen-lockfile

    if (-not (Test-Path -LiteralPath ".env.local")) {
        @(
            "VITE_QUANTUM_API_BASE_URL=http://127.0.0.1:8001"
            "VITE_QML_API_BASE_URL=http://127.0.0.1:8010"
        ) | Set-Content -LiteralPath ".env.local" -Encoding ascii
    }
    if (-not (Test-Path -LiteralPath "quantum_search_api\.env")) {
        @(
            "NCBI_API_KEY="
            "NCBI_TOOL_NAME=quantum_helix_lab"
            "NCBI_DEVELOPER_EMAIL="
            "NCBI_REQUEST_TIMEOUT_SECONDS=30"
            "NCBI_MAX_RETRIES=3"
            "NCBI_CACHE_TTL_SECONDS=86400"
        ) | Set-Content -LiteralPath "quantum_search_api\.env" -Encoding ascii
    }

    Write-Host ""
    Write-Host "Setup complete."
    Write-Host "Edit quantum_search_api\.env with your NCBI email and optional API key."
    Write-Host "Then run scripts\start-backend.ps1, scripts\start-qml-inference.ps1, and scripts\start-frontend.ps1 in separate terminals."
}
finally {
    Pop-Location
}
