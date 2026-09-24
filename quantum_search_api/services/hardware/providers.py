from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, Protocol

import httpx
from qiskit import QuantumCircuit

from quantum_search_api.services.hardware.models import (
    DeviceCandidate,
    ProviderExecutionResult,
)


class HardwareProviderError(RuntimeError):
    pass


class HardwareProvider(Protocol):
    provider_name: str

    def configured(self) -> bool:
        ...

    def discover(self, required_qubits: int) -> list[DeviceCandidate]:
        ...

    def submit(
        self,
        candidate: DeviceCandidate,
        circuit: QuantumCircuit,
        *,
        shots: int,
        classical_register: str,
    ) -> ProviderExecutionResult:
        ...


def _normalized_counts(raw: dict[Any, Any]) -> dict[str, int]:
    return dict(
        sorted(
            (
                str(state).replace(" ", ""),
                int(count),
            )
            for state, count in raw.items()
        )
    )


def _nonnegative_int(value: Any, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _price_is_zero(pricing: Any) -> bool:
    if not isinstance(pricing, dict):
        return False
    for key in ("perTask", "perShot", "perMinute"):
        if key not in pricing:
            return False
        try:
            if float(pricing.get(key, 0) or 0) != 0.0:
                return False
        except (TypeError, ValueError):
            return False
    return True


def _result_timeout_seconds() -> int:
    raw = os.getenv("QDNA_HARDWARE_RESULT_TIMEOUT_SECONDS", "3600")
    try:
        return max(30, min(86400, int(raw)))
    except ValueError:
        return 3600


class QbraidHardwareProvider:
    provider_name = "qbraid"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_base: str | None = None,
        client_factory: Callable[..., httpx.Client] = httpx.Client,
        runtime_provider_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.api_key = (api_key or os.getenv("QBRAID_API_KEY") or "").strip()
        self.api_base = (
            api_base
            or os.getenv("QBRAID_API_BASE_URL")
            or "https://api-v2.qbraid.com/api/v1"
        ).rstrip("/")
        self.client_factory = client_factory
        self.runtime_provider_factory = runtime_provider_factory

    def configured(self) -> bool:
        return bool(self.api_key)

    def discover(self, required_qubits: int) -> list[DeviceCandidate]:
        if not self.configured():
            return []
        try:
            with self.client_factory(
                headers={"X-API-KEY": self.api_key},
                timeout=15.0,
            ) as client:
                response = client.get(f"{self.api_base}/devices")
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            raise HardwareProviderError(
                f"qBraid device discovery failed: {type(exc).__name__}"
            ) from exc

        data = payload.get("data", payload) if isinstance(payload, dict) else payload
        if isinstance(data, dict):
            data = data.get("devices", data.get("items", []))
        if not isinstance(data, list):
            raise HardwareProviderError("qBraid device discovery returned an unknown schema")

        candidates: list[DeviceCandidate] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            qubits = _nonnegative_int(item.get("numberQubits"))
            status = str(item.get("status") or "").upper()
            device_type = str(item.get("deviceType") or "").upper()
            inputs = tuple(str(value).lower() for value in item.get("runInputTypes", []))
            free = _price_is_zero(item.get("pricing"))
            if (
                status != "ONLINE"
                or device_type != "QPU"
                or qubits < required_qubits
                or not free
                or item.get("directAccess") is not True
                or not {"qasm2", "qasm3"}.intersection(inputs)
            ):
                continue
            qrn = str(item.get("qrn") or "")
            if not qrn:
                continue
            candidates.append(
                DeviceCandidate(
                    provider=self.provider_name,
                    device_id=qrn,
                    name=str(item.get("name") or qrn),
                    qubits=qubits,
                    queue_depth=_nonnegative_int(item.get("queueDepth")),
                    status=status,
                    device_type=device_type,
                    is_free=True,
                    input_types=inputs,
                    metadata={
                        "avgQueueTime": item.get("avgQueueTime"),
                        "pricing": item.get("pricing"),
                    },
                )
            )
        return candidates

    def submit(
        self,
        candidate: DeviceCandidate,
        circuit: QuantumCircuit,
        *,
        shots: int,
        classical_register: str,
    ) -> ProviderExecutionResult:
        current = {item.device_id: item for item in self.discover(circuit.num_qubits)}
        if candidate.device_id not in current:
            raise HardwareProviderError(
                "The selected qBraid device is no longer online, free, and large enough"
            )
        try:
            provider = self._runtime_provider()
            device = provider.get_device(candidate.device_id)
            job = device.run(circuit, shots=shots)
            remote_job_id = self._job_identifier(job)
            wait_for_final_state = getattr(job, "wait_for_final_state", None)
            if callable(wait_for_final_state):
                wait_for_final_state(timeout=_result_timeout_seconds())
            result = job.result()
            counts = _normalized_counts(result.data.get_counts())
            status = str(job.status())
        except HardwareProviderError:
            raise
        except Exception as exc:
            raise HardwareProviderError(
                f"qBraid hardware submission failed: {type(exc).__name__}"
            ) from exc
        return ProviderExecutionResult(
            remote_job_id=remote_job_id,
            counts=counts,
            provider_status=status,
            provider_metadata={"rawMitigationApplied": False},
        )

    def _runtime_provider(self) -> Any:
        if self.runtime_provider_factory is not None:
            return self.runtime_provider_factory(self.api_key)
        try:
            from qbraid.runtime import QbraidProvider
        except ImportError as exc:
            raise HardwareProviderError(
                "qBraid execution requires the optional qbraid SDK"
            ) from exc
        try:
            return QbraidProvider(api_key=self.api_key)
        except TypeError as exc:
            raise HardwareProviderError(
                "Installed qBraid SDK cannot accept an in-memory API key; "
                "upgrade qbraid instead of saving credentials in source"
            ) from exc

    @staticmethod
    def _job_identifier(job: Any) -> str:
        value = getattr(job, "id", None)
        if callable(value):
            value = value()
        if not value:
            value = getattr(job, "job_id", None)
            value = value() if callable(value) else value
        if not value:
            raise HardwareProviderError("qBraid did not return a remote job identifier")
        return str(value)


class IbmHardwareProvider:
    provider_name = "ibm"
    default_backend_names = ("ibm_fez", "ibm_marrakesh", "ibm_kingston")

    def __init__(
        self,
        *,
        token: str | None = None,
        channel: str | None = None,
        instance: str | None = None,
        backend_names: tuple[str, ...] | None = None,
        service_factory: Callable[[], Any] | None = None,
        sampler_factory: Callable[[Any], Any] | None = None,
        pass_manager_factory: Callable[[Any], Any] | None = None,
    ) -> None:
        self.token = (token or os.getenv("QISKIT_IBM_TOKEN") or "").strip()
        self.channel = (
            channel
            or os.getenv("QISKIT_IBM_CHANNEL")
            or "ibm_quantum_platform"
        ).strip()
        self.instance = (instance or os.getenv("QISKIT_IBM_INSTANCE") or "").strip()
        configured_names = os.getenv("QDNA_IBM_BACKENDS")
        if backend_names is not None:
            self.backend_names = backend_names
        elif configured_names is not None:
            self.backend_names = tuple(
                name.strip() for name in configured_names.split(",") if name.strip()
            )
        else:
            self.backend_names = self.default_backend_names
        self.service_factory = service_factory
        self.sampler_factory = sampler_factory
        self.pass_manager_factory = pass_manager_factory

    def configured(self) -> bool:
        return bool(self.token)

    def discover(self, required_qubits: int) -> list[DeviceCandidate]:
        if not self.configured():
            return []
        try:
            service = self._service()
            backends = service.backends(
                simulator=False,
                operational=True,
                min_num_qubits=required_qubits,
            )
        except Exception as exc:
            raise HardwareProviderError(
                f"IBM backend discovery failed: {type(exc).__name__}"
            ) from exc

        candidates: list[DeviceCandidate] = []
        allowed = set(self.backend_names)
        for backend in backends:
            name = self._backend_name(backend)
            if allowed and name not in allowed:
                continue
            status = backend.status()
            if not bool(getattr(status, "operational", False)):
                continue
            qubits = _nonnegative_int(getattr(backend, "num_qubits", 0))
            if qubits < required_qubits:
                continue
            candidates.append(
                DeviceCandidate(
                    provider=self.provider_name,
                    device_id=name,
                    name=name,
                    qubits=qubits,
                    queue_depth=_nonnegative_int(
                        getattr(status, "pending_jobs", 0)
                    ),
                    status="ONLINE",
                    device_type="QPU",
                    is_free=True,
                    input_types=("qiskit_isa",),
                    metadata={
                        "entitlement": (
                            "Accessible through the configured IBM account; provider "
                            "usage limits remain authoritative."
                        )
                    },
                )
            )
        return candidates

    def submit(
        self,
        candidate: DeviceCandidate,
        circuit: QuantumCircuit,
        *,
        shots: int,
        classical_register: str,
    ) -> ProviderExecutionResult:
        current = {item.device_id: item for item in self.discover(circuit.num_qubits)}
        if candidate.device_id not in current:
            raise HardwareProviderError(
                "The selected IBM backend is no longer operational and large enough"
            )
        try:
            service = self._service()
            backend = service.backend(candidate.device_id)
            pass_manager = self._pass_manager(backend)
            isa_circuit = pass_manager.run(circuit)
            sampler = self._sampler(backend)
            job = sampler.run([isa_circuit], shots=shots)
            remote_job_id = self._job_identifier(job)
            primitive_result = job.result(timeout=_result_timeout_seconds())
            pub_result = primitive_result[0]
            register_data = getattr(pub_result.data, classical_register)
            counts = _normalized_counts(register_data.get_counts())
            provider_status = str(job.status())
        except HardwareProviderError:
            raise
        except Exception as exc:
            raise HardwareProviderError(
                f"IBM hardware submission failed: {type(exc).__name__}"
            ) from exc

        return ProviderExecutionResult(
            remote_job_id=remote_job_id,
            counts=counts,
            provider_status=provider_status,
            transpiled_circuit_metrics={
                "qubits": isa_circuit.num_qubits,
                "depth": isa_circuit.depth(),
                "size": isa_circuit.size(),
                "operationCounts": {
                    str(name): int(count)
                    for name, count in isa_circuit.count_ops().items()
                },
            },
            provider_metadata={
                "isaTranspilation": True,
                "errorMitigationApplied": False,
            },
        )

    def _service(self) -> Any:
        if self.service_factory is not None:
            return self.service_factory()
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
        except ImportError as exc:
            raise HardwareProviderError(
                "IBM execution requires the optional qiskit-ibm-runtime package"
            ) from exc
        kwargs: dict[str, Any] = {"channel": self.channel, "token": self.token}
        if self.instance:
            kwargs["instance"] = self.instance
        return QiskitRuntimeService(**kwargs)

    def _sampler(self, backend: Any) -> Any:
        if self.sampler_factory is not None:
            return self.sampler_factory(backend)
        from qiskit_ibm_runtime import SamplerV2

        return SamplerV2(mode=backend)

    def _pass_manager(self, backend: Any) -> Any:
        if self.pass_manager_factory is not None:
            return self.pass_manager_factory(backend)
        from qiskit.transpiler import generate_preset_pass_manager

        return generate_preset_pass_manager(
            optimization_level=1,
            backend=backend,
        )

    @staticmethod
    def _backend_name(backend: Any) -> str:
        value = getattr(backend, "name", "")
        value = value() if callable(value) else value
        return str(value)

    @staticmethod
    def _job_identifier(job: Any) -> str:
        value = getattr(job, "job_id", None)
        value = value() if callable(value) else value
        if not value:
            raise HardwareProviderError("IBM did not return a remote job identifier")
        return str(value)


def select_best_device(
    candidates: list[DeviceCandidate],
    *,
    required_qubits: int,
) -> DeviceCandidate:
    """Select the smallest adequate QPU, then the least queued stable choice."""

    eligible = [
        candidate
        for candidate in candidates
        if candidate.status == "ONLINE"
        and candidate.device_type == "QPU"
        and candidate.is_free
        and candidate.qubits >= required_qubits
    ]
    if not eligible:
        raise HardwareProviderError(
            f"No online free hardware device can fit the {required_qubits}-qubit circuit"
        )
    return min(
        eligible,
        key=lambda candidate: (
            candidate.qubits - required_qubits,
            candidate.queue_depth,
            candidate.provider,
            candidate.device_id,
        ),
    )
