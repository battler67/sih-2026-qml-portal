# BreastMNIST QCNN serving integration specification

## Source artifact and scientific boundary

The promoted model is the existing completed research run `e77cc845e586cfdd` from sibling repository `qml-research`, created by commit `77c82e9acb484441c75e8fa66d75cf969b4ccf29` on `feature/qcnn-breast-cancer`. The source checkpoint is `results/qcnn_breast_cancer/runs/e77cc845e586cfdd/checkpoint.pt`. It is a smoke experiment trained on 32 BreastMNIST training images for two epochs, not a clinically validated device. Its saved test AUROC is 0.347826, AUPRC 0.232270, balanced accuracy 0.509662, sensitivity 0.888889, and specificity 0.130435 at the validation-selected threshold. These weak results must remain visible wherever the live demonstration is presented.

## Exact inference contract

1. Accept one PNG or JPEG image with a bounded byte size.
2. Decode with Pillow, reject malformed or unsupported content, apply EXIF orientation, convert to single-channel grayscale, and resize to 28×28 using bilinear interpolation. Training data were native 28×28 `uint8` grayscale; resizing exists only to adapt uploaded images to that exact tensor shape.
3. Divide the 28×28 image into a 2×2 grid of 14×14 regions, take each region mean, divide by 255, and map each value with `π × (2x - 1)`. This produces four angles in `[-π, π]`. Spatial pooling has no fitted parameters.
4. Encode the four angles with one `RY` rotation on each of four qubits.
5. Run two hierarchical QCNN stages. Each convolution uses U3 rotations plus IsingXX, IsingYY and IsingZZ interactions; each pooling block uses CRZ, CRX and CRY. Active wires reduce 4 → 2 → 1.
6. Measure the final Pauli-Z expectation, then apply the checkpoint's learned output scale and bias to produce a logit.
7. Apply sigmoid to obtain the saved model's malignant score. Predict malignant when the score is at least `0.4121575951576233`; otherwise predict normal-or-benign.

BreastMNIST's original label `0` is malignant and original label `1` is normal/benign. The research pipeline remaps this to serving target `0 = normal/benign`, `1 = malignant`.

## Serving bundle

The versioned bundle adds:

- `qcnn/breastmnist/checkpoint.pt`: the original trained Torch state and checkpoint metadata.
- `qcnn/breastmnist/serving.json`: immutable input, preprocessing, architecture, label, threshold, resource and evidence metadata.
- SHA-256 and byte-size entries in `manifest.json`, including original source hashes.

The portal loader validates manifest hashes, checkpoint type, state tensor names/shapes, config values, metadata/checkpoint agreement, probability finiteness and output range before reporting readiness. The model and PennyLane device are created once per service process; prediction uses evaluation mode and `torch.no_grad()`.

## API contract

`POST /api/qml/v1/qcnn/breastmnist/predict` accepts a raw PNG or JPEG request body with the corresponding `Content-Type`. The response contains the predicted class, malignant score, saved threshold, original and processed shapes, four reduced angles, model/run/version provenance, four-qubit circuit resources, backend and research disclaimer. The service exposes no fabricated uncertainty. Errors distinguish missing body, oversized upload, unsupported media type, malformed image and unavailable model without exposing local artifact paths.

## Frontend route

`/qml/imaging` provides drag-and-drop and file selection, local preview, bounded client validation, real service invocation, prediction and model provenance, reduced quantum input angles, and a compact image → preprocessing → spatial reduction → RY encoding → QCNN → measurement → prediction flow. It will reuse the current Clinical Lab shell and visual language.

## Implemented files

- `qml_inference/qcnn.py`
- `qml_inference/model.py`
- `qml_inference/server.py`
- `qml_inference/tests/test_qcnn.py`
- `qml_inference/tests/test_service.py`
- `qml_inference/artifacts/v1/qcnn/breastmnist/*`
- `qml_inference/artifacts/v1/manifest.json`
- `scripts/promote_qcnn_model.py`
- `src/lib/qml-api.ts`
- `src/components/QcnnImaging.tsx`
- `src/routes/qml.imaging.tsx`
- generated route tree, README and QML documentation

## Verification completed

- Replayed five recorded BreastMNIST test indices against `predictions.csv`; maximum absolute score error was `2.7346502173841714e-08`, passing the `1e-7` backend floating-point tolerance.
- Passed 12 QML inference tests covering grayscale/RGB conversion, resize, normalization/spatial pooling, deterministic inference, corrupt QCNN checkpoint rejection, PNG/JPEG, missing/invalid/unsupported/oversized requests, and existing tabular endpoint/score regressions.
- Passed targeted frontend ESLint and the production frontend build, including generated route `/qml/imaging`.
- Passed a browser-to-service smoke journey with an official BreastMNIST test image. The page displayed the checkpoint-derived score, threshold, Pauli-Z expectation, four encoded angles and model provenance, and showed no Vite error overlay.
