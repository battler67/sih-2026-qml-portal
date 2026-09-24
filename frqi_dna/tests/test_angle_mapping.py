from math import isclose, pi

from frqi_dna.src.angle_mapping import (
    nucleotide_to_angle,
    nucleotide_to_decomposition_rotation,
    qiskit_ry_angle,
)


def test_exact_paper_angle_mapping():
    assert isclose(nucleotide_to_angle("A"), pi)
    assert isclose(nucleotide_to_angle("C"), pi / 2)
    assert isclose(nucleotide_to_angle("T"), pi / 6)
    assert isclose(nucleotide_to_angle("G"), 0.0)


def test_exact_paper_parameterized_rotation_mapping():
    assert isclose(nucleotide_to_decomposition_rotation("A"), pi / 4)
    assert isclose(nucleotide_to_decomposition_rotation("C"), pi / 8)
    assert isclose(nucleotide_to_decomposition_rotation("T"), pi / 24)
    assert isclose(nucleotide_to_decomposition_rotation("G"), 0.0)


def test_default_qiskit_angle_reproduces_paper_state_angle():
    assert isclose(qiskit_ry_angle("A"), pi)
    assert isclose(qiskit_ry_angle("T"), pi / 6)
