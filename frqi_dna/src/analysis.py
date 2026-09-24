"""High-level comparison API and theoretical validation."""

from __future__ import annotations

import json
from dataclasses import replace
from math import cos
from pathlib import Path

from .angle_mapping import angle_mapping_report, qiskit_ry_angle
from .comparison_circuit import build_comparison_circuit, build_measured_comparison_circuit
from .config import DEFAULT_ANGLE_MODE, DEFAULT_SEED, DEFAULT_SHOTS
from .frqi_encoding import build_frqi_dna_state
from .models import ComparisonResult
from .simulator import (
    circuit_metrics,
    run_shot_simulation,
    strip_probabilities_from_statevector,
)
from .validation import position_qubit_count, position_register_size, validate_sequence_pair
from .visualization import save_experiment_artifacts


def classical_frqi_overlap(
    reference: str, query: str, *, angle_mode: str = DEFAULT_ANGLE_MODE
) -> float:
    """Classically compute the expected FRQI branch overlap.

    With Qiskit RY(alpha), the DNA color state is
    cos(alpha/2)|0> + sin(alpha/2)|1>, so each position contributes
    cos((alpha_ref - alpha_query)/2).
    """

    ref, qry = validate_sequence_pair(reference, query)
    total = 0.0
    for ref_base, qry_base in zip(ref, qry):
        ref_angle = qiskit_ry_angle(ref_base, angle_mode=angle_mode)
        qry_angle = qiskit_ry_angle(qry_base, angle_mode=angle_mode)
        total += cos((ref_angle - qry_angle) / 2.0)
    return total / len(ref)


def classical_expected_p1(
    reference: str, query: str, *, angle_mode: str = DEFAULT_ANGLE_MODE
) -> float:
    """Return P(strip=1) expected from the branch-overlap formula."""

    overlap = classical_frqi_overlap(reference, query, angle_mode=angle_mode)
    return (1.0 - overlap) / 2.0


def compare_dna_frqi(
    reference: str,
    query: str,
    shots: int = DEFAULT_SHOTS,
    simulator_type: str = "aer",
    seed: int = DEFAULT_SEED,
    angle_mode: str = DEFAULT_ANGLE_MODE,
    output_dir: str | Path | None = None,
    save_circuits: bool = False,
) -> ComparisonResult:
    """Compare two DNA sequences using the paper's FRQI strip method."""

    if simulator_type != "aer":
        raise ValueError("only simulator_type='aer' is currently supported")

    ref, qry = validate_sequence_pair(reference, query)
    encoding = build_frqi_dna_state(ref, qry, angle_mode=angle_mode)
    unmeasured = build_comparison_circuit(ref, qry, angle_mode=angle_mode)
    measured = build_measured_comparison_circuit(ref, qry, angle_mode=angle_mode)

    theoretical_p0, theoretical_p1 = strip_probabilities_from_statevector(unmeasured)
    theoretical_similarity = 1.0 - 2.0 * theoretical_p1
    counts, transpiled, elapsed = run_shot_simulation(measured, shots=shots, seed=seed)
    p0 = counts["0"] / shots
    p1 = counts["1"] / shots
    similarity = 1.0 - 2.0 * p1
    clipped_similarity = min(1.0, max(-1.0, similarity))
    overlap = classical_frqi_overlap(ref, qry, angle_mode=angle_mode)
    classical_p1 = classical_expected_p1(ref, qry, angle_mode=angle_mode)

    result = ComparisonResult(
        reference=ref,
        query=qry,
        sequence_length=len(ref),
        position_qubits=position_qubit_count(len(ref)),
        position_register_states=position_register_size(len(ref)),
        non_power_of_two_strategy=(
            "exact uniform state over valid positions only; unused basis states have zero amplitude"
        ),
        shots=shots,
        seed=seed,
        angle_mode=angle_mode,
        angle_mapping=angle_mapping_report(),
        counts=counts,
        p0=p0,
        p1=p1,
        similarity=similarity,
        similarity_percentage=similarity * 100.0,
        clipped_similarity=clipped_similarity,
        clipped_similarity_percentage=clipped_similarity * 100.0,
        theoretical_p0=theoretical_p0,
        theoretical_p1=theoretical_p1,
        theoretical_similarity=theoretical_similarity,
        theoretical_similarity_percentage=theoretical_similarity * 100.0,
        classical_overlap=overlap,
        classical_p1=classical_p1,
        absolute_error=abs(p1 - theoretical_p1),
        circuit_metrics=circuit_metrics(measured),
        transpiled_circuit_metrics=circuit_metrics(transpiled),
        execution_time_seconds=elapsed,
        output_paths={},
    )

    if output_dir is not None:
        paths = save_experiment_artifacts(
            output_dir=Path(output_dir),
            reference=ref,
            query=qry,
            encoding_circuit=encoding,
            unmeasured_circuit=unmeasured,
            measured_circuit=measured,
            transpiled_circuit=transpiled,
            result=result,
            save_circuits=save_circuits,
        )
        result = replace(result, output_paths=paths)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        (Path(output_dir) / "result.json").write_text(
            json.dumps(result.to_dict(), indent=2), encoding="utf-8"
        )

    return result
