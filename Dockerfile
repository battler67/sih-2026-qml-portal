FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY quantum_search_api/pyproject.toml /tmp/quantum_search_api/pyproject.toml
COPY qml_inference/pyproject.toml /tmp/qml_inference/pyproject.toml
RUN python -m pip install --no-cache-dir /tmp/quantum_search_api /tmp/qml_inference

COPY quantum_search_api /app/quantum_search_api
COPY qgsa_grover /app/qgsa_grover
COPY frqi_dna /app/frqi_dna
COPY qml_inference /app/qml_inference
COPY vercel_backend.py /app/vercel_backend.py

CMD ["sh", "-c", "python -m uvicorn vercel_backend:app --host 0.0.0.0 --port ${PORT:-3000}"]
