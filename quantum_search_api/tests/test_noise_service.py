from __future__ import annotations

import math

import pytest

from quantum_search_api.services.noise.mitigation import (
    mitigate_readout_distribution,
    zero_noise_extrapolate,
)
from quantum_search_api.services.noise.noise_models import (
    GROVER_MAX_NOISY_GATE_OCCURRENCES,
    YLC_READOUT_MATRIX,
    build_frqi_noise_model,
    select_sparse_grover_noise_targets,
)
from quantum_search_api.services.noise.noise_runner import (
    MAX_GROVER_NOISE_SHOTS,
    run_noise_comparison,
)
from qgsa_grover.qgsa import build_qgsa_circuit
from qiskit import transpile


def test_frqi_noise_model_targets_transpiled_basis_gates():
    instructions = build_frqi_noise_model().to_dict()["errors"]
    noisy_operations = {
        operation
        for error in instructions
        for operation in error.get("operations", [])
    }
    assert {"u", "cx"} <= noisy_operations


def test_grover_noise_is_sparse_bounded_and_has_consistent_schema():
    result = run_noise_comparison(
        algorithm="grover",
        query_sequence="A",
        target_sequence="A",
        shots=512,
    )
    assert set(result) >= {
        "algorithm",
        "noiseType",
        "mitigation",
        "ideal",
        "noisy",
        "mitigated",
        "circuitMetrics",
        "noiseParameters",
    }
    assert len(result["noiseScaleResults"]) == 3
    assert result["shots"] == MAX_GROVER_NOISE_SHOTS
    assert result["requestedShots"] == 512
    assert result["noiseParameters"]["shotCapApplied"] is True
    assert (
        0
        < result["noiseParameters"]["affectedGateOccurrences"]
        <= GROVER_MAX_NOISY_GATE_OCCURRENCES
    )
    assert result["noiseParameters"]["coverageFraction"] < 1
    assert result["noiseParameters"]["simulatorMethod"] == "matrix_product_state"
    assert "Sparse sensitivity experiment" in result["noiseModelScope"]


def test_sparse_grover_target_selection_stays_within_occurrence_budget():
    circuit, _ = build_qgsa_circuit(
        target="ACG",
        pattern="CG",
        iterations="auto",
        boundary_mode="boundary_safe",
        measured=True,
    )
    compiled = transpile(
        circuit,
        basis_gates=["u", "cx"],
        optimization_level=3,
        seed_transpiler=42,
    )
    targets = select_sparse_grover_noise_targets(compiled)
    assert targets["affectedGateOccurrences"] == 3
    assert targets["maximumAffectedGateOccurrences"] == 4
    assert targets["totalEligibleGateOccurrences"] > 3


def test_zero_noise_extrapolation_is_finite_probability():
    value = zero_noise_extrapolate([1.0, 2.0, 3.0], [0.72, 0.64, 0.57])
    assert math.isfinite(value)
    assert 0.0 <= value <= 1.0


def test_ylc_readout_correction_is_normalized():
    corrected = mitigate_readout_distribution(
        {"00": 0.5, "01": 0.2, "10": 0.2, "11": 0.1},
        2,
        YLC_READOUT_MATRIX,
    )
    assert sum(corrected.values()) == pytest.approx(1.0)
    assert all(value >= 0.0 for value in corrected.values())


def test_noise_runner_rejects_invalid_algorithm():
    with pytest.raises(ValueError, match="Unsupported noise algorithm"):
        run_noise_comparison(
            algorithm="not-an-algorithm",
            query_sequence="A",
            target_sequence="A",
            shots=16,
        )


def test_all_algorithm_responses_share_comparison_sections():
    for algorithm in ("frqi", "hybrid"):
        result = run_noise_comparison(
            algorithm=algorithm,
            query_sequence="A",
            target_sequence="A",
            shots=32,
            expected_states=[0],
        )
        assert all(section in result for section in ("ideal", "noisy", "mitigated"))
        assert all(
            "successProbability" in result[section]
            for section in ("ideal", "noisy", "mitigated")
        )


def test_custom_noise_parameters_are_applied_to_response():
    frqi = run_noise_comparison(
        algorithm="frqi",
        query_sequence="A",
        target_sequence="A",
        shots=32,
        noise_parameters={"singleQubitError": 0.01, "twoQubitError": 0.02},
    )
    assert frqi["noiseParameters"]["singleQubitError"] == 0.01
    assert frqi["noiseParameters"]["twoQubitError"] == 0.02

    hybrid = run_noise_comparison(
        algorithm="hybrid",
        query_sequence="A",
        target_sequence="A",
        shots=32,
        expected_states=[0],
        noise_parameters={"readoutZeroToOne": 0.08, "readoutOneToZero": 0.06},
    )
    assert hybrid["noiseParameters"]["readoutZeroToOne"] == 0.08
    assert hybrid["noiseParameters"]["readoutOneToZero"] == 0.06
