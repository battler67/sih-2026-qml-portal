"""Central scientific and simulator configuration."""

from __future__ import annotations

from math import pi

VALID_BASES = frozenset("ACGT")
DEFAULT_SHOTS = 8192
DEFAULT_SEED = 12345

# Scientific Reports 13, 14552 (2023), Table 1.  Qiskit implements
# RY(a)|0> = cos(a/2)|0> + sin(a/2)|1>; these state angles reproduce Table 2.
NUCLEOTIDE_STATE_ANGLES = {"A": pi, "C": pi / 2, "T": pi / 6, "G": 0.0}
PAPER_DECOMPOSITION_ROTATIONS = {"A": pi / 4, "C": pi / 8, "T": pi / 24, "G": 0.0}

IBM_BASIS_GATES = ["id", "rz", "sx", "x", "cx"]
