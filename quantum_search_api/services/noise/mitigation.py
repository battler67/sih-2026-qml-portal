from __future__ import annotations

from math import isfinite

import numpy as np


def zero_noise_extrapolate(scales: list[float], values: list[float]) -> float:
    if len(scales) != len(values) or len(scales) < 2:
        raise ValueError("ZNE requires matching scale/value samples")
    fitted = np.polyfit(np.asarray(scales, dtype=float), np.asarray(values, dtype=float), 1)
    estimate = float(fitted[1])
    if not isfinite(estimate):
        raise ValueError("ZNE produced a non-finite estimate")
    return min(1.0, max(0.0, estimate))


def mitigate_readout_distribution(
    probabilities: dict[str, float],
    width: int,
    assignment_matrix: tuple[tuple[float, float], tuple[float, float]],
) -> dict[str, float]:
    if width < 1:
        raise ValueError("Measured register width must be positive")
    states = 1 << width
    measured = np.asarray(
        [float(probabilities.get(format(index, f"0{width}b"), 0.0)) for index in range(states)]
    )
    single = np.asarray(assignment_matrix, dtype=float).T
    response = single
    for _ in range(width - 1):
        response = np.kron(response, single)
    corrected = np.linalg.pinv(response) @ measured
    corrected = np.clip(corrected, 0.0, None)
    total = float(corrected.sum())
    if total <= 0:
        raise ValueError("Readout mitigation produced an empty distribution")
    corrected /= total
    return {
        format(index, f"0{width}b"): float(value)
        for index, value in enumerate(corrected)
    }
