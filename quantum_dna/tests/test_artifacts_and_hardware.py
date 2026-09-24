from pathlib import Path

import numpy as np
from qiskit import qasm2
from qiskit.quantum_info import Statevector

from quantum_dna.src.grover_amplification import build_localization_circuits
from quantum_dna.src.hardware_adapter import prepare_for_ibm_backend
from quantum_dna.src.visualization import save_circuit


def test_qasm_artifact_round_trips(tmp_path: Path):
    circuit = build_localization_circuits("ACGT", "ACTT")["measured"]
    paths = save_circuit(circuit, tmp_path, "roundtrip")
    loaded = qasm2.load(paths["roundtrip_qasm"])
    assert loaded.num_qubits == circuit.num_qubits
    assert loaded.num_clbits == circuit.num_clbits
    original_state = Statevector.from_instruction(circuit.remove_final_measurements(inplace=False))
    loaded_state = Statevector.from_instruction(loaded.remove_final_measurements(inplace=False))
    assert np.isclose(abs(np.vdot(original_state.data, loaded_state.data)), 1.0, atol=1e-10)


def test_missing_runtime_uses_aer_fallback():
    circuit = build_localization_circuits("ACGT", "ACTT")["measured"]
    prepared = prepare_for_ibm_backend(circuit)
    assert prepared["simulator_fallback"] is True
    assert prepared["submitted"] is False
    assert prepared["metrics"].logical_qubits == circuit.num_qubits
