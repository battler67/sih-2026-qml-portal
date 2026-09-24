"""Mount the existing genomics API beneath its public Vercel service path."""

import sys
from pathlib import Path

from fastapi import FastAPI

# The reusable Grover package uses a src layout. Vercel uploads the complete
# repository, so expose that source tree without a non-portable file dependency.
repository_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository_root / "qgsa_grover" / "src"))

from quantum_search_api.app import app as genomics_app

app = FastAPI(title="QDNA Genomics Service")
app.mount("/api/genomics", genomics_app)
