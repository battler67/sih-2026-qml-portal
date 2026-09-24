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
        Copy-Item -LiteralPath ".env.example" -Destination ".env.local"
    }
    if (-not (Test-Path -LiteralPath "quantum_search_api\.env")) {
        Copy-Item -LiteralPath "quantum_search_api\.env.example" -Destination "quantum_search_api\.env"
    }

    Write-Host ""
    Write-Host "Setup complete."
    Write-Host "Edit quantum_search_api\.env with your NCBI email and optional API key."
    Write-Host "Then run scripts\start-backend.ps1, scripts\start-qml-inference.ps1, and scripts\start-frontend.ps1 in separate terminals."
}
finally {
    Pop-Location
}
