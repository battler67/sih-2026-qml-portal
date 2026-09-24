from __future__ import annotations

import importlib
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from quantum_search_api.services.hardware.circuit_service import HardwareCircuitService
from quantum_search_api.services.hardware.job_service import HardwareJobService
from quantum_search_api.services.hardware.models import (
    DeviceCandidate,
    HardwareSubmissionRequest,
    ProviderExecutionResult,
)
from quantum_search_api.services.hardware.providers import (
    HardwareProviderError,
    IbmHardwareProvider,
    QbraidHardwareProvider,
    select_best_device,
)
from quantum_search_api.services.ncbi.models import SearchRequest


def local_request(algorithm: str = "frqi", *, shots: int = 32) -> SearchRequest:
    return SearchRequest(
        querySource="pasted",
        querySequence="ACGT",
        referenceSequence="ATGT",
        databaseScope="pasted_sequence",
        algorithm=algorithm,
        maxWindows=8,
        strand="forward",
        shots=shots,
    )


@pytest.mark.parametrize(
    ("algorithm", "classical_register"),
    [
        ("frqi", "c"),
        ("grover", "c_idx"),
        ("hybrid", "c_pos"),
    ],
)
def test_hardware_circuit_service_builds_actual_measured_circuit(
    algorithm,
    classical_register,
):
    prepared = HardwareCircuitService().prepare(local_request(algorithm))

    assert prepared.algorithm == algorithm
    assert prepared.classical_register == classical_register
    assert prepared.circuit.num_clbits >= 1
    assert prepared.window_sequence == "ATGT"
    assert prepared.window_metadata["selectionMethod"].endswith("no Aer pre-ranking.")
    assert any("one representative bounded window" in item for item in prepared.warnings)


def test_hardware_circuit_service_bounds_one_hundred_thousand_base_inputs():
    sequence = "ACGT" * 25_000
    prepared = HardwareCircuitService().prepare(
        SearchRequest(
            querySource="pasted",
            querySequence=f">query length=100000 seed=42\n{sequence}",
            referenceSequence=f">reference_sequence length=100000 seed=42\n{sequence}",
            databaseScope="pasted_sequence",
            algorithm="frqi",
            maxQueryLength=32,
            maxBasesPerRecord=100_000,
            maxTotalBases=100_000,
            maxWindows=1,
            strand="forward",
            shots=138,
        )
    )

    assert len(prepared.query_sequence) == 32
    assert len(prepared.window_sequence) == 32
    assert prepared.circuit.num_qubits == 7
    assert any("100000 bases" in warning for warning in prepared.warnings)


def test_hardware_circuit_service_prepares_hybrid_input_over_thirty_two_bases():
    reference = "ACGT" * 8 + "A"
    query = reference[:-1] + "T"

    prepared = HardwareCircuitService().prepare(
        SearchRequest(
            querySource="pasted",
            querySequence=query,
            referenceSequence=reference,
            databaseScope="pasted_sequence",
            algorithm="hybrid",
            maxQueryLength=32,
            maxWindows=1,
            strand="forward",
            shots=32,
        )
    )

    assert len(prepared.query_sequence) == 33
    assert len(prepared.window_sequence) == 33
    assert prepared.circuit.num_qubits == 13
    assert prepared.classical_register == "c_pos"


def test_device_selection_minimizes_unused_qubits_before_queue_depth():
    selected = select_best_device(
        [
            DeviceCandidate("ibm", "ibm-156", "IBM", 156, 0, "ONLINE"),
            DeviceCandidate("qbraid", "qpu-20-busy", "20Q", 20, 9, "ONLINE"),
            DeviceCandidate("qbraid", "qpu-20-free", "20Q", 20, 2, "ONLINE"),
            DeviceCandidate("qbraid", "qpu-12", "12Q", 12, 0, "ONLINE"),
        ],
        required_qubits=13,
    )

    assert selected.device_id == "qpu-20-free"


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self, payload, **_kwargs):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def get(self, _url):
        return FakeResponse(self.payload)


def test_qbraid_discovery_filters_to_online_free_qpus_with_capacity():
    payload = {
        "data": [
            {
                "qrn": "free:20",
                "name": "Free 20",
                "numberQubits": 20,
                "status": "ONLINE",
                "deviceType": "QPU",
                "queueDepth": 3,
                "directAccess": True,
                "runInputTypes": ["qasm2", "qasm3"],
                "pricing": {"perTask": 0, "perShot": 0, "perMinute": 0},
            },
            {
                "qrn": "paid:36",
                "name": "Paid 36",
                "numberQubits": 36,
                "status": "ONLINE",
                "deviceType": "QPU",
                "queueDepth": 0,
                "directAccess": True,
                "runInputTypes": ["qasm3"],
                "pricing": {"perTask": 1, "perShot": 0, "perMinute": 0},
            },
            {
                "qrn": "sim:30",
                "name": "Simulator",
                "numberQubits": 30,
                "status": "ONLINE",
                "deviceType": "SIMULATOR",
                "queueDepth": 0,
                "directAccess": True,
                "runInputTypes": ["qasm3"],
                "pricing": {"perTask": 0, "perShot": 0, "perMinute": 0},
            },
        ]
    }
    provider = QbraidHardwareProvider(
        api_key="test-only",
        client_factory=lambda **kwargs: FakeHttpClient(payload, **kwargs),
    )

    devices = provider.discover(required_qubits=13)

    assert [device.device_id for device in devices] == ["free:20"]
    assert devices[0].queue_depth == 3


class FakeBackend:
    def __init__(self, name: str, qubits: int, queue: int, operational: bool = True):
        self.name = name
        self.num_qubits = qubits
        self._status = SimpleNamespace(
            operational=operational,
            pending_jobs=queue,
        )

    def status(self):
        return self._status


class FakeIbmService:
    def __init__(self, backends):
        self._backends = backends

    def backends(self, **_kwargs):
        return self._backends


def test_ibm_discovery_uses_accessible_allowlisted_operational_backends():
    service = FakeIbmService(
        [
            FakeBackend("ibm_fez", 156, 7),
            FakeBackend("ibm_other", 200, 0),
            FakeBackend("ibm_kingston", 156, 1, operational=False),
        ]
    )
    provider = IbmHardwareProvider(
        token="test-only",
        backend_names=("ibm_fez", "ibm_kingston"),
        service_factory=lambda: service,
    )

    devices = provider.discover(required_qubits=150)

    assert [device.device_id for device in devices] == ["ibm_fez"]
    assert devices[0].queue_depth == 7


class FakeHardwareProvider:
    provider_name = "fake"

    def __init__(self):
        self.submissions = 0

    def configured(self):
        return True

    def discover(self, required_qubits):
        return [
            DeviceCandidate(
                provider="fake",
                device_id="fake-qpu-12",
                name="Fake QPU",
                qubits=max(12, required_qubits),
                queue_depth=0,
                status="ONLINE",
                input_types=("qiskit",),
            )
        ]

    def submit(self, candidate, circuit, *, shots, classical_register):
        self.submissions += 1
        assert candidate.device_id == "fake-qpu-12"
        assert circuit.num_qubits <= candidate.qubits
        assert classical_register == "c"
        return ProviderExecutionResult(
            remote_job_id="fake-job-1",
            counts={"0": shots - 2, "1": 2},
            provider_status="COMPLETED",
            transpiled_circuit_metrics={
                "qubits": candidate.qubits,
                "depth": 10,
                "size": 20,
                "operationCounts": {"x": 1},
            },
        )


class FallbackHardwareProvider:
    def __init__(
        self,
        provider_name: str,
        *,
        qubits: int,
        failure: Exception | None = None,
    ):
        self.provider_name = provider_name
        self.qubits = qubits
        self.failure = failure
        self.submissions = 0

    def configured(self):
        return True

    def discover(self, required_qubits):
        return [
            DeviceCandidate(
                provider=self.provider_name,
                device_id=f"{self.provider_name}-qpu",
                name=f"{self.provider_name} QPU",
                qubits=max(self.qubits, required_qubits),
                queue_depth=0,
                status="ONLINE",
                input_types=("qiskit",),
            )
        ]

    def submit(self, candidate, circuit, *, shots, classical_register):
        self.submissions += 1
        if self.failure is not None:
            raise self.failure
        return ProviderExecutionResult(
            remote_job_id=f"{self.provider_name}-job-1",
            counts={"0": shots},
            provider_status="COMPLETED",
        )


def test_hardware_job_service_submits_once_and_returns_raw_unmitigated_counts(
    monkeypatch,
):
    monkeypatch.setenv("QDNA_REAL_HARDWARE_MAX_SHOTS", "16")
    provider = FakeHardwareProvider()
    service = HardwareJobService(
        providers=[provider],
        run_inline=True,
    )
    submission = HardwareSubmissionRequest(
        searchRequest=local_request("frqi", shots=32),
        confirmRealHardware=True,
    )

    job = service.create_job(submission)

    assert job.status == "completed"
    assert provider.submissions == 1
    assert job.result["execution"]["submittedShots"] == 16
    assert job.result["execution"]["errorMitigationApplied"] is False
    assert job.result["remoteJobId"] == "fake-job-1"
    assert job.result["selection"]["policy"] == "minimum_unused_qubits_then_queue_depth"


def test_hardware_job_service_falls_back_from_qbraid_to_ibm():
    qbraid = FallbackHardwareProvider(
        "qbraid",
        qubits=12,
        failure=HardwareProviderError(
            "qBraid hardware submission failed: ValueError"
        ),
    )
    ibm = FallbackHardwareProvider("ibm", qubits=156)
    service = HardwareJobService(
        providers=[qbraid, ibm],
        run_inline=True,
    )

    job = service.create_job(
        HardwareSubmissionRequest(
            searchRequest=local_request("frqi", shots=8),
            confirmRealHardware=True,
        )
    )

    assert job.status == "completed"
    assert qbraid.submissions == 1
    assert ibm.submissions == 1
    assert job.selected_device.provider == "ibm"
    assert job.result["provider"] == "ibm"
    assert job.result["remoteJobId"] == "ibm-job-1"
    assert job.result["selection"]["policy"] == "qbraid_to_ibm_fallback"
    assert job.result["providerErrors"] == [
        "qBraid attempt failed: qBraid hardware submission failed: ValueError"
    ]
    assert job.provider_errors == [
        "qBraid attempt failed: qBraid hardware submission failed: ValueError"
    ]


def test_hardware_job_service_reports_terminal_failure_after_both_providers_fail():
    qbraid = FallbackHardwareProvider(
        "qbraid",
        qubits=12,
        failure=HardwareProviderError(
            "qBraid hardware submission failed: ValueError"
        ),
    )
    ibm = FallbackHardwareProvider(
        "ibm",
        qubits=156,
        failure=HardwareProviderError("IBM hardware submission failed: TimeoutError"),
    )
    service = HardwareJobService(
        providers=[qbraid, ibm],
        run_inline=True,
    )

    job = service.create_job(
        HardwareSubmissionRequest(
            searchRequest=local_request("frqi", shots=8),
            confirmRealHardware=True,
        )
    )

    assert job.status == "failed"
    assert job.message == (
        "Hardware calls failed; no provider completed the real-hardware request"
    )
    assert job.error == (
        "Hardware calls failed. No configured hardware provider completed the request."
    )
    assert job.result is None
    assert qbraid.submissions == 1
    assert ibm.submissions == 1
    assert job.selected_device.provider == "ibm"
    assert job.provider_errors == [
        "qBraid attempt failed: qBraid hardware submission failed: ValueError",
        "IBM attempt failed: IBM hardware submission failed: TimeoutError",
    ]


def test_hardware_api_requires_confirmation_and_exposes_separate_results(monkeypatch):
    app_module = importlib.import_module("quantum_search_api.app")
    provider = FakeHardwareProvider()
    service = HardwareJobService(
        providers=[provider],
        run_inline=True,
    )
    monkeypatch.setattr(app_module, "hardware_jobs", service)
    client = TestClient(app_module.app)
    payload = local_request("frqi", shots=8).model_dump(by_alias=True)

    preview = client.post("/api/quantum-search/hardware/preview", json=payload)
    assert preview.status_code == 200
    assert preview.json()["submissionPerformed"] is False
    assert preview.json()["selectedDevice"]["deviceId"] == "fake-qpu-12"
    assert provider.submissions == 0

    denied = client.post(
        "/api/quantum-search/hardware/jobs",
        json={"searchRequest": payload, "confirmRealHardware": False},
    )
    assert denied.status_code == 400

    created = client.post(
        "/api/quantum-search/hardware/jobs",
        json={"searchRequest": payload, "confirmRealHardware": True},
    )
    assert created.status_code == 200
    job_id = created.json()["jobId"]

    status = client.get(f"/api/quantum-search/hardware/jobs/{job_id}")
    results = client.get(f"/api/quantum-search/hardware/jobs/{job_id}/results")
    assert status.json()["status"] == "completed"
    assert results.status_code == 200
    assert results.json()["execution"]["rawHardwareMeasurements"] is True
    assert "ideal" not in results.json()
    assert "mitigated" not in results.json()


def test_qbraid_discovery_error_does_not_expose_api_key():
    class BrokenClient:
        def __init__(self, **_kwargs):
            raise httpx.ConnectError("secret test-only")

    provider = QbraidHardwareProvider(
        api_key="must-not-appear",
        client_factory=BrokenClient,
    )

    with pytest.raises(Exception) as exc_info:
        provider.discover(required_qubits=1)
    assert "must-not-appear" not in str(exc_info.value)
