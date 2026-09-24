"""Complete analysis and artifact pipeline for coherent unknown-M search."""

from __future__ import annotations

import importlib.util
import json
from math import sqrt
from pathlib import Path
from typing import Iterable

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from .encoding import padded_length, position_qubit_count, validate_pair
from .fixed_point_hybrid import (
    FixedPointSchedule,
    build_fixed_point_circuits,
)
from .models import FixedPointAnalysisResult
from .simulator import circuit_metrics, position_probabilities, run_aer
from .visualization import (
    ibm_basis_example,
    save_alignment,
    save_circuit,
    save_fixed_point_success_curve,
    save_histogram,
    save_json,
    save_metrics_plot,
    save_phase_schedule,
    save_qasm3,
)


def _verification_positions(
    positions: Iterable[int], sequence_length: int
) -> list[int]:
    """Validate caller-supplied truth without deriving it from the sequences."""
    normalized = list(positions)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in normalized):
        raise TypeError("verification positions must be integer indices")
    if len(set(normalized)) != len(normalized):
        raise ValueError("verification positions must be unique")
    if any(value < 0 or value >= sequence_length for value in normalized):
        raise ValueError("verification position is outside the sequence")
    return sorted(normalized)


def _inferred_positions(
    probabilities: dict[str, float],
    *,
    sequence_length: int,
    width: int,
    shots: int,
) -> list[int]:
    uniform = 1.0 / sequence_length
    # Use a conservative four-sigma excess over the uniform null rather than
    # treating ordinary one-shot fluctuations as amplified positions.
    tolerance = 4.0 * sqrt(uniform * (1.0 - uniform) / shots)
    return [
        position
        for position in range(sequence_length)
        if probabilities[format(position, f"0{width}b")] > uniform + tolerance
    ]


def _probability_sum(
    probabilities: dict[str, float], positions: list[int], width: int
) -> float:
    return sum(probabilities[format(position, f"0{width}b")] for position in positions)


def _resource_estimate(
    reference: str, query: str, schedule: FixedPointSchedule
) -> dict[str, int | str]:
    one_bits = sum(base in {"C", "T"} for base in reference + query)
    one_bits += sum(base in {"G", "T"} for base in reference + query)
    return {
        "logical_sequence_table_bits": 4 * len(reference),
        "qrom_controlled_x_per_load": one_bits,
        "qrom_controlled_x_per_phase_oracle_load_and_unload": 2 * one_bits,
        "phase_oracle_calls_in_this_circuit": schedule.rounds,
        "qrom_controlled_x_across_all_phase_oracles": 2
        * one_bits
        * schedule.rounds,
        "asymptotic_warning": (
            "Explicit table loading is O(N) per phase oracle; this implementation "
            "does not establish end-to-end Grover speedup."
        ),
    }


def analyze_fixed_point_sequences(
    reference: str,
    query: str,
    *,
    verification_positions: Iterable[int],
    shots: int = 8192,
    seed: int = 12345,
    delta: float = 0.2,
    lambda_min: float | None = None,
    save_circuits: bool = False,
    output_dir: str | Path | None = None,
) -> FixedPointAnalysisResult:
    """Analyze coherent mismatch amplification without constructing from M.

    ``verification_positions`` is caller-supplied experiment truth used only
    after circuit construction to score the output. It is never passed to the
    QROM, comparator, oracle, source reflection, or phase scheduler.
    """
    ref, qry = validate_pair(reference, query)
    if shots < 1:
        raise ValueError("shots must be positive")

    # This is intentionally built before verification truth is normalized.
    circuits = build_fixed_point_circuits(
        ref, qry, delta=delta, lambda_min=lambda_min
    )
    schedule = circuits["schedule"]
    assert isinstance(schedule, FixedPointSchedule)
    truth = _verification_positions(verification_positions, len(ref))
    width = position_qubit_count(len(ref))

    preparation = circuits["position_preparation"]
    unmeasured = circuits["unmeasured"]
    measured = circuits["measured"]
    assert isinstance(preparation, QuantumCircuit)
    assert isinstance(unmeasured, QuantumCircuit)
    assert isinstance(measured, QuantumCircuit)

    before = position_probabilities(preparation, width)
    exact_after = position_probabilities(unmeasured, width)
    state = Statevector.from_instruction(unmeasured)
    work_probabilities = state.probabilities(
        qargs=list(range(width, unmeasured.num_qubits))
    )
    clean_work = float(work_probabilities[0])

    counts, transpiled, transpiled_stats = run_aer(
        measured, shots=shots, seed=seed
    )
    shot_probabilities = {
        format(position, f"0{width}b"): counts.get(
            format(position, f"0{width}b"), 0
        )
        / shots
        for position in range(1 << width)
    }
    inferred = _inferred_positions(
        shot_probabilities,
        sequence_length=len(ref),
        width=width,
        shots=shots,
    )
    exact_success = _probability_sum(exact_after, truth, width)
    shot_success = _probability_sum(shot_probabilities, truth, width)
    verified_fraction = len(truth) / len(ref)
    guarantee_applicable = bool(truth) and verified_fraction >= schedule.lambda_min
    guarantee_satisfied = (
        exact_success + 1e-12 >= schedule.guaranteed_success_probability
        if guarantee_applicable
        else None
    )
    exact_padding = sum(
        exact_after[format(position, f"0{width}b")]
        for position in range(len(ref), 1 << width)
    )
    shot_padding = sum(
        shot_probabilities[format(position, f"0{width}b")]
        for position in range(len(ref), 1 << width)
    )

    result = FixedPointAnalysisResult(
        reference=ref,
        query=qry,
        sequence_length=len(ref),
        padded_length=padded_length(len(ref)),
        position_indexing="zero-based",
        verification_positions_zero_based=truth,
        verification_truth_role=(
            "Caller-supplied only after circuit construction; used to score "
            "the experiment, never to synthesize the oracle or schedule."
        ),
        measurement_inferred_positions_zero_based=inferred,
        delta=delta,
        lambda_min=schedule.lambda_min,
        schedule=schedule.to_dict(),
        fixed_point_rounds=schedule.rounds,
        shots=shots,
        counts=counts,
        probabilities_before=before,
        exact_probabilities_after=exact_after,
        shot_probabilities_after=shot_probabilities,
        exact_verified_target_probability=exact_success,
        shot_verified_target_probability=shot_success,
        guaranteed_success_probability=schedule.guaranteed_success_probability,
        guarantee_applicable=guarantee_applicable,
        guarantee_satisfied_exactly=guarantee_satisfied,
        clean_work_probability=clean_work,
        invalid_padded_probability_exact=exact_padding,
        invalid_padded_probability_shots=shot_padding,
        circuit_metrics=circuit_metrics(measured),
        transpiled_metrics=transpiled_stats,
        register_layout={
            "position_qubits": width,
            "reference_basis_data_qubits": 2,
            "query_basis_data_qubits": 2,
            "different_flag_qubits": 1,
            "classical_position_bits": width,
            "logical_qubits": width + 5,
        },
        oracle_construction=(
            "Classical DNA symbols synthesize reversible basis-state QROM "
            "lookups. CNOT gates coherently compute two-bit XOR, a reversible "
            "OR sets the inequality flag, a target phase is applied, and every "
            "work operation is uncomputed. No mismatch-position list is used."
        ),
        amplification_construction=(
            "Yoder-Low-Chuang matched phases use delta and lambda_min=1/N by "
            "default. The actual M is not used to choose phases or rounds."
        ),
        backend="AerSimulator",
        seed=seed,
        supported_claims=[
            "Mismatch equality is evaluated coherently across position superposition.",
            "The circuit and fixed-point schedule are constructed without mismatch positions or M.",
            "The exact statevector verifies work-register uncomputation.",
            "The local experiment demonstrates fixed-point amplitude amplification.",
        ],
        limitations=[
            "Classical sequences are compiled into explicit QROM-style gates.",
            "Explicit lookup costs O(N) controlled operations per phase oracle.",
            "This simulator result is not evidence of quantum advantage.",
            "Real-QPU noise, connectivity, compilation overhead, and credit cost are not represented by exact simulation.",
            "Measurement frequency is not biological or clinical confidence.",
        ],
    )

    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        paths: dict[str, str] = {}
        paths["histogram_before"] = save_histogram(
            before,
            out / "histogram_before.png",
            "Before fixed-point amplification",
            truth,
        )
        paths["histogram_exact_after"] = save_histogram(
            exact_after,
            out / "histogram_exact_after.png",
            "After fixed-point amplification (exact statevector)",
            truth,
        )
        paths["histogram_shots_after"] = save_histogram(
            shot_probabilities,
            out / "histogram_shots_after.png",
            "After fixed-point amplification (Aer shots)",
            truth,
        )
        paths["alignment"] = save_alignment(ref, qry, out / "alignment.png")
        paths["metrics_summary"] = save_metrics_plot(
            result.circuit_metrics,
            result.transpiled_metrics,
            out / "circuit_metrics.png",
        )
        paths["phase_schedule_plot"] = save_phase_schedule(
            list(schedule.phases), out / "phase_schedule.png"
        )
        paths["success_curve_plot"] = save_fixed_point_success_curve(
            schedule.to_dict(),
            out / "fixed_point_success_curve.png",
            verified_lambda=verified_fraction if truth else None,
        )
        paths["phase_schedule_json"] = save_json(
            out / "phase_schedule.json", schedule.to_dict()
        )
        paths["verification_truth_json"] = save_json(
            out / "verification_truth.json",
            {
                "positions_zero_based": truth,
                "role": result.verification_truth_role,
                "not_used_by_circuit_construction": True,
            },
        )
        paths["measurement_inference_json"] = save_json(
            out / "measurement_inference.json",
            {
                "positions_zero_based": inferred,
                "rule": (
                    "valid shot probability > 1/N + "
                    "4*sqrt((1/N)*(1-1/N)/shots)"
                ),
                "does_not_use_verification_positions": True,
            },
        )
        paths["resource_estimate_json"] = save_json(
            out / "resource_estimate.json",
            _resource_estimate(ref, qry, schedule),
        )

        if save_circuits:
            circuit_names = {
                "position_preparation": circuits["position_preparation"],
                "qrom_pair_loader": circuits["qrom_pair_loader"],
                "xor_comparator": circuits["xor_comparator"],
                "coherent_mismatch_oracle": circuits[
                    "coherent_mismatch_oracle"
                ],
                "source_phase": circuits["source_phase"],
                "fixed_point_round_1": circuits["first_round"],
                "fixed_point_final_unmeasured": unmeasured,
                "fixed_point_final_measured": measured,
                "transpiled_aer": transpiled,
            }
            for stem, circuit in circuit_names.items():
                assert isinstance(circuit, QuantumCircuit)
                paths.update(save_circuit(circuit, out, stem))
            representative, representative_metrics = ibm_basis_example(measured)
            paths.update(
                save_circuit(
                    representative, out, "representative_hardware_basis"
                )
            )
            paths["representative_hardware_metrics_json"] = save_json(
                out / "representative_hardware_metrics.json",
                representative_metrics.__dict__,
            )
            paths["qbraid_openqasm3"] = save_qasm3(
                measured, out / "fixed_point_qbraid_ready.qasm3"
            )
            paths["qbraid_readiness_json"] = save_json(
                out / "qbraid_readiness.json",
                {
                    "qbraid_sdk_installed": importlib.util.find_spec("qbraid")
                    is not None,
                    "submitted": False,
                    "target_device": None,
                    "program_format": "OpenQASM 3",
                    "portable_lowered_basis": ["u", "cx", "measure"],
                    "requires_device_specific_transform": True,
                    "note": (
                        "Preparation artifact only. Select a compatible gate-model "
                        "QPU in qBraid and inspect transformed depth before explicit "
                        "credit-consuming submission."
                    ),
                },
            )

        paths["result_json"] = str(out / "result.json")
        paths["report_text"] = str(out / "report.txt")
        result.artifact_paths = paths
        save_json(out / "result.json", result.to_dict())
        report = [
            "Unknown-M coherent DNA fixed-point amplification report",
            "",
            f"Reference: {ref}",
            f"Query:     {qry}",
            f"Sequence length: {len(ref)}",
            f"Verification positions (zero-based; scoring only): {truth}",
            f"Measurement-inferred positions: {inferred}",
            f"Delta: {delta}",
            f"Lambda lower bound used by circuit: {schedule.lambda_min}",
            f"Fixed-point rounds: {schedule.rounds}",
            f"Guaranteed success when promise applies: {schedule.guaranteed_success_probability:.12f}",
            f"Exact verified target probability: {exact_success:.12f}",
            f"Shot verified target probability: {shot_success:.12f}",
            f"Guarantee applicable: {guarantee_applicable}",
            f"Guarantee satisfied exactly: {guarantee_satisfied}",
            f"Clean-work probability: {clean_work:.12f}",
            f"Exact padded-state probability: {exact_padding:.12e}",
            "",
            "Construction",
            result.oracle_construction,
            result.amplification_construction,
            "",
            "Supported claims",
            *[f"- {claim}" for claim in result.supported_claims],
            "",
            "Limitations",
            *[f"- {item}" for item in result.limitations],
            "",
            "Exact probabilities",
            json.dumps(exact_after, indent=2, sort_keys=True),
            "",
            "Shot probabilities",
            json.dumps(shot_probabilities, indent=2, sort_keys=True),
        ]
        (out / "report.txt").write_text(
            "\n".join(report) + "\n", encoding="utf-8"
        )
    return result
