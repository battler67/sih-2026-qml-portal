"""End-to-end future-integration-friendly sequence-analysis API."""

from __future__ import annotations

import json
from pathlib import Path

from .baseline_similarity import build_baseline_circuit, run_baseline
from .encoding import classical_mutations, padded_length, position_qubit_count, validate_pair
from .frqi_state import build_sequence_frqi_state
from .grover_amplification import build_localization_circuits
from .models import AnalysisResult, MutationResult
from .simulator import circuit_metrics, position_probabilities, run_aer
from .visualization import (
    ibm_basis_example,
    save_alignment,
    save_circuit,
    save_histogram,
    save_json,
    save_metrics_plot,
)


def _status(length: int, marked: int) -> str:
    if marked == 0:
        return "no mutations detected; Grover amplification skipped"
    if marked == length:
        return "all positions are mutations; amplification cannot improve localization"
    return "generalized FRQI-state amplitude amplification executed"


def _infer_amplified_positions(
    probabilities: dict[str, float],
    *,
    sequence_length: int,
    position_width: int,
    marked_count: int,
    iterations: int,
    shots: int,
) -> list[int]:
    """Infer peaks from shot probabilities without relabeling oracle truth.

    A state is called amplified only when it is above the uniform valid-state
    probability by more than one shot. For the M=N special case all valid
    positions are returned because every position is marked by definition.
    """
    if marked_count == 0:
        return []
    if marked_count == sequence_length:
        return list(range(sequence_length))
    if iterations == 0:
        return []
    uniform = 1.0 / sequence_length
    tolerance = 1.0 / shots
    return [
        i
        for i in range(sequence_length)
        if probabilities[format(i, f"0{position_width}b")] > uniform + tolerance
    ]


def analyze_sequences(
    reference: str,
    query: str,
    shots: int = 8192,
    backend_type: str = "aer_simulator",
    *,
    seed: int = 12345,
    save_circuits: bool = False,
    output_dir: str | Path | None = None,
) -> AnalysisResult:
    """Analyze equal-length DNA substitutions using baseline FRQI and Grover.

    Mismatch positions and the iteration count are classically precomputed for
    this proof of concept. The quantum circuit samples the amplified position
    distribution; its frequencies are not clinical confidence estimates.
    """
    ref, qry = validate_pair(reference, query)
    if backend_type not in {"aer", "aer_simulator"}:
        raise ValueError("backend_type must be 'aer' or 'aer_simulator'; hardware preparation is separate")
    if shots < 1:
        raise ValueError("shots must be positive")
    marked = classical_mutations(ref, qry)
    circuits = build_localization_circuits(ref, qry)
    width = position_qubit_count(len(ref))
    before = position_probabilities(circuits["preparation"], width)
    exact_after = position_probabilities(circuits["unmeasured"], width)
    counts, transpiled, transpiled_stats = run_aer(circuits["measured"], shots=shots, seed=seed)
    probabilities = {format(i, f"0{width}b"): counts.get(format(i, f"0{width}b"), 0) / shots for i in range(1 << width)}
    detected = _infer_amplified_positions(
        probabilities,
        sequence_length=len(ref),
        position_width=width,
        marked_count=len(marked),
        iterations=int(circuits["iterations"]),
        shots=shots,
    )
    baseline, _ = run_baseline(ref, qry, shots, seed)
    mutation_results = [
        MutationResult(
            position_zero_based=i,
            position_one_based=i + 1,
            reference_base=ref[i],
            query_base=qry[i],
            substitution=f"{ref[i]}->{qry[i]}",
            counts=counts.get(format(i, f"0{width}b"), 0),
            probability=probabilities[format(i, f"0{width}b")],
            probability_before=before[format(i, f"0{width}b")],
        )
        for i in marked
    ]
    result = AnalysisResult(
        reference=ref,
        query=qry,
        sequence_length=len(ref),
        padded_length=padded_length(len(ref)),
        position_indexing="zero-based internally; both zero- and one-based values reported",
        mutations=mutation_results,
        similarity_percentage=100 * (len(ref) - len(marked)) / len(ref),
        baseline_frqi=baseline,
        grover_iterations=int(circuits["iterations"]),
        amplification_status=_status(len(ref), len(marked)),
        shots=shots,
        counts=counts,
        probabilities=probabilities,
        probabilities_before=before,
        oracle_marked_positions_zero_based=marked,
        measured_detected_positions_zero_based=detected,
        invalid_padded_probability=sum(probabilities[format(i, f"0{width}b")] for i in range(len(ref), 1 << width)),
        circuit_metrics=circuit_metrics(circuits["measured"]),
        transpiled_metrics=transpiled_stats,
        register_layout={"position_qubits": width, "reference_color_qubits": 1, "query_color_qubits": 1, "classical_position_bits": width, "logical_qubits": width + 2},
        oracle_construction="Classically identify finite-alphabet mismatches, then synthesize reversible position-controlled phase flips; FRQI color qubits remain in A.",
        diffuser="Generalized prepared-state reflection D_A = A S_0 A† (up to a physically irrelevant global phase).",
        backend="AerSimulator",
        seed=seed,
        warnings=[
            "FRQI angle states are generally nonorthogonal; the oracle does not infer bases from one color qubit.",
            "Classical preprocessing supplies mismatch positions and M for iteration selection.",
            "Shot frequency is a simulator sampling result, not clinical mutation confidence.",
        ],
    )
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        paths: dict[str, str] = {}
        paths["histogram_before"] = save_histogram(before, out / "histogram_before.png", "Before amplitude amplification", marked)
        paths["histogram_after"] = save_histogram(probabilities, out / "histogram_after.png", "After amplitude amplification (Aer shots)", marked)
        paths["alignment"] = save_alignment(ref, qry, out / "alignment.png")
        paths["metrics_summary"] = save_metrics_plot(result.circuit_metrics, result.transpiled_metrics, out / "circuit_metrics.png")
        paths["expected_mutations_json"] = save_json(
            out / "expected_mutations.json",
            {"classical_expected_positions_zero_based": marked},
        )
        paths["detected_mutations_json"] = save_json(
            out / "detected_mutations.json",
            {
                "oracle_marked_positions_zero_based": marked,
                "measurement_inferred_amplified_positions_zero_based": detected,
                "inference_rule": "valid-position shot probability > 1/N + 1/shots",
            },
        )
        if save_circuits:
            ref_circuit = build_sequence_frqi_state(ref, "reference_frqi")
            qry_circuit = build_sequence_frqi_state(qry, "query_frqi")
            baseline_circuit = build_baseline_circuit(ref, qry)
            named = {
                "baseline_frqi": baseline_circuit,
                "reference_frqi": ref_circuit,
                "query_frqi": qry_circuit,
                "combined_frqi_state": circuits["preparation"],
                "mutation_oracle": circuits["oracle"],
                "generalized_diffuser": circuits["diffuser"],
                "grover_iteration": circuits["iteration"],
                "final_circuit": circuits["measured"],
                "transpiled_aer": transpiled,
            }
            for stem, circuit in named.items():
                paths.update(save_circuit(circuit, out, stem))
            ibm_example, ibm_metrics = ibm_basis_example(circuits["measured"])
            paths.update(save_circuit(ibm_example, out, "transpiled_ibm_basis"))
            paths["ibm_basis_metrics_json"] = save_json(
                out / "ibm_basis_metrics.json", ibm_metrics.__dict__
            )
        paths["result_json"] = str(out / "result.json")
        paths["report_text"] = str(out / "report.txt")
        result.artifact_paths = paths
        save_json(out / "result.json", result.to_dict())
        report = [
            "FRQI–Grover mutation-localization simulator report",
            f"Reference: {ref}",
            f"Query:     {qry}",
            f"Mutations (zero-based): {marked}",
            f"Measurement-inferred amplified positions: {detected}",
            f"Similarity: {result.similarity_percentage:.3f}%",
            f"Grover iterations: {result.grover_iterations}",
            f"Status: {result.amplification_status}",
            f"Exact post-amplification probabilities: {json.dumps(exact_after, sort_keys=True)}",
            f"Shot probabilities: {json.dumps(probabilities, sort_keys=True)}",
        ]
        (out / "report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    return result
