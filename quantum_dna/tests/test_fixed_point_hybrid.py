import json
from pathlib import Path

import numpy as np
import pytest
from qiskit import qasm2
from qiskit.quantum_info import Statevector

from quantum_dna.src.fixed_point_analysis import analyze_fixed_point_sequences
from quantum_dna.src.fixed_point_hybrid import (
    build_coherent_mismatch_oracle,
    build_fixed_point_circuits,
    build_fixed_point_mismatch_circuit,
    build_fixed_point_schedule,
    run_fixed_point_experiment,
    theoretical_fixed_point_success,
)


def test_coherent_oracle_computes_expected_phase_and_uncomputes_work():
    oracle = build_coherent_mismatch_oracle("ACGT", "ATGA", np.pi)
    width = 2
    for position in range(4):
        initial = Statevector.from_int(position, 1 << oracle.num_qubits)
        final = initial.evolve(oracle)
        expected_phase = -1 if position in {1, 3} else 1
        assert final.data[position] == pytest.approx(expected_phase, abs=1e-12)
        assert np.count_nonzero(np.abs(final.data) > 1e-12) == 1
        work = final.probabilities(
            qargs=list(range(width, oracle.num_qubits))
        )
        assert work[0] == pytest.approx(1.0, abs=1e-12)


def test_schedule_uses_length_bound_not_m():
    first = build_fixed_point_schedule(8, delta=0.2)
    second = build_fixed_point_schedule(8, delta=0.2)
    assert first == second
    assert first.lambda_min == 1 / 8
    assert first.guaranteed_width <= first.lambda_min
    assert first.guaranteed_success_probability == pytest.approx(0.96)
    assert first.rounds == len(first.phases)


@pytest.mark.parametrize(
    ("reference", "query", "truth"),
    [
        ("AAAA", "AAAT", [3]),
        ("AAAA", "AATT", [2, 3]),
        ("AAAA", "ATTT", [1, 2, 3]),
        ("AAAA", "TTTT", [0, 1, 2, 3]),
    ],
)
def test_fixed_point_guarantee_for_unknown_nonzero_m(reference, query, truth):
    result = run_fixed_point_experiment(
        reference,
        query,
        expected_positions=truth,
        delta=0.2,
    )
    assert result.success_probability + 1e-12 >= (
        result.guaranteed_success_probability
    )
    assert result.clean_work_probability == pytest.approx(1.0, abs=1e-12)
    schedule = build_fixed_point_schedule(len(reference), delta=0.2)
    theory = theoretical_fixed_point_success(
        len(truth) / len(reference), schedule
    )
    assert result.success_probability == pytest.approx(theory, abs=1e-12)


def test_non_power_of_two_has_no_padding_leakage():
    result = analyze_fixed_point_sequences(
        "ACGTA",
        "ATGTT",
        verification_positions=[1, 4],
        shots=2048,
    )
    assert result.invalid_padded_probability_exact == pytest.approx(
        0.0, abs=1e-12
    )
    assert result.invalid_padded_probability_shots == 0.0
    assert result.clean_work_probability == pytest.approx(1.0, abs=1e-12)
    assert result.guarantee_satisfied_exactly is True


def test_no_mismatch_remains_uniform_and_has_no_false_peak():
    result = analyze_fixed_point_sequences(
        "AAAA",
        "AAAA",
        verification_positions=[],
        shots=4096,
    )
    assert result.guarantee_applicable is False
    assert result.guarantee_satisfied_exactly is None
    assert result.exact_verified_target_probability == 0.0
    assert result.measurement_inferred_positions_zero_based == []
    assert all(
        probability == pytest.approx(0.25, abs=1e-12)
        for probability in result.exact_probabilities_after.values()
    )


def test_complete_artifacts_and_qasm_round_trip(tmp_path: Path):
    result = analyze_fixed_point_sequences(
        "ACGT",
        "ATGA",
        verification_positions=[1, 3],
        shots=1024,
        save_circuits=True,
        output_dir=tmp_path,
    )
    assert result.guarantee_satisfied_exactly is True
    assert len(result.artifact_paths) >= 35
    for artifact in result.artifact_paths.values():
        assert Path(artifact).is_file()

    stored = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert stored["verification_positions_zero_based"] == [1, 3]
    assert stored["clean_work_probability"] == pytest.approx(1.0)
    assert stored["limitations"]

    qasm_path = result.artifact_paths["fixed_point_final_measured_qasm"]
    loaded = qasm2.load(qasm_path)
    assert loaded.num_qubits == result.circuit_metrics.logical_qubits
    assert loaded.num_clbits == 2
    qasm3_text = Path(
        result.artifact_paths["qbraid_openqasm3"]
    ).read_text(encoding="utf-8")
    assert qasm3_text.startswith("OPENQASM 3")
    assert "measure" in qasm3_text

    unmeasured_qasm = qasm2.load(
        result.artifact_paths["fixed_point_final_unmeasured_qasm"]
    )
    original = build_fixed_point_circuits("ACGT", "ATGA")["unmeasured"]
    assert hasattr(original, "num_qubits")
    original_state = Statevector.from_instruction(original)
    loaded_state = Statevector.from_instruction(unmeasured_qasm)
    assert abs(np.vdot(original_state.data, loaded_state.data)) == pytest.approx(
        1.0, abs=1e-10
    )


def test_builder_source_has_no_legacy_classical_mismatch_helper():
    source = Path("quantum_dna/src/fixed_point_hybrid.py").read_text(
        encoding="utf-8"
    )
    analysis_source = Path(
        "quantum_dna/src/fixed_point_analysis.py"
    ).read_text(encoding="utf-8")
    assert "classical_mutations" not in source
    assert "classical_mutations" not in analysis_source
    circuit, phases = build_fixed_point_mismatch_circuit("ACGT", "ATGA")
    assert circuit.num_qubits == 7
    assert len(phases) == 2
