"""Small Python 3.12 HTTP service for local research inference.

No external provider calls, persistence, request-body logging, or extra web framework.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from uuid import uuid4

from .model import ArtifactError, InvalidInput, MODELS, ModelStore, schema
from .hardware import HardwareError, QmlHardwareService
from .qcnn import MAX_IMAGE_BYTES, QcnnArtifactError, QcnnInputError, decode_image

MAX_BODY_BYTES = 32_768
PREFIX = "/api/qml/v1"
QCNN_PREDICT_PATH = f"{PREFIX}/qcnn/breastmnist/predict"


def create_handler(
    store: ModelStore,
    allowed_origins: set[str],
    hardware_service: QmlHardwareService | None = None,
):
    hardware = hardware_service or QmlHardwareService(store)

    class Handler(BaseHTTPRequestHandler):
        server_version = "QMLResearch/1"

        def log_message(self, format, *args):  # noqa: A002
            # URLs may contain user data in malformed requests. Do not log requests.
            return

        def _send(self, status: int, data: dict | list, *, origin: str | None = None) -> None:
            body = json.dumps(data, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if origin and origin in allowed_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(body)

        def _origin(self) -> str | None:
            origin = self.headers.get("Origin")
            if origin and origin not in allowed_origins:
                self._send(HTTPStatus.FORBIDDEN, {"error": "Origin is not allowed"})
                return None
            return origin or ""

        def do_OPTIONS(self):  # noqa: N802
            origin = self._origin()
            if origin is None:
                return
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store")
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Vary", "Origin")
            self.end_headers()

        def do_GET(self):  # noqa: N802
            origin = self._origin()
            if origin is None:
                return
            parsed = urlsplit(self.path)
            path = unquote(parsed.path)
            query = parse_qs(parsed.query)
            if path == f"{PREFIX}/health":
                return self._send(200, {"status": "ready", "service": "qml-inference",
                                         "bundleVersion": store.manifest["version"]}, origin=origin)
            if path == f"{PREFIX}/models":
                modality = query.get("modality", [None])[0]
                if modality not in {None, "ehr", "genomics", "imaging"}:
                    return self._send(422, {"error": "modality must be ehr, genomics or imaging"}, origin=origin)
                return self._send(200, {"models": store.models(modality), "disclaimer": store.evidence["framingham"]["limitation"]}, origin=origin)
            if path == f"{PREFIX}/lab/modalities":
                counts = {name: len(store.models(name)) for name in ("ehr", "genomics", "imaging")}
                return self._send(200, {
                    "modalities": [
                        {"id": "ehr", "name": "EHR", "modelCount": counts["ehr"], "status": "available"},
                        {"id": "genomics", "name": "Genomics", "modelCount": counts["genomics"], "status": "available"},
                        {"id": "imaging", "name": "Medical imaging", "modelCount": counts["imaging"], "status": "available"},
                    ],
                    "disclaimer": "Research-use workflows only; no modality provides a medical diagnosis.",
                }, origin=origin)
            if path == f"{PREFIX}/lab/models":
                modality = query.get("modality", [None])[0]
                if modality not in {None, "ehr", "genomics", "imaging"}:
                    return self._send(422, {"error": "modality must be ehr, genomics or imaging"}, origin=origin)
                return self._send(200, {"models": store.models(modality)}, origin=origin)
            if path == f"{PREFIX}/lab/genomics/fh/schema":
                from .fh import fh_schema
                return self._send(200, fh_schema(store.fh.snapshot), origin=origin)
            if path == f"{PREFIX}/lab/evidence-snapshots/{store.fh.snapshot['snapshotId']}":
                return self._send(200, store.fh.snapshot, origin=origin)
            if path == f"{PREFIX}/evidence":
                return self._send(200, store.evidence, origin=origin)
            if path == f"{PREFIX}/hardware/capabilities":
                return self._send(200, hardware.capabilities(), origin=origin)
            if path.startswith(f"{PREFIX}/hardware/jobs/"):
                suffix = path[len(f"{PREFIX}/hardware/jobs/"):]
                job_id, separator, tail = suffix.partition("/")
                try:
                    job = hardware.get(job_id)
                except KeyError:
                    return self._send(404, {"error": "Hardware job not found"}, origin=origin)
                if not separator:
                    return self._send(200, job.public(), origin=origin)
                if tail == "results":
                    if job.status == "failed":
                        return self._send(409, {"error": job.error or "Hardware job failed"}, origin=origin)
                    if job.result is None:
                        return self._send(202, job.public(), origin=origin)
                    return self._send(200, job.result, origin=origin)
                return self._send(404, {"error": "Route not found"}, origin=origin)
            if path.startswith(f"{PREFIX}/models/"):
                parts = path[len(f"{PREFIX}/models/"):].split("/")
                model_id = parts[0]
                if not any(item["id"] == model_id for item in store.models()):
                    return self._send(404, {"error": "Model not found"}, origin=origin)
                if len(parts) == 2 and parts[1] == "schema":
                    if model_id not in MODELS:
                        return self._send(409, {"error": "This model is evidence-only and has no live inference schema"}, origin=origin)
                    return self._send(200, schema(model_id), origin=origin)
                if len(parts) == 2 and parts[1] == "evidence":
                    return self._send(200, store.evidence_for(model_id), origin=origin)
            self._send(404, {"error": "Route not found"}, origin=origin)

        def do_POST(self):  # noqa: N802
            origin = self._origin()
            if origin is None:
                return
            path = unquote(urlsplit(self.path).path)
            query = parse_qs(urlsplit(self.path).query)
            if path == f"{PREFIX}/hardware/qcnn/breastmnist/jobs":
                try:
                    try:
                        length = int(self.headers.get("Content-Length", "-1"))
                    except ValueError as exc:
                        raise QcnnInputError("Image request has an invalid Content-Length") from exc
                    if length < 0 or length > MAX_IMAGE_BYTES:
                        raise QcnnInputError("Image must be present and 5 MB or smaller")
                    processed = decode_image(self.rfile.read(length), self.headers.get("Content-Type", ""))
                    job = hardware.submit_qcnn(
                        processed,
                        query.get("provider", [""])[0],
                        query.get("shots", ["128"])[0],
                        query.get("confirmRealHardware", ["false"])[0].lower() == "true",
                    )
                    return self._send(202, job.public(), origin=origin)
                except QcnnInputError as exc:
                    return self._send(422, {"error": str(exc)}, origin=origin)
                except HardwareError as exc:
                    return self._send(409, {"error": str(exc)}, origin=origin)
            if path == QCNN_PREDICT_PATH:
                try:
                    try:
                        length = int(self.headers.get("Content-Length", "-1"))
                    except ValueError as exc:
                        raise QcnnInputError("Image request has an invalid Content-Length") from exc
                    if length < 0:
                        raise QcnnInputError("Image request is missing Content-Length")
                    if length > MAX_IMAGE_BYTES:
                        raise QcnnInputError("Image must be 5 MB or smaller")
                    content_type = self.headers.get("Content-Type", "")
                    return self._send(
                        200,
                        store.predict_qcnn(self.rfile.read(length), content_type),
                        origin=origin,
                    )
                except QcnnInputError as exc:
                    return self._send(422, {"error": str(exc)}, origin=origin)
                except (QcnnArtifactError, OSError, RuntimeError, ValueError):
                    return self._send(503, {"error": "QCNN inference is unavailable"}, origin=origin)
            if path not in {
                f"{PREFIX}/predict",
                f"{PREFIX}/report",
                f"{PREFIX}/lab/genomics/fh/analyze",
                f"{PREFIX}/hardware/preview",
                f"{PREFIX}/hardware/jobs",
            }:
                return self._send(404, {"error": "Route not found"}, origin=origin)
            try:
                length = int(self.headers.get("Content-Length", "-1"))
                if not 0 <= length <= MAX_BODY_BYTES:
                    raise InvalidInput("JSON request is missing or too large")
                if "application/json" not in self.headers.get("Content-Type", ""):
                    raise InvalidInput("Content-Type must be application/json")
                request = json.loads(self.rfile.read(length))
                if path == f"{PREFIX}/lab/genomics/fh/analyze":
                    if not isinstance(request, dict) or set(request) != {"record"}:
                        raise InvalidInput("Expected record only")
                    return self._send(200, store.fh.analyze(request["record"]), origin=origin)
                if path == f"{PREFIX}/hardware/preview":
                    if not isinstance(request, dict) or set(request) != {"modelId", "provider"}:
                        raise InvalidInput("Expected modelId and provider only")
                    try:
                        return self._send(200, hardware.preview(str(request["modelId"]), str(request["provider"])), origin=origin)
                    except HardwareError as exc:
                        return self._send(409, {"error": str(exc)}, origin=origin)
                if path == f"{PREFIX}/hardware/jobs":
                    expected = {"modelId", "features", "provider", "shots", "confirmRealHardware"}
                    if not isinstance(request, dict) or set(request) != expected:
                        raise InvalidInput("Expected modelId, features, provider, shots and confirmRealHardware")
                    try:
                        job = hardware.submit_tabular(
                            str(request["modelId"]), request["features"], str(request["provider"]),
                            request["shots"], request["confirmRealHardware"] is True,
                        )
                        return self._send(202, job.public(), origin=origin)
                    except HardwareError as exc:
                        return self._send(409, {"error": str(exc)}, origin=origin)
                if not isinstance(request, dict) or set(request) != {"modelId", "features"}:
                    raise InvalidInput("Expected modelId and features only")
                model_id = request["modelId"]
                if not isinstance(model_id, str) or model_id not in MODELS:
                    return self._send(404, {"error": "Model not found"}, origin=origin)
                prediction = store.predict(model_id, request["features"])
                if path.endswith("/predict"):
                    return self._send(200, prediction, origin=origin)
                return self._send(200, {
                    "reportId": uuid4().hex,
                    "generatedAt": datetime.now(UTC).isoformat(),
                    "prediction": prediction,
                    "benchmark": store.evidence_for(model_id)["selectedRun"],
                    "disclaimer": prediction["disclaimer"],
                }, origin=origin)
            except (InvalidInput, ValueError, TypeError, json.JSONDecodeError) as exc:
                return self._send(422, {"error": str(exc)}, origin=origin)
            except Exception:
                # Never include input rows or internal artifact paths in HTTP errors.
                return self._send(503, {"error": "QML inference is unavailable"}, origin=origin)

    return Handler


def main() -> None:
    root = Path(os.getenv("QML_BUNDLE_DIR", Path(__file__).parent / "artifacts/v1"))
    try:
        store = ModelStore(root)
    except (ArtifactError, QcnnArtifactError, OSError, KeyError, ValueError) as exc:
        raise SystemExit(f"QML bundle failed readiness check: {exc}") from exc
    origins = {part.strip().rstrip("/") for part in os.getenv(
        "QML_CORS_ORIGINS", "http://127.0.0.1:8081,http://localhost:8081"
    ).split(",") if part.strip()}
    host = os.getenv("QML_HOST", "127.0.0.1")
    port = int(os.getenv("PORT", os.getenv("QML_PORT", "8010")))
    print(f"QML inference ready on {host}:{port}; bundle {store.manifest['version']}")
    ThreadingHTTPServer((host, port), create_handler(store, origins)).serve_forever()


if __name__ == "__main__":
    main()
