# Portal startup script alignment

## Goal

Make the local portal start consistently with the frontend on port 8081, the main FastAPI backend on port 8001, and the QML inference service on port 8010.

## Planned changes

- Make the frontend fail clearly if port 8081 is unavailable instead of silently moving to another port.
- Add a dedicated QML inference startup script using this repository's Python 3.12 environment.
- Align the browser API environment variables with ports 8001 and 8010.
- Allow the local QML service to accept the configured frontend origin.
- Update the local startup documentation.

## Verification

- Confirmed all three launchers resolve from the repository root and use ports 8001, 8010, and 8081.
- Confirmed `.env.local` and `.env.example` point the browser to ports 8001 and 8010.
- Confirmed the QML launcher allows the exact frontend origin on port 8081.
- Added a QML port guard so a second inference process cannot silently share port 8010.
- `bun run lint` completed without reporting an ESLint error.
- `python -m py_compile qml_inference/server.py` passed.

## Files changed

- `scripts/start-backend.ps1`
- `scripts/start-frontend.ps1`
- `scripts/start-qml-inference.ps1`
- `scripts/setup.ps1`
- `.env.local`
- `.env.example`
- `qml_inference/server.py`
- `README.md`
