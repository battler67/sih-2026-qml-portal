"""Bounded, provider-selectable real-hardware execution for promoted QML models.

Credentials are read only from process environment variables. They are never returned,
logged, persisted, or included in exception messages.
"""

from __future__ import annotations

import math
import os
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4

import httpx
import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit
from qiskit.circuit.library import StatePreparation

from .model import MODELS, ModelStore, validate
from .qcnn import QCNN_MODEL_ID, ProcessedImage

QKSVM_MODEL_ID = "framingham-angle-qksvm-pca2"
SUPPORTED_PROVIDERS = ("ibm", "qbraid")


class HardwareError(RuntimeError):
    """A safe, user-facing hardware failure."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _shots(value: Any) -> int:
    try:
        requested = int(value)
    except (TypeError, ValueError) as exc:
        raise HardwareError("Shots must be an integer") from exc
    maximum = int(os.getenv("QML_REAL_HARDWARE_MAX_SHOTS", "1024"))
    if requested < 32 or requested > max(32, min(maximum, 4096)):
        raise HardwareError(f"Shots must be between 32 and {max(32, min(maximum, 4096))}")
    return requested


def _timeout() -> int:
    try:
        return max(30, min(86400, int(os.getenv("QML_HARDWARE_RESULT_TIMEOUT_SECONDS", "3600"))))
    except ValueError:
        return 3600


def _counts(raw: dict[Any, Any]) -> dict[str, int]:
    return dict(sorted((str(key).replace(" ", ""), int(value)) for key, value in raw.items()))


def _zero_price(pricing: Any) -> bool:
    if not isinstance(pricing, dict):
        return False
    try:
        return all(float(pricing.get(key, 0) or 0) == 0 for key in ("perTask", "perShot", "perMinute"))
    except (TypeError, ValueError):
        return False


@dataclass(frozen=True)
class Device:
    provider: str
    device_id: str
    name: str
    qubits: int
    queue_depth: int
    input_types: tuple[str, ...] = ()

    def public(self, required_qubits: int) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "deviceId": self.device_id,
            "name": self.name,
            "qubits": self.qubits,
            "requiredQubits": required_qubits,
            "queueDepth": self.queue_depth,
            "status": "ONLINE",
            "deviceType": "QPU",
            "free": True,
            "inputTypes": list(self.input_types),
        }


@dataclass(frozen=True)
class Execution:
    remote_job_ids: list[str]
    counts: list[dict[str, int]]
    provider_status: str
    transpiled: dict[str, Any]


class IbmProvider:
    name = "ibm"

    def __init__(self, service_factory: Callable[[], Any] | None = None) -> None:
        self.token = os.getenv("QISKIT_IBM_TOKEN", "").strip()
        self.channel = os.getenv("QISKIT_IBM_CHANNEL", "ibm_quantum_platform").strip()
        self.instance = os.getenv("QISKIT_IBM_INSTANCE", "").strip()
        configured = os.getenv("QML_IBM_BACKENDS", os.getenv("QDNA_IBM_BACKENDS", ""))
        self.allowed = {item.strip() for item in configured.split(",") if item.strip()}
        self.service_factory = service_factory

    def configured(self) -> bool:
        return bool(self.token)

    def _service(self):
        if self.service_factory:
            return self.service_factory()
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
        except ImportError as exc:
            raise HardwareError("IBM execution SDK is not installed") from exc
        kwargs: dict[str, Any] = {"channel": self.channel, "token": self.token}
        if self.instance:
            kwargs["instance"] = self.instance
        return QiskitRuntimeService(**kwargs)

    def discover(self, required_qubits: int) -> list[Device]:
        if not self.configured():
            return []
        try:
            backends = self._service().backends(
                simulator=False, operational=True, min_num_qubits=required_qubits
            )
            found = []
            for backend in backends:
                name = getattr(backend, "name", "")
                name = name() if callable(name) else str(name)
                if self.allowed and name not in self.allowed:
                    continue
                status = backend.status()
                if not getattr(status, "operational", False):
                    continue
                found.append(
                    Device(
                        self.name,
                        name,
                        name,
                        int(getattr(backend, "num_qubits", 0)),
                        max(0, int(getattr(status, "pending_jobs", 0))),
                        ("qiskit_isa",),
                    )
                )
            return sorted(found, key=lambda item: (item.qubits - required_qubits, item.queue_depth, item.name))
        except Exception as exc:
            raise HardwareError(f"IBM backend discovery failed ({type(exc).__name__})") from exc

    def run(
        self,
        device: Device,
        circuits: list[QuantumCircuit],
        shots: int,
        on_submitted: Callable[[list[str], str], None],
    ) -> Execution:
        try:
            from qiskit.transpiler import generate_preset_pass_manager
            from qiskit_ibm_runtime import SamplerV2

            service = self._service()
            backend = service.backend(device.device_id)
            manager = generate_preset_pass_manager(optimization_level=1, backend=backend)
            isa = manager.run(circuits)
            if not isinstance(isa, list):
                isa = [isa]
            job = SamplerV2(mode=backend).run(isa, shots=shots)
            job_id = str(job.job_id())
            on_submitted([job_id], str(job.status()))
            result = job.result(timeout=_timeout())
            all_counts = [_counts(getattr(pub.data, "meas").get_counts()) for pub in result]
            depths = [int(circuit.depth()) for circuit in isa]
            sizes = [int(circuit.size()) for circuit in isa]
            return Execution(
                [job_id],
                all_counts,
                str(job.status()),
                {
                    "isaTranspilation": True,
                    "circuitCount": len(isa),
                    "minDepth": min(depths),
                    "maxDepth": max(depths),
                    "minSize": min(sizes),
                    "maxSize": max(sizes),
                    "errorMitigationApplied": False,
                },
            )
        except HardwareError:
            raise
        except Exception as exc:
            raise HardwareError(f"IBM hardware execution failed ({type(exc).__name__})") from exc


class QbraidProvider:
    name = "qbraid"

    def __init__(
        self,
        client_factory: Callable[..., Any] = httpx.Client,
        runtime_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.key = os.getenv("QBRAID_API_KEY", "").strip()
        self.api_base = os.getenv("QBRAID_API_BASE_URL", "https://api-v2.qbraid.com/api/v1").rstrip("/")
        self.client_factory = client_factory
        self.runtime_factory = runtime_factory

    def configured(self) -> bool:
        return bool(self.key)

    def discover(self, required_qubits: int) -> list[Device]:
        if not self.configured():
            return []
        try:
            with self.client_factory(headers={"X-API-KEY": self.key}, timeout=15.0) as client:
                response = client.get(f"{self.api_base}/devices")
                response.raise_for_status()
                payload = response.json()
            data = payload.get("data", payload) if isinstance(payload, dict) else payload
            if isinstance(data, dict):
                data = data.get("devices", data.get("items", []))
            if not isinstance(data, list):
                raise HardwareError("qBraid device discovery returned an unknown schema")
            found = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                inputs = tuple(str(value).lower() for value in item.get("runInputTypes", []))
                qubits = int(item.get("numberQubits") or 0)
                if (
                    str(item.get("status", "")).upper() != "ONLINE"
                    or str(item.get("deviceType", "")).upper() != "QPU"
                    or qubits < required_qubits
                    or item.get("directAccess") is not True
                    or not {"qasm2", "qasm3"}.intersection(inputs)
                    or not _zero_price(item.get("pricing"))
                ):
                    continue
                qrn = str(item.get("qrn") or "")
                if qrn:
                    found.append(Device(self.name, qrn, str(item.get("name") or qrn), qubits, max(0, int(item.get("queueDepth") or 0)), inputs))
            return sorted(found, key=lambda item: (item.qubits - required_qubits, item.queue_depth, item.name))
        except HardwareError:
            raise
        except Exception as exc:
            raise HardwareError(f"qBraid device discovery failed ({type(exc).__name__})") from exc

    def _runtime(self):
        if self.runtime_factory:
            return self.runtime_factory(self.key)
        try:
            from qbraid.runtime import QbraidProvider
        except ImportError as exc:
            raise HardwareError("qBraid execution SDK is not installed") from exc
        try:
            return QbraidProvider(api_key=self.key)
        except TypeError as exc:
            raise HardwareError("Installed qBraid SDK cannot use an in-memory API key") from exc

    def run(
        self,
        device: Device,
        circuits: list[QuantumCircuit],
        shots: int,
        on_submitted: Callable[[list[str], str], None],
    ) -> Execution:
        if len(circuits) != 1:
            raise HardwareError("qBraid QML execution is limited to one circuit per prediction")
        try:
            job = self._runtime().get_device(device.device_id).run(circuits[0], shots=shots)
            value = getattr(job, "id", None)
            value = value() if callable(value) else value
            job_id = str(value or "")
            if not job_id:
                raise HardwareError("qBraid did not return a job identifier")
            on_submitted([job_id], str(job.status()))
            wait = getattr(job, "wait_for_final_state", None)
            if callable(wait):
                wait(timeout=_timeout())
            result = job.result()
            return Execution(
                [job_id],
                [_counts(result.data.get_counts())],
                str(job.status()),
                {
                    "isaTranspilation": False,
                    "circuitCount": 1,
                    "logicalDepth": circuits[0].depth(),
                    "logicalSize": circuits[0].size(),
                    "errorMitigationApplied": False,
                },
            )
        except HardwareError:
            raise
        except Exception as exc:
            raise HardwareError(f"qBraid hardware execution failed ({type(exc).__name__})") from exc


def qcnn_circuit(store: ModelStore, angles: np.ndarray) -> QuantumCircuit:
    """Build the exact trained four-qubit circuit using Qiskit gates."""
    model = store.qcnn.model
    conv = model.conv_weights.detach().cpu().numpy()
    pool = model.pool_weights.detach().cpu().numpy()
    circuit = QuantumCircuit(4)
    for qubit, angle in enumerate(angles):
        circuit.ry(float(angle), qubit)
    active = [0, 1, 2, 3]
    for stage in range(2):
        pairs = [(active[index], active[index + 1]) for index in range(0, len(active), 2)]
        if len(active) > 2:
            pairs.extend((active[index], active[(index + 1) % len(active)]) for index in range(1, len(active), 2))
        for first, second in pairs:
            weights = conv[stage]
            circuit.u(*map(float, weights[0:3]), first)
            circuit.u(*map(float, weights[3:6]), second)
            circuit.rxx(float(weights[6]), first, second)
            circuit.ryy(float(weights[7]), first, second)
            circuit.rzz(float(weights[8]), first, second)
            circuit.u(*map(float, weights[9:12]), first)
            circuit.u(*map(float, weights[12:15]), second)
        for index in range(0, len(active), 2):
            source, sink = active[index], active[index + 1]
            weights = pool[stage]
            circuit.crz(float(weights[0]), source, sink)
            circuit.x(source)
            circuit.crx(float(weights[1]), source, sink)
            circuit.x(source)
            circuit.cry(float(weights[2]), source, sink)
        active = active[1::2]
    register = ClassicalRegister(1, "meas")
    circuit.add_register(register)
    circuit.measure(active[0], register[0])
    return circuit


def qksvm_circuits(store: ModelStore, reduced: np.ndarray) -> list[QuantumCircuit]:
    circuits = []
    for state in store.fhs_training_states:
        circuit = QuantumCircuit(2)
        circuit.ry(float(reduced[0]), 0)
        circuit.ry(float(reduced[1]), 1)
        # PennyLane indexes wire 0 as the most-significant tensor axis; Qiskit uses
        # qubit 0 as the least-significant statevector bit. Swap axes without altering state.
        qiskit_state = np.asarray(state, dtype=complex).reshape(2, 2).T.reshape(4)
        circuit.append(StatePreparation(qiskit_state).inverse(), [0, 1])
        register = ClassicalRegister(2, "meas")
        circuit.add_register(register)
        circuit.measure([0, 1], register)
        circuits.append(circuit)
    return circuits


def _expectation(counts: dict[str, int]) -> float:
    total = sum(counts.values())
    if total <= 0:
        raise HardwareError("Hardware returned no measurement counts")
    zeros = sum(value for state, value in counts.items() if state[-1:] == "0")
    return 2.0 * zeros / total - 1.0


def _fidelity(counts: dict[str, int]) -> float:
    total = sum(counts.values())
    if total <= 0:
        raise HardwareError("Hardware returned no measurement counts")
    return max(0.0, min(1.0, counts.get("00", 0) / total))


@dataclass
class HardwareJob:
    job_id: str
    model_id: str
    provider: str
    shots: int
    status: str = "queued"
    message: str = "Queued for hardware preparation"
    progress_percent: int = 0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    device: Device | None = None
    remote_job_ids: list[str] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None

    def touch(self) -> None:
        self.updated_at = _now()

    def public(self) -> dict[str, Any]:
        return {
            "jobId": self.job_id,
            "modelId": self.model_id,
            "provider": self.provider,
            "shots": self.shots,
            "status": self.status,
            "message": self.message,
            "progressPercent": self.progress_percent,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "selectedDevice": self.device.public(4 if self.model_id == QCNN_MODEL_ID else 2) if self.device else None,
            "remoteJobId": self.remote_job_ids[0] if self.remote_job_ids else None,
            "remoteJobIds": list(self.remote_job_ids),
            "hasResults": self.result is not None,
            "error": self.error,
        }


class QmlHardwareService:
    def __init__(
        self,
        store: ModelStore,
        providers: dict[str, Any] | None = None,
        *,
        run_inline: bool = False,
    ) -> None:
        self.store = store
        self.providers = providers or {"ibm": IbmProvider(), "qbraid": QbraidProvider()}
        self.run_inline = run_inline
        self.jobs: dict[str, HardwareJob] = {}
        self.lock = threading.Lock()

    def capabilities(self) -> dict[str, Any]:
        providers = {
            name: {"configured": bool(provider.configured()), "realHardwareOnly": True}
            for name, provider in self.providers.items()
        }
        return {
            "simulatorDefault": True,
            "providers": providers,
            "models": {
                QCNN_MODEL_ID: {
                    "qubits": 4,
                    "circuitCount": 1,
                    "providers": {"ibm": {"supported": True}, "qbraid": {"supported": True}},
                },
                QKSVM_MODEL_ID: {
                    "qubits": 2,
                    "circuitCount": int(self.store.fhs_qsvm.n_features_in_),
                    "providers": {
                        "ibm": {"supported": True},
                        "qbraid": {
                            "supported": False,
                            "reason": "A faithful prediction needs 256 overlap circuits; qBraid would create separate hardware jobs rather than one bounded batch.",
                        },
                    },
                },
            },
            "credentialPolicy": "Backend environment only; tokens are never returned or logged.",
        }

    def _compatibility(self, model_id: str, provider: str) -> tuple[int, int]:
        if model_id not in (QCNN_MODEL_ID, QKSVM_MODEL_ID):
            raise HardwareError("This model is classical or has no hardware-compatible serving bundle")
        if provider not in self.providers:
            raise HardwareError("Unknown hardware provider")
        capability = self.capabilities()["models"][model_id]["providers"][provider]
        if not capability["supported"]:
            raise HardwareError(capability["reason"])
        return (4, 1) if model_id == QCNN_MODEL_ID else (2, int(self.store.fhs_qsvm.n_features_in_))

    def preview(self, model_id: str, provider: str) -> dict[str, Any]:
        required, circuits = self._compatibility(model_id, provider)
        adapter = self.providers[provider]
        if not adapter.configured():
            raise HardwareError(f"{provider} credentials are not configured in the backend environment")
        devices = adapter.discover(required)
        if not devices:
            raise HardwareError(f"No online free {provider} QPU can fit this {required}-qubit model")
        return {
            "submissionPerformed": False,
            "modelId": model_id,
            "provider": provider,
            "requiredQubits": required,
            "circuitCount": circuits,
            "selectedDevice": devices[0].public(required),
            "candidates": [item.public(required) for item in devices],
        }

    def submit_qcnn(self, processed: ProcessedImage, provider: str, shots: Any, confirmed: bool) -> HardwareJob:
        if not confirmed:
            raise HardwareError("Explicit real-hardware confirmation is required")
        return self._create(QCNN_MODEL_ID, provider, shots, (processed,))

    def submit_tabular(self, model_id: str, features: Any, provider: str, shots: Any, confirmed: bool) -> HardwareJob:
        if not confirmed:
            raise HardwareError("Explicit real-hardware confirmation is required")
        frame = validate(model_id, features)
        return self._create(model_id, provider, shots, (frame,))

    def _create(self, model_id: str, provider: str, shots: Any, payload: tuple[Any, ...]) -> HardwareJob:
        self._compatibility(model_id, provider)
        job = HardwareJob(uuid4().hex, model_id, provider, _shots(shots))
        with self.lock:
            self.jobs[job.job_id] = job
        if self.run_inline:
            self._run(job, payload)
        else:
            threading.Thread(target=self._run, args=(job, payload), daemon=True).start()
        return job

    def get(self, job_id: str) -> HardwareJob:
        with self.lock:
            job = self.jobs.get(job_id)
        if not job:
            raise KeyError(job_id)
        return job

    def _update(self, job: HardwareJob, status: str, message: str, progress: int) -> None:
        with self.lock:
            job.status, job.message, job.progress_percent = status, message, progress
            job.touch()

    def _run(self, job: HardwareJob, payload: tuple[Any, ...]) -> None:
        try:
            self._update(job, "preparing", "Validating hardware compatibility", 10)
            preview = self.preview(job.model_id, job.provider)
            device_id = preview["selectedDevice"]["deviceId"]
            devices = self.providers[job.provider].discover(4 if job.model_id == QCNN_MODEL_ID else 2)
            job.device = next(item for item in devices if item.device_id == device_id)
            if job.model_id == QCNN_MODEL_ID:
                circuits = [qcnn_circuit(self.store, payload[0].angles)]
            else:
                reduced = np.asarray(self.store.fhs_pipeline.transform(payload[0])[0], dtype=float)
                circuits = qksvm_circuits(self.store, reduced)
            self._update(job, "submitting", "Submitting transpiled circuits to the selected QPU", 30)

            def submitted(ids: list[str], provider_status: str) -> None:
                with self.lock:
                    job.remote_job_ids = ids
                    job.message = f"Provider job {provider_status}; waiting for hardware result"
                    job.status = "running"
                    job.progress_percent = 55
                    job.touch()

            started = perf_counter()
            execution = self.providers[job.provider].run(job.device, circuits, job.shots, submitted)
            elapsed = (perf_counter() - started) * 1000.0
            if job.model_id == QCNN_MODEL_ID:
                result = self._qcnn_result(payload[0], execution, elapsed, job)
            else:
                result = self._qksvm_result(payload[0], execution, elapsed, job)
            with self.lock:
                job.result = result
                job.remote_job_ids = execution.remote_job_ids
                job.status = "completed"
                job.message = "Real-hardware prediction completed"
                job.progress_percent = 100
                job.touch()
        except Exception as exc:
            safe = str(exc) if isinstance(exc, HardwareError) else f"Hardware execution failed ({type(exc).__name__})"
            with self.lock:
                job.status = "failed"
                job.message = "Real-hardware prediction did not complete"
                job.error = safe
                job.touch()

    def _hardware_metadata(self, execution: Execution, elapsed: float, job: HardwareJob) -> dict[str, Any]:
        return {
            "provider": job.provider,
            "device": job.device.name if job.device else None,
            "deviceId": job.device.device_id if job.device else None,
            "jobId": execution.remote_job_ids[0],
            "jobIds": execution.remote_job_ids,
            "providerStatus": execution.provider_status,
            "shots": job.shots,
            "qubits": 4 if job.model_id == QCNN_MODEL_ID else 2,
            "circuitCount": len(execution.counts),
            "executionTimeMsIncludingQueue": elapsed,
            "transpilation": execution.transpiled,
            "rawHardwareMeasurements": True,
            "errorMitigationApplied": False,
        }

    def _qcnn_result(self, processed: ProcessedImage, execution: Execution, elapsed: float, job: HardwareJob) -> dict[str, Any]:
        baseline = self.store.qcnn.predict_processed(processed)
        expectation = _expectation(execution.counts[0])
        model = self.store.qcnn.model
        scale = float(model.output_scale.detach().cpu())
        bias = float(model.output_bias.detach().cpu())
        logit = scale * expectation + bias
        score = 1.0 / (1.0 + math.exp(-logit))
        malignant = score >= self.store.qcnn.threshold
        baseline.update(
            {
                "prediction": "malignant" if malignant else "normal_or_benign",
                "predictedClass": int(malignant),
                "classId": int(malignant),
                "probabilities": {"normal_or_benign": 1.0 - score, "malignant": score},
                "malignantScore": score,
                "measurementExpectationZ": expectation,
                "logit": logit,
                "inferenceTimeMs": elapsed,
                "backend": {"type": "real_quantum_hardware", "name": f"{job.provider} · {job.device.name}"},
                "hardwareExecution": self._hardware_metadata(execution, elapsed, job),
            }
        )
        baseline["quantum"] = {**baseline["quantum"], "shots": job.shots, "circuitExecutionsThisPrediction": 1, "circuitDepth": execution.transpiled.get("maxDepth", execution.transpiled.get("logicalDepth"))}
        baseline["warnings"].append("The primary score uses raw finite-shot QPU counts without error mitigation; the occlusion explanation remains a local ideal-simulator calculation and is labeled separately.")
        baseline["explainability"]["executionBackend"] = "local_ideal_simulator"
        return baseline

    def _qksvm_result(self, frame: Any, execution: Execution, elapsed: float, job: HardwareJob) -> dict[str, Any]:
        baseline = self.store.predict(QKSVM_MODEL_ID, frame.iloc[0].to_dict())
        kernel = np.asarray([_fidelity(item) for item in execution.counts], dtype=float).reshape(1, -1)
        score = float(self.store.fhs_qsvm.decision_function(kernel)[0])
        probability = float(self.store.fhs_qcal.predict_proba(np.array([[score]]))[0, 1])
        threshold = float(baseline["threshold"])
        elevated = probability >= threshold
        baseline.update(
            {
                "prediction": "elevated research risk score" if elevated else "lower research risk score",
                "predictedClass": int(elevated),
                "score": score,
                "calibratedProbability": probability,
                "inferenceTimeMs": elapsed,
                "backend": {"type": "real_quantum_hardware", "name": f"{job.provider} · {job.device.name}"},
                "resources": {"qubits": 2, "shots": job.shots, "circuitDepth": execution.transpiled.get("maxDepth"), "circuitExecutionsThisPrediction": len(execution.counts)},
                "hardwareExecution": self._hardware_metadata(execution, elapsed, job),
            }
        )
        baseline["warnings"].append("The primary kernel uses raw finite-shot QPU overlap counts without error mitigation; feature perturbation explanations remain local ideal-simulator calculations and are labeled separately.")
        baseline["explainability"]["executionBackend"] = "local_ideal_simulator"
        return baseline
