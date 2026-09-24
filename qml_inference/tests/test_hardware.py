from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from qiskit.quantum_info import Statevector

from qml_inference.hardware import (
    Device,
    Execution,
    HardwareError,
    QKSVM_MODEL_ID,
    QmlHardwareService,
    qcnn_circuit,
    qksvm_circuits,
)
from qml_inference.model import ModelStore, schema, validate
from qml_inference.qcnn import decode_image

BUNDLE = Path(__file__).resolve().parents[1] / "artifacts/v1"


class FakeProvider:
    name = "ibm"

    def __init__(self, counts: list[dict[str, int]] | None = None):
        self.counts = counts
        self.submissions = 0

    def configured(self):
        return True

    def discover(self, required_qubits):
        return [Device("ibm", "fake_qpu", "Fake QPU", max(4, required_qubits), 0)]

    def run(self, device, circuits, shots, on_submitted):
        self.submissions += 1
        on_submitted(["safe-remote-id"], "RUNNING")
        counts = self.counts or [{"0": shots} for _ in circuits]
        return Execution(
            ["safe-remote-id"], counts, "DONE",
            {"maxDepth": max(c.depth() for c in circuits), "circuitCount": len(circuits)},
        )


class CircuitEquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = ModelStore(BUNDLE)

    def test_qcnn_qiskit_circuit_matches_saved_pennylane_circuit(self):
        angles = np.array([-1.2, -0.1, 0.7, 2.1])
        expected = float(self.store.qcnn.model.expectation(
            __import__("torch").as_tensor(angles, dtype=__import__("torch").float64)
        ).detach().cpu())
        circuit = qcnn_circuit(self.store, angles).remove_final_measurements(inplace=False)
        state = Statevector.from_instruction(circuit)
        probabilities = state.probabilities([3])
        actual = float(probabilities[0] - probabilities[1])
        self.assertAlmostEqual(actual, expected, places=10)

    def test_qksvm_overlap_circuits_match_cached_state_fidelity(self):
        frame = validate(QKSVM_MODEL_ID, schema(QKSVM_MODEL_ID)["demo"])
        reduced = np.asarray(self.store.fhs_pipeline.transform(frame)[0], dtype=float)
        query = np.asarray(self.store._state(reduced))
        wanted = np.abs(query.conj() @ self.store.fhs_training_states[:6].T) ** 2
        circuits = qksvm_circuits(self.store, reduced)[:6]
        actual = [
            Statevector.from_instruction(circuit.remove_final_measurements(inplace=False)).probabilities()[0]
            for circuit in circuits
        ]
        np.testing.assert_allclose(actual, wanted, atol=1e-10)


class HardwareServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = ModelStore(BUNDLE)

    def test_capabilities_are_honest_about_qbraid_qksvm_limit(self):
        service = QmlHardwareService(self.store, providers={"ibm": FakeProvider(), "qbraid": FakeProvider()})
        capability = service.capabilities()["models"][QKSVM_MODEL_ID]["providers"]["qbraid"]
        self.assertFalse(capability["supported"])
        self.assertIn("256", capability["reason"])

    def test_confirmation_is_required_before_provider_submission(self):
        provider = FakeProvider()
        service = QmlHardwareService(self.store, providers={"ibm": provider}, run_inline=True)
        with self.assertRaisesRegex(HardwareError, "confirmation"):
            service.submit_tabular(QKSVM_MODEL_ID, schema(QKSVM_MODEL_ID)["demo"], "ibm", 32, False)
        self.assertEqual(provider.submissions, 0)

    def test_qcnn_hardware_counts_drive_primary_score(self):
        provider = FakeProvider([{"0": 24, "1": 8}])
        service = QmlHardwareService(self.store, providers={"ibm": provider}, run_inline=True)
        from PIL import Image
        import io

        stream = io.BytesIO()
        Image.fromarray(np.full((28, 28), 128, dtype=np.uint8)).save(stream, format="PNG")
        processed = decode_image(stream.getvalue(), "image/png")
        job = service.submit_qcnn(processed, "ibm", 32, True)
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.result["measurementExpectationZ"], 0.5)
        self.assertEqual(job.result["backend"]["type"], "real_quantum_hardware")
        self.assertEqual(job.result["hardwareExecution"]["jobId"], "safe-remote-id")
        self.assertEqual(job.result["explainability"]["executionBackend"], "local_ideal_simulator")


if __name__ == "__main__":
    unittest.main()
