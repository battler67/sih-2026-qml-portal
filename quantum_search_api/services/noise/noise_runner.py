from __future__ import annotations

from typing import Any

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from frqi_dna.src.comparison_circuit import build_measured_comparison_circuit
from qgsa_grover.analysis import counts_to_probabilities, success_and_false_positive
from qgsa_grover.qgsa import build_qgsa_circuit
from quantum_search_api.services.quantum.hybrid_search import build_hybrid_fixed_point_circuits

from .mitigation import mitigate_readout_distribution, zero_noise_extrapolate
from .noise_models import (
    FRQI_SINGLE_QUBIT_ERROR,
    FRQI_TWO_QUBIT_ERROR,
    GROVER_SINGLE_QUBIT_ERROR,
    GROVER_TWO_QUBIT_ERROR,
    GROVER_MAX_NOISY_GATE_OCCURRENCES,
    YLC_ONE_TO_ZERO_ERROR,
    YLC_ZERO_TO_ONE_ERROR,
    build_frqi_noise_model,
    build_sparse_grover_noise_model,
    build_ylc_readout_noise_model,
    readout_matrix,
    select_sparse_grover_noise_targets,
)


SEED = 42
MAX_NOISE_QUBITS = 24
MAX_GROVER_NOISE_SHOTS = 128


def _probabilities(counts: dict[str, int], shots: int) -> dict[str, float]:
    return {key: value / shots for key, value in counts.items()}


def _run(
    circuit: QuantumCircuit,
    shots: int,
    *,
    noise_model=None,
) -> tuple[dict[str, int], QuantumCircuit]:
    backend = AerSimulator(noise_model=noise_model, seed_simulator=SEED)
    compiled = transpile(
        circuit,
        basis_gates=["u", "cx"],
        optimization_level=3,
        seed_transpiler=SEED,
    )
    raw = backend.run(compiled, shots=shots).result().get_counts()
    counts = {
        key.replace(" ", ""): int(value)
        for key, value in sorted(raw.items())
    }
    return counts, compiled


def _run_compiled(
    compiled: QuantumCircuit,
    shots: int,
    *,
    noise_model=None,
    method: str = "automatic",
) -> dict[str, int]:
    backend = AerSimulator(
        noise_model=noise_model,
        seed_simulator=SEED,
        method=method,
    )
    raw = backend.run(compiled, shots=shots).result().get_counts()
    return {
        key.replace(" ", ""): int(value)
        for key, value in sorted(raw.items())
    }


def _metrics(original: QuantumCircuit, compiled: QuantumCircuit) -> dict[str, int]:
    operations = compiled.count_ops()
    return {
        "originalDepth": original.depth(),
        "transpiledDepth": compiled.depth(),
        "originalSize": original.size(),
        "transpiledSize": compiled.size(),
        "cxCount": int(operations.get("cx", 0)),
        "qubits": original.num_qubits,
    }


def _section(
    counts: dict[str, int],
    probabilities: dict[str, float],
    success: float,
    false_positive: float,
    **extra: Any,
) -> dict[str, Any]:
    top_state = max(probabilities, key=probabilities.get) if probabilities else None
    return {
        "counts": counts,
        "probabilities": probabilities,
        "successProbability": float(success),
        "falsePositiveProbability": float(false_positive),
        "topState": top_state,
        **extra,
    }


def _frqi(
    reference: str,
    query: str,
    shots: int,
    *,
    single_qubit_error: float,
    two_qubit_error: float,
) -> dict[str, Any]:
    circuit = build_measured_comparison_circuit(reference, query)
    ideal_counts, _ = _run(circuit, shots)
    noisy_counts, compiled = _run(
        circuit,
        shots,
        noise_model=build_frqi_noise_model(single_qubit_error, two_qubit_error),
    )
    ideal_probs = _probabilities(ideal_counts, shots)
    noisy_probs = _probabilities(noisy_counts, shots)
    ideal_p1 = ideal_probs.get("1", 0.0)
    noisy_p1 = noisy_probs.get("1", 0.0)
    ideal_similarity = min(1.0, max(-1.0, 1.0 - 2.0 * ideal_p1))
    noisy_similarity = min(1.0, max(-1.0, 1.0 - 2.0 * noisy_p1))
    return {
        "algorithm": "frqi",
        "noiseType": "rotation_and_controlled_gate_depolarizing",
        "mitigation": "optimization_level_3",
        "shots": shots,
        "metricLabel": "Strip |1> probability",
        "ideal": _section(
            ideal_counts, ideal_probs, ideal_p1, 1.0 - ideal_p1, similarity=ideal_similarity
        ),
        "noisy": _section(
            noisy_counts, noisy_probs, noisy_p1, 1.0 - noisy_p1, similarity=noisy_similarity
        ),
        "mitigated": _section(
            noisy_counts, noisy_probs, noisy_p1, 1.0 - noisy_p1, similarity=noisy_similarity
        ),
        "circuitMetrics": _metrics(circuit, compiled),
        "noiseParameters": {
            "singleQubitError": single_qubit_error,
            "twoQubitError": two_qubit_error,
        },
    }


def _grover(
    reference: str,
    query: str,
    shots: int,
    boundary_mode: str,
    *,
    single_qubit_error: float,
    two_qubit_error: float,
) -> dict[str, Any]:
    circuit, metadata = build_qgsa_circuit(
        target=reference,
        pattern=query,
        iterations="auto",
        boundary_mode=boundary_mode,
        measured=True,
    )
    if circuit.num_qubits > MAX_NOISE_QUBITS:
        raise ValueError(
            f"Noise simulation is limited to {MAX_NOISE_QUBITS} qubits; "
            f"this Grover circuit requires {circuit.num_qubits}."
        )
    effective_shots = min(shots, MAX_GROVER_NOISE_SHOTS)
    compiled = transpile(
        circuit,
        basis_gates=["u", "cx"],
        optimization_level=3,
        seed_transpiler=SEED,
    )
    sparse_targets = select_sparse_grover_noise_targets(
        compiled,
        max_gate_occurrences=GROVER_MAX_NOISY_GATE_OCCURRENCES,
    )
    if sparse_targets["affectedGateOccurrences"] == 0:
        raise ValueError(
            "The transpiled Grover circuit has no eligible sparse-noise gate location"
        )
    ideal_counts = _run_compiled(
        compiled,
        effective_shots,
        method="matrix_product_state",
    )
    width = int(metadata["index_qubits"])
    ideal_probs = counts_to_probabilities(ideal_counts, effective_shots, width)
    matches = list(metadata["classical_matches"])
    valid = list(metadata["valid_positions"])
    ideal_success, ideal_false = success_and_false_positive(ideal_probs, matches, valid)
    samples: list[dict[str, float]] = []
    noisy_counts: dict[str, int] = {}
    noisy_probs: dict[str, float] = {}
    noisy_success = noisy_false = 0.0
    for scale in (1.0, 2.0, 3.0):
        counts = _run_compiled(
            compiled,
            effective_shots,
            noise_model=build_sparse_grover_noise_model(
                sparse_targets,
                scale,
                single_qubit_error=single_qubit_error,
                two_qubit_error=two_qubit_error,
            ),
            method="matrix_product_state",
        )
        probabilities = counts_to_probabilities(counts, effective_shots, width)
        success, false_positive = success_and_false_positive(probabilities, matches, valid)
        samples.append(
            {
                "scaleFactor": scale,
                "successProbability": success,
                "falsePositiveProbability": false_positive,
            }
        )
        if scale == 1.0:
            noisy_counts, noisy_probs = counts, probabilities
            noisy_success, noisy_false = success, false_positive
    mitigated_success = zero_noise_extrapolate(
        [sample["scaleFactor"] for sample in samples],
        [sample["successProbability"] for sample in samples],
    )
    mitigated_false = zero_noise_extrapolate(
        [sample["scaleFactor"] for sample in samples],
        [sample["falsePositiveProbability"] for sample in samples],
    )
    return {
        "algorithm": "grover",
        "noiseType": "sparse_targeted_depolarizing",
        "mitigation": "linear_zero_noise_extrapolation",
        "shots": effective_shots,
        "requestedShots": shots,
        "metricLabel": "Valid target probability",
        "ideal": _section(ideal_counts, ideal_probs, ideal_success, ideal_false),
        "noisy": _section(noisy_counts, noisy_probs, noisy_success, noisy_false),
        "mitigated": _section({}, {}, mitigated_success, mitigated_false),
        "noiseScaleResults": samples,
        "circuitMetrics": _metrics(circuit, compiled),
        "noiseModelScope": (
            "Sparse sensitivity experiment: depolarizing errors are applied only to "
            "the least-used transpiled gate locations, not to the full circuit."
        ),
        "noiseParameters": {
            "singleQubitError": single_qubit_error,
            "twoQubitError": two_qubit_error,
            "scaleFactors": [1, 2, 3],
            "requestedShots": shots,
            "executedShots": effective_shots,
            "maximumNoiseShots": MAX_GROVER_NOISE_SHOTS,
            "shotCapApplied": effective_shots < shots,
            "simulatorMethod": "matrix_product_state",
            "scope": "least_used_transpiled_gate_locations",
            **sparse_targets,
        },
    }


def _hybrid(
    reference: str,
    query: str,
    shots: int,
    expected_states: list[int],
    *,
    readout_zero_to_one: float,
    readout_one_to_zero: float,
) -> dict[str, Any]:
    circuits = build_hybrid_fixed_point_circuits(reference, query)
    circuit = circuits["measured"]
    assert isinstance(circuit, QuantumCircuit)
    if circuit.num_qubits > MAX_NOISE_QUBITS:
        raise ValueError(
            f"Noise simulation is limited to {MAX_NOISE_QUBITS} qubits; "
            f"this YLC circuit requires {circuit.num_qubits}."
        )
    width = max(1, (len(query) - 1).bit_length())
    ideal_counts, _ = _run(circuit, shots)
    assignment = readout_matrix(readout_zero_to_one, readout_one_to_zero)
    noisy_counts, compiled = _run(
        circuit,
        shots,
        noise_model=build_ylc_readout_noise_model(
            readout_zero_to_one,
            readout_one_to_zero,
        ),
    )
    ideal_probs = _probabilities(ideal_counts, shots)
    noisy_probs = _probabilities(noisy_counts, shots)
    mitigated_probs = mitigate_readout_distribution(noisy_probs, width, assignment)
    expected_keys = {format(index, f"0{width}b") for index in expected_states}

    def score(values: dict[str, float]) -> tuple[float, float]:
        success = sum(values.get(key, 0.0) for key in expected_keys)
        return success, max(0.0, 1.0 - success)

    ideal_success, ideal_false = score(ideal_probs)
    noisy_success, noisy_false = score(noisy_probs)
    mitigated_success, mitigated_false = score(mitigated_probs)
    return {
        "algorithm": "hybrid",
        "noiseType": "measurement_readout_error",
        "mitigation": "local_assignment_matrix_inversion",
        "shots": shots,
        "metricLabel": "Expected output probability",
        "ideal": _section(ideal_counts, ideal_probs, ideal_success, ideal_false),
        "noisy": _section(noisy_counts, noisy_probs, noisy_success, noisy_false),
        "mitigated": _section(
            {}, mitigated_probs, mitigated_success, mitigated_false
        ),
        "circuitMetrics": _metrics(circuit, compiled),
        "noiseParameters": {
            "readoutZeroToOne": readout_zero_to_one,
            "readoutOneToZero": readout_one_to_zero,
            "readoutMatrix": [list(row) for row in assignment],
        },
    }


def run_noise_comparison(
    *,
    algorithm: str,
    query_sequence: str,
    target_sequence: str,
    shots: int,
    grover_boundary_mode: str = "boundary_safe",
    expected_states: list[int] | None = None,
    noise_parameters: dict[str, float] | None = None,
) -> dict[str, Any]:
    parameters = noise_parameters or {}
    if algorithm == "frqi":
        result = _frqi(
            target_sequence,
            query_sequence,
            shots,
            single_qubit_error=parameters.get(
                "singleQubitError", FRQI_SINGLE_QUBIT_ERROR
            ),
            two_qubit_error=parameters.get(
                "twoQubitError", FRQI_TWO_QUBIT_ERROR
            ),
        )
    elif algorithm == "grover":
        result = _grover(
            target_sequence,
            query_sequence,
            shots,
            grover_boundary_mode,
            single_qubit_error=parameters.get(
                "singleQubitError", GROVER_SINGLE_QUBIT_ERROR
            ),
            two_qubit_error=parameters.get(
                "twoQubitError", GROVER_TWO_QUBIT_ERROR
            ),
        )
    elif algorithm == "hybrid":
        result = _hybrid(
            target_sequence,
            query_sequence,
            shots,
            expected_states or [],
            readout_zero_to_one=parameters.get(
                "readoutZeroToOne", YLC_ZERO_TO_ONE_ERROR
            ),
            readout_one_to_zero=parameters.get(
                "readoutOneToZero", YLC_ONE_TO_ZERO_ERROR
            ),
        )
    else:
        raise ValueError(f"Unsupported noise algorithm: {algorithm}")
    return {
        **result,
        "simulator": "Qiskit Aer shot-based simulation",
        "hardwareRun": False,
        "bitOrder": "Qiskit classical bitstrings are displayed most-significant bit first",
    }
