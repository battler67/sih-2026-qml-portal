"""Central configuration for the FRQI DNA paper reproduction."""

from __future__ import annotations

from dataclasses import dataclass
from math import pi


DEFAULT_SHOTS = 8000
DEFAULT_SEED = 12345
VALID_BASES = frozenset({"A", "C", "G", "T"})

# The default reproduces Table 2 and the A-vs-T example in the paper.
DEFAULT_ANGLE_MODE = "paper_state"


@dataclass(frozen=True)
class NucleotideAngle:
    """Angles reported in Table 1 of the paper.

    state_angle is the "Quantum state representation" column.
    decomposition_rotation is the "Parameterized gate rotations" column shown
    in the paper's decomposed multi-control circuits.
    """

    base: str
    name: str
    state_angle: float
    decomposition_rotation: float


NUCLEOTIDE_ANGLES: dict[str, NucleotideAngle] = {
    "A": NucleotideAngle("A", "Adenine", pi, pi / 4),
    "C": NucleotideAngle("C", "Cytosine", pi / 2, pi / 8),
    "T": NucleotideAngle("T", "Thymine", pi / 6, pi / 24),
    "G": NucleotideAngle("G", "Guanine", 0.0, 0.0),
}

ANGLE_MODE_DESCRIPTIONS = {
    "paper_state": (
        "Pass the paper's quantum-state angle to Qiskit RY. This reproduces "
        "Table 2 because RY(alpha)|0> has color angle alpha/2."
    ),
    "table_parameter_direct": (
        "Pass the Table 1 parameterized gate-rotation value directly to RY. "
        "This is useful for ambiguity analysis but does not reproduce Table 2."
    ),
    "frqi_color_angle": (
        "Treat the Table 1 parameterized value as the FRQI color angle theta "
        "and pass 2*theta to RY."
    ),
}
