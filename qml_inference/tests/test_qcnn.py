from __future__ import annotations

import io
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from qml_inference.qcnn import (
    QcnnBundle,
    QcnnInputError,
    decode_image,
    spatial_pool_angles,
)

BUNDLE = Path(__file__).resolve().parents[1] / "artifacts/v1"


def image_bytes(mode: str = "L", size: tuple[int, int] = (28, 28)) -> bytes:
    if mode == "RGB":
        values = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        values[..., 0] = 220
        values[..., 1] = 80
        values[..., 2] = 30
    else:
        values = np.arange(size[0] * size[1], dtype=np.uint8).reshape(size[1], size[0])
    stream = io.BytesIO()
    Image.fromarray(values, mode=mode).save(stream, format="PNG")
    return stream.getvalue()


class PreprocessingTests(unittest.TestCase):
    def test_spatial_pool_maps_black_and_white_to_angle_bounds(self):
        black = spatial_pool_angles(np.zeros((1, 28, 28), dtype=np.uint8))[0]
        white = spatial_pool_angles(np.full((1, 28, 28), 255, dtype=np.uint8))[0]
        np.testing.assert_allclose(black, np.full(4, -np.pi))
        np.testing.assert_allclose(white, np.full(4, np.pi))

    def test_grayscale_and_rgb_are_resized_to_exact_training_shape(self):
        grayscale = decode_image(image_bytes(size=(42, 35)), "image/png")
        rgb = decode_image(image_bytes("RGB"), "image/png")
        self.assertEqual(grayscale.original_shape, [35, 42, 1])
        self.assertEqual(rgb.original_shape, [28, 28, 3])
        self.assertEqual(grayscale.pixels.shape, (28, 28))
        self.assertEqual(rgb.pixels.shape, (28, 28))
        self.assertEqual(grayscale.angles.shape, (4,))
        self.assertTrue(np.all(grayscale.angles >= -np.pi))
        self.assertTrue(np.all(grayscale.angles <= np.pi))

    def test_invalid_and_unsupported_inputs_fail_clearly(self):
        with self.assertRaisesRegex(QcnnInputError, "Only PNG and JPEG"):
            decode_image(image_bytes(), "image/gif")
        with self.assertRaisesRegex(QcnnInputError, "readable"):
            decode_image(b"not an image", "image/png")
        with self.assertRaisesRegex(QcnnInputError, "missing"):
            decode_image(b"", "image/png")


class InferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import json

        manifest = json.loads((BUNDLE / "manifest.json").read_text(encoding="utf-8"))
        cls.bundle = QcnnBundle(BUNDLE, manifest)

    def test_checkpoint_loads_and_inference_is_deterministic(self):
        payload = image_bytes()
        first = self.bundle.predict_bytes(payload, "image/png")
        second = self.bundle.predict_bytes(payload, "image/png")
        self.assertAlmostEqual(first["malignantScore"], second["malignantScore"], places=12)
        self.assertGreaterEqual(first["malignantScore"], 0)
        self.assertLessEqual(first["malignantScore"], 1)
        self.assertEqual(first["input"]["processedShape"], [28, 28, 1])
        self.assertEqual(len(first["transformedFeatures"]), 4)
        self.assertEqual(first["quantum"]["qubits"], 4)
        self.assertEqual(first["quantum"]["circuitExecutionsThisPrediction"], 5)
        self.assertGreater(first["inferenceTimeMs"], 0)
        self.assertEqual(first["explainability"]["method"], "four_region_midgray_occlusion")
        self.assertEqual(len(first["explainability"]["regions"]), 4)
        self.assertEqual(
            [item["modelScoreChange"] for item in first["explainability"]["regions"]],
            [item["modelScoreChange"] for item in second["explainability"]["regions"]],
        )
        self.assertEqual(first["researchRunId"], "e77cc845e586cfdd")
        self.assertIn("not intended for clinical diagnosis", first["disclaimer"])


if __name__ == "__main__":
    unittest.main()
