"""Optional, explicit IBM Runtime adapter with simulator-safe lazy imports."""

from __future__ import annotations

import os
from typing import Any

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from .simulator import circuit_metrics


def _aer_fallback(circuit: QuantumCircuit, reason: str) -> dict[str, Any]:
    """Return a local preparation result when IBM access is unavailable."""
    backend = AerSimulator()
    compiled = transpile(circuit, backend=backend, optimization_level=1)
    return {
        "backend_name": backend.name,
        "transpiled_circuit": compiled,
        "metrics": circuit_metrics(compiled),
        "layout": str(getattr(compiled, "layout", None)),
        "submitted": False,
        "simulator_fallback": True,
        "fallback_reason": reason,
        "note": "Local Aer fallback; no remote job was submitted.",
    }


def _runtime_backend(backend_name: str | None = None):
    """Resolve IBM Runtime and backend using environment or saved credentials."""
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError as exc:
        raise RuntimeError("qiskit-ibm-runtime is not installed") from exc
    token = os.getenv("IBM_QUANTUM_TOKEN")
    channel = os.getenv("IBM_QUANTUM_CHANNEL", "ibm_quantum_platform")
    instance = os.getenv("IBM_QUANTUM_INSTANCE")
    selected = backend_name or os.getenv("IBM_QUANTUM_BACKEND")
    kwargs: dict[str, str] = {"channel": channel}
    if token:
        kwargs["token"] = token
    if instance:
        kwargs["instance"] = instance
    service = QiskitRuntimeService(**kwargs) if kwargs != {"channel": channel} else QiskitRuntimeService()
    backend = service.backend(selected) if selected else service.least_busy(operational=True, simulator=False)
    return backend


def prepare_for_ibm_backend(
    circuit: QuantumCircuit,
    backend_name: str | None = None,
    *,
    simulator_fallback: bool = True,
) -> dict[str, Any]:
    """Transpile for IBM without submitting; optionally fall back to local Aer."""
    try:
        backend = _runtime_backend(backend_name)
    except Exception as exc:
        if simulator_fallback:
            return _aer_fallback(circuit, str(exc))
        raise
    compiled = transpile(circuit, backend=backend, optimization_level=3)
    layout = str(getattr(compiled, "layout", None))
    return {
        "backend_name": backend.name,
        "transpiled_circuit": compiled,
        "metrics": circuit_metrics(compiled),
        "layout": layout,
        "submitted": False,
        "simulator_fallback": False,
        "note": "Preparation only. Real execution requires a separate explicit submission step.",
    }


def submit_to_ibm_hardware(
    circuit: QuantumCircuit,
    *,
    backend_name: str | None = None,
    shots: int = 8192,
    confirm_real_hardware: bool = False,
):
    """Explicitly submit through Runtime SamplerV2 only after confirmation.

    This function can consume paid allocation. It is never called by simulator
    analysis, examples, tests, or artifact generation.
    """
    if not confirm_real_hardware:
        raise ValueError("set confirm_real_hardware=True to authorize real IBM hardware submission")
    if shots < 1:
        raise ValueError("shots must be positive")
    from qiskit_ibm_runtime import SamplerV2

    backend = _runtime_backend(backend_name)
    compiled = transpile(circuit, backend=backend, optimization_level=3)
    sampler = SamplerV2(mode=backend)
    return sampler.run([compiled], shots=shots)
