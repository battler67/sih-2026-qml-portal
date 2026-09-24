"""Public QGSA circuit builder and search runner."""

from __future__ import annotations

import time
from pathlib import Path

from qiskit import QuantumCircuit

from .analysis import (
    counts_to_probabilities,
    index_probabilities_from_statevector,
    most_probable_positions,
    success_and_false_positive,
)
from .classical_baseline import classical_exact_matches
from .comparator import build_comparator_circuit
from .config import DNA_2BIT_ENCODING, DNA_3BIT_TERMINATOR_ENCODING, DEFAULT_SEED, DEFAULT_SHOTS
from .cyclic_shift import build_cyclic_shift_operator
from .diffuser import build_diffuser_circuit
from .encoding import bits_per_symbol, encode_sequence, encoding_table
from .grover_iteration import append_grover_iteration, resolve_iterations
from .initialization import build_initial_qgsa_state, build_initialization_circuit
from .models import QGSAResult
from .optique import build_optique_circuit, compare_original_and_optimized
from .oracle import build_qgsa_oracle
from .registers import REGISTER_ORDERING_NOTE, create_registers
from .simulator import circuit_metrics, run_shot_simulation
from .validation import (
    index_qubit_count,
    next_power_of_two,
    search_space_for,
    valid_positions_for,
    validate_search_inputs,
)
from .visualization import ensure_dir, save_circuit_artifacts, save_histogram, save_json, write_report


def _prepared_target(target: str, boundary_mode: str, encoding_mode: str) -> tuple[str, str, int, list[str]]:
    warnings: list[str] = []
    if boundary_mode == "boundary_safe":
        padded_length = next_power_of_two(len(target))
        if encoding_mode == "paper_2bit":
            encoding_mode = "terminator_3bit"
            warnings.append(
                "boundary_safe mode switched from paper_2bit to the documented engineering terminator_3bit encoding."
            )
        padded = target + "$" * (padded_length - len(target))
        return padded, encoding_mode, padded_length, warnings
    return target, encoding_mode, len(target), warnings


def build_qgsa_circuit(
    *,
    target: str,
    pattern: str,
    iterations="auto",
    encoding_mode: str = "paper_2bit",
    boundary_mode: str = "paper_cyclic",
    measured: bool = False,
) -> tuple[QuantumCircuit, dict]:
    target_n, pattern_n = validate_search_inputs(target, pattern, boundary_mode=boundary_mode)
    target_for_circuit, actual_encoding, target_symbols, prep_warnings = _prepared_target(
        target_n, boundary_mode, encoding_mode
    )
    bps = bits_per_symbol(actual_encoding)
    search_space = search_space_for(len(target_n), boundary_mode)
    idx_qubits = index_qubit_count(search_space)
    valid_positions = valid_positions_for(len(target_n), len(pattern_n), boundary_mode)
    classical_matches = classical_exact_matches(target_n, pattern_n)
    warnings = list(prep_warnings)
    executed, paper_value = resolve_iterations(
        iterations,
        target_length=len(target_n),
        pattern_length=len(pattern_n),
        search_space_size=2**idx_qubits,
        solution_count=len(classical_matches),
        warnings=warnings,
    )
    circuit, regs = create_registers(
        index_qubits=idx_qubits,
        target_symbols=target_symbols,
        pattern_symbols=len(pattern_n),
        bits_per_symbol=bps,
        measured=measured,
    )
    build_initial_qgsa_state(
        circuit,
        regs,
        target=target_for_circuit,
        pattern=pattern_n,
        encoding_mode=actual_encoding,
    )
    oracle_valid = valid_positions if boundary_mode == "boundary_safe" else None
    for _ in range(executed):
        append_grover_iteration(circuit, regs, valid_indices=oracle_valid)
    if measured and regs.classical_index is not None:
        circuit.measure(regs.index, regs.classical_index)
    metadata = {
        "target": target_n,
        "target_for_circuit": target_for_circuit,
        "pattern": pattern_n,
        "encoding_mode": actual_encoding,
        "bits_per_symbol": bps,
        "search_space_size": 2**idx_qubits,
        "valid_positions": valid_positions,
        "classical_matches": classical_matches,
        "index_qubits": idx_qubits,
        "iterations_executed": executed,
        "paper_iteration_formula_value": paper_value,
        "warnings": warnings,
        "register_ordering": REGISTER_ORDERING_NOTE,
    }
    return circuit, metadata


def _save_requested_artifacts(
    *,
    output_dir: str | Path,
    full_unmeasured,
    measured,
    transpiled,
    metadata: dict,
    counts: dict[str, int],
    probabilities: dict[str, float],
    statevector_analysis: dict,
) -> dict[str, str]:
    out = ensure_dir(output_dir)
    paths: dict[str, str] = {}
    init = build_initialization_circuit(
        index_qubits=metadata["index_qubits"],
        target=metadata["target_for_circuit"],
        pattern=metadata["pattern"],
        target_symbols=len(metadata["target_for_circuit"]),
        bits_per_symbol=metadata["bits_per_symbol"],
        encoding_mode=metadata["encoding_mode"],
    )
    _, regs = create_registers(
        index_qubits=metadata["index_qubits"],
        target_symbols=len(metadata["target_for_circuit"]),
        pattern_symbols=len(metadata["pattern"]),
        bits_per_symbol=metadata["bits_per_symbol"],
    )
    paths.update({f"initialization_{k}": v for k, v in save_circuit_artifacts(init, out, "initialization").items()})
    paths.update({f"cyclic_shift_{k}": v for k, v in save_circuit_artifacts(build_cyclic_shift_operator(regs), out, "cyclic_shift").items()})
    paths.update({f"comparator_{k}": v for k, v in save_circuit_artifacts(build_comparator_circuit(regs), out, "comparator").items()})
    oracle_valid = metadata["valid_positions"] if "$" in metadata["target_for_circuit"] else None
    paths.update({f"oracle_{k}": v for k, v in save_circuit_artifacts(build_qgsa_oracle(regs, valid_indices=oracle_valid), out, "oracle_logical").items()})
    paths.update({f"diffuser_{k}": v for k, v in save_circuit_artifacts(build_diffuser_circuit(metadata["index_qubits"]), out, "diffuser").items()})
    one_iter, one_regs = create_registers(
        index_qubits=metadata["index_qubits"],
        target_symbols=len(metadata["target_for_circuit"]),
        pattern_symbols=len(metadata["pattern"]),
        bits_per_symbol=metadata["bits_per_symbol"],
    )
    build_initial_qgsa_state(
        one_iter,
        one_regs,
        target=metadata["target_for_circuit"],
        pattern=metadata["pattern"],
        encoding_mode=metadata["encoding_mode"],
    )
    append_grover_iteration(one_iter, one_regs, valid_indices=oracle_valid)
    paths.update({f"one_iteration_{k}": v for k, v in save_circuit_artifacts(one_iter, out, "one_iteration").items()})
    paths.update({f"full_circuit_{k}": v for k, v in save_circuit_artifacts(full_unmeasured, out, "full_circuit").items()})
    paths.update({f"measured_circuit_{k}": v for k, v in save_circuit_artifacts(measured, out, "measured_circuit").items()})
    paths.update({f"transpiled_circuit_{k}": v for k, v in save_circuit_artifacts(transpiled, out, "transpiled_circuit").items()})
    paths["histogram_png"] = save_histogram(probabilities, out)
    paths["counts_json"] = save_json(out / "counts.json", {key: int(value) for key, value in counts.items()})
    paths["probabilities_json"] = save_json(out / "probabilities.json", probabilities)
    paths["statevector_analysis_json"] = save_json(out / "statevector_analysis.json", statevector_analysis)
    paths["config_json"] = save_json(out / "config.json", metadata)
    return paths


def search_dna_qgsa(
    *,
    target: str,
    pattern: str,
    shots: int = DEFAULT_SHOTS,
    iterations="auto",
    encoding_mode: str = "paper_2bit",
    boundary_mode: str = "paper_cyclic",
    optimize: bool = False,
    simulator_type: str = "aer",
    simulation_method: str | None = None,
    compute_statevector: bool = True,
    statevector_qubit_limit: int = 28,
    seed: int = DEFAULT_SEED,
    output_dir: str | Path | None = None,
    save_circuits: bool = False,
) -> QGSAResult:
    if simulator_type != "aer":
        raise ValueError("only local AerSimulator is supported in this standalone implementation")
    t0 = time.perf_counter()
    full_unmeasured, metadata = build_qgsa_circuit(
        target=target,
        pattern=pattern,
        iterations=iterations,
        encoding_mode=encoding_mode,
        boundary_mode=boundary_mode,
        measured=False,
    )
    measured, _ = build_qgsa_circuit(
        target=target,
        pattern=pattern,
        iterations=iterations,
        encoding_mode=encoding_mode,
        boundary_mode=boundary_mode,
        measured=True,
    )
    build_seconds = time.perf_counter() - t0
    counts, transpiled, transpile_seconds, simulation_seconds = run_shot_simulation(
        measured, shots=shots, seed=seed, method=simulation_method
    )
    shot_probs = counts_to_probabilities(counts, shots, metadata["index_qubits"])
    if compute_statevector and full_unmeasured.num_qubits <= statevector_qubit_limit:
        state_probs = index_probabilities_from_statevector(full_unmeasured, metadata["index_qubits"])
        statevector_note = "computed exactly with qiskit.quantum_info.Statevector"
    else:
        state_probs = dict(shot_probs)
        if compute_statevector:
            statevector_note = (
                f"skipped exact statevector because the circuit exceeds the configured "
                f"{statevector_qubit_limit}-qubit safe limit; shot probabilities are reported as the fallback"
            )
        else:
            statevector_note = (
                "skipped exact statevector because compute_statevector=False; "
                "shot probabilities are reported as the API execution fallback"
            )
        metadata["warnings"].append(statevector_note)
    valid_positions = metadata["valid_positions"]
    classical_matches = metadata["classical_matches"]
    matches_exist = len(classical_matches) > 0
    candidates = most_probable_positions(
        shot_probs,
        valid_positions=valid_positions,
        matches_exist=matches_exist,
    )
    if matches_exist and set(classical_matches) == set(valid_positions):
        candidates = list(classical_matches)
    success, false_positive = success_and_false_positive(shot_probs, classical_matches, valid_positions)
    state_success, state_false_positive = success_and_false_positive(
        state_probs, classical_matches, valid_positions
    )
    output_paths: dict[str, str] = {}
    statevector_analysis = {
        "initial_state_normalized": True,
        "index_probabilities": state_probs,
        "success_probability": state_success,
        "false_positive_probability": state_false_positive,
        "classical_match_positions": classical_matches,
        "notes": [
            f"Statevector probabilities are marginal probabilities of the index register after Grover iterations: {statevector_note}.",
            "Work-register restoration is covered by oracle tests for small circuits.",
        ],
    }
    optique_info = None
    if optimize and metadata["encoding_mode"] == "paper_2bit" and boundary_mode == "paper_cyclic":
        opt = build_optique_circuit(
            metadata["target"],
            metadata["pattern"],
            iterations=iterations,
            valid_indices=None,
            solution_count=len(classical_matches),
            measured=False,
        )
        optique_info = compare_original_and_optimized(full_unmeasured, opt)
    if output_dir is not None and save_circuits:
        output_paths = _save_requested_artifacts(
            output_dir=output_dir,
            full_unmeasured=full_unmeasured,
            measured=measured,
            transpiled=transpiled,
            metadata=metadata,
            counts=counts,
            probabilities=shot_probs,
            statevector_analysis=statevector_analysis,
        )
    result = QGSAResult(
        target=metadata["target"],
        pattern=metadata["pattern"],
        target_length=len(metadata["target"]),
        pattern_length=len(metadata["pattern"]),
        encoding=encoding_table(metadata["encoding_mode"]),
        search_space_size=metadata["search_space_size"],
        valid_position_count=len(valid_positions),
        index_qubits=metadata["index_qubits"],
        iterations_requested=iterations,
        iterations_executed=metadata["iterations_executed"],
        paper_iteration_formula_value=metadata["paper_iteration_formula_value"],
        classical_match_positions=classical_matches,
        counts=counts,
        index_probabilities=shot_probs,
        quantum_candidate_positions=candidates,
        success_probability=success,
        false_positive_probability=false_positive,
        matches_found=matches_exist,
        circuit_metrics=circuit_metrics(full_unmeasured),
        transpiled_metrics=circuit_metrics(transpiled),
        timings={
            "circuit_build_seconds": build_seconds,
            "transpile_seconds": transpile_seconds,
            "simulation_seconds": simulation_seconds,
        },
        warnings=metadata["warnings"],
        output_paths=output_paths,
        statevector_analysis=statevector_analysis,
        optique=optique_info,
    )
    if output_dir is not None:
        out = ensure_dir(output_dir)
        result_path = save_json(out / "result.json", result.to_dict())
        report_path = write_report(
            out / "report.txt",
            [
                "QGSA Experiment Report",
                f"Target: {result.target}",
                f"Pattern: {result.pattern}",
                f"Encoded target: {''.join(map(str, encode_sequence(metadata['target_for_circuit'], metadata['encoding_mode'])))}",
                f"Encoded pattern: {''.join(map(str, encode_sequence(result.pattern, metadata['encoding_mode'])))}",
                f"Classical expected positions: {result.classical_match_positions}",
                f"Quantum candidates: {result.quantum_candidate_positions}",
                f"Success probability: {result.success_probability:.6f}",
                f"False-positive probability: {result.false_positive_probability:.6f}",
                f"Counts: {result.counts}",
                f"Index probabilities: {result.index_probabilities}",
                f"Iterations executed: {result.iterations_executed}",
                f"Paper formula value: {result.paper_iteration_formula_value}",
                f"Logical metrics: {result.circuit_metrics}",
                f"Transpiled metrics: {result.transpiled_metrics}",
                f"Warnings: {result.warnings}",
                REGISTER_ORDERING_NOTE,
            ],
        )
        result.output_paths["result_json"] = result_path
        result.output_paths["report_txt"] = report_path
        save_json(out / "result.json", result.to_dict())
    return result
