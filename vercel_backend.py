"""Combined container entrypoint for the deployed genomics and QML APIs."""

import sys
from pathlib import Path

from fastapi import FastAPI

repository_root = Path(__file__).resolve().parent
sys.path.insert(0, str(repository_root / "qgsa_grover" / "src"))

from qml_inference.vercel_app import app as qml_app
from quantum_search_api.app import app as genomics_app

app = FastAPI(title="QClinic backend services")
app.mount("/api/genomics", genomics_app)
app.mount("/", qml_app)
