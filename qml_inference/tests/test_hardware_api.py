from __future__ import annotations

import io
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import numpy as np
from PIL import Image

from qml_inference.hardware import Device, Execution, QmlHardwareService
from qml_inference.model import ModelStore
from qml_inference.server import create_handler

BUNDLE = Path(__file__).resolve().parents[1] / "artifacts/v1"


class FakeProvider:
    def configured(self):
        return True

    def discover(self, required_qubits):
        return [Device("ibm", "fake-qpu", "Fake QPU", max(4, required_qubits), 0)]

    def run(self, device, circuits, shots, on_submitted):
        on_submitted(["remote-safe-id"], "RUNNING")
        return Execution(
            ["remote-safe-id"],
            [{"0": shots} for _ in circuits],
            "DONE",
            {"maxDepth": max(circuit.depth() for circuit in circuits), "circuitCount": len(circuits)},
        )


class HardwareApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        store = ModelStore(BUNDLE)
        hardware = QmlHardwareService(store, providers={"ibm": FakeProvider()}, run_inline=True)
        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            create_handler(store, {"http://127.0.0.1:8080"}, hardware),
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}/api/qml/v1"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def call(self, path, data=None, content_type="application/json"):
        request = Request(
            self.base + path,
            data=data,
            headers={"Content-Type": content_type, "Origin": "http://127.0.0.1:8080"},
            method="POST" if data is not None else "GET",
        )
        try:
            with urlopen(request, timeout=20) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.load(exc)

    def test_capabilities_confirmation_submission_poll_and_result(self):
        status, capabilities = self.call("/hardware/capabilities")
        self.assertEqual(status, 200)
        self.assertTrue(capabilities["simulatorDefault"])
        self.assertFalse(
            capabilities["models"]["framingham-angle-qksvm-pca2"]["providers"]["qbraid"]["supported"]
        )

        stream = io.BytesIO()
        Image.fromarray(np.full((28, 28), 128, dtype=np.uint8)).save(stream, format="PNG")
        payload = stream.getvalue()
        status, denied = self.call(
            "/hardware/qcnn/breastmnist/jobs?provider=ibm&shots=32&confirmRealHardware=false",
            payload,
            "image/png",
        )
        self.assertEqual(status, 409)
        self.assertIn("confirmation", denied["error"])

        status, created = self.call(
            "/hardware/qcnn/breastmnist/jobs?provider=ibm&shots=32&confirmRealHardware=true",
            payload,
            "image/png",
        )
        self.assertEqual(status, 202)
        self.assertEqual(created["status"], "completed")
        status, result = self.call(f"/hardware/jobs/{created['jobId']}/results")
        self.assertEqual(status, 200)
        self.assertEqual(result["backend"]["type"], "real_quantum_hardware")
        self.assertEqual(result["hardwareExecution"]["jobId"], "remote-safe-id")
        self.assertTrue(result["hardwareExecution"]["rawHardwareMeasurements"])


if __name__ == "__main__":
    unittest.main()
