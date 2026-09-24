"""Nucleotide-to-angle helpers for the paper's Table 1."""

from __future__ import annotations

from .config import ANGLE_MODE_DESCRIPTIONS, NUCLEOTIDE_ANGLES


def nucleotide_to_angle(base: str) -> float:
    """Return the paper's quantum-state angle for a nucleotide."""

    normalized = base.upper()
    if normalized not in NUCLEOTIDE_ANGLES:
        raise ValueError(f"invalid DNA nucleotide: {base!r}")
    return NUCLEOTIDE_ANGLES[normalized].state_angle


def nucleotide_to_decomposition_rotation(base: str) -> float:
    """Return the Table 1 parameterized decomposition rotation."""

    normalized = base.upper()
    if normalized not in NUCLEOTIDE_ANGLES:
        raise ValueError(f"invalid DNA nucleotide: {base!r}")
    return NUCLEOTIDE_ANGLES[normalized].decomposition_rotation


def qiskit_ry_angle(base: str, *, angle_mode: str = "paper_state") -> float:
    """Return the angle to pass to Qiskit's RY/MCRY operation.

    Qiskit implements RY(alpha)|0> = cos(alpha/2)|0> + sin(alpha/2)|1>.
    The paper's reported Table 2 probabilities are reproduced when alpha is
    the Table 1 quantum-state angle, not the displayed decomposition rotation.
    """

    normalized = base.upper()
    if normalized not in NUCLEOTIDE_ANGLES:
        raise ValueError(f"invalid DNA nucleotide: {base!r}")
    if angle_mode not in ANGLE_MODE_DESCRIPTIONS:
        supported = ", ".join(sorted(ANGLE_MODE_DESCRIPTIONS))
        raise ValueError(f"unsupported angle_mode {angle_mode!r}; use one of {supported}")

    entry = NUCLEOTIDE_ANGLES[normalized]
    if angle_mode == "paper_state":
        return entry.state_angle
    if angle_mode == "table_parameter_direct":
        return entry.decomposition_rotation
    if angle_mode == "frqi_color_angle":
        return 2.0 * entry.decomposition_rotation
    raise AssertionError("unreachable angle mode")


def angle_mapping_report() -> dict[str, dict[str, str | float]]:
    """Return a JSON-friendly representation of the centralized mapping."""

    return {
        base: {
            "name": entry.name,
            "paper_quantum_state_angle_radians": entry.state_angle,
            "paper_parameterized_gate_rotation_radians": entry.decomposition_rotation,
        }
        for base, entry in NUCLEOTIDE_ANGLES.items()
    }
