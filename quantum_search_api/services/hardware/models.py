from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from qiskit import QuantumCircuit

from quantum_search_api.services.ncbi.models import SearchRequest


class HardwareSubmissionRequest(BaseModel):
    """Explicitly confirmed request to spend an external hardware job."""

    model_config = ConfigDict(populate_by_name=True)

    search_request: SearchRequest = Field(alias="searchRequest")
    confirm_real_hardware: bool = Field(default=False, alias="confirmRealHardware")


@dataclass(frozen=True)
class DeviceCandidate:
    provider: str
    device_id: str
    name: str
    qubits: int
    queue_depth: int
    status: str
    device_type: str = "QPU"
    is_free: bool = True
    input_types: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def public_dict(self, *, required_qubits: int | None = None) -> dict[str, Any]:
        payload = {
            "provider": self.provider,
            "deviceId": self.device_id,
            "name": self.name,
            "qubits": self.qubits,
            "queueDepth": self.queue_depth,
            "status": self.status,
            "deviceType": self.device_type,
            "free": self.is_free,
            "inputTypes": list(self.input_types),
        }
        if required_qubits is not None:
            payload["requiredQubits"] = required_qubits
            payload["unusedQubits"] = self.qubits - required_qubits
        return payload


@dataclass(frozen=True)
class PreparedHardwareCircuit:
    circuit: QuantumCircuit
    algorithm: str
    classical_register: str
    query_sequence: str
    window_sequence: str
    window_metadata: dict[str, Any]
    retrieval_metadata: dict[str, Any]
    warnings: tuple[str, ...] = ()

    def circuit_metadata(self) -> dict[str, Any]:
        return {
            "logicalQubits": self.circuit.num_qubits,
            "classicalBits": self.circuit.num_clbits,
            "depth": self.circuit.depth(),
            "size": self.circuit.size(),
            "operationCounts": {
                str(name): int(count) for name, count in self.circuit.count_ops().items()
            },
        }


@dataclass(frozen=True)
class ProviderExecutionResult:
    remote_job_id: str
    counts: dict[str, int]
    provider_status: str
    transpiled_circuit_metrics: dict[str, Any] | None = None
    provider_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HardwareJob:
    job_id: str
    request: SearchRequest
    status: str = "queued"
    progress_percent: int = 0
    message: str = "Queued for hardware preparation"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    selected_device: DeviceCandidate | None = None
    remote_job_id: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    provider_errors: list[str] = field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "jobId": self.job_id,
            "status": self.status,
            "progressPercent": self.progress_percent,
            "message": self.message,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "remoteJobId": self.remote_job_id,
            "selectedDevice": (
                self.selected_device.public_dict() if self.selected_device else None
            ),
            "providerErrors": list(self.provider_errors),
            "hasResults": self.result is not None,
            "error": self.error,
        }
