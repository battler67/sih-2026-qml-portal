import pytest

from quantum_search_api.services.ncbi.models import SequenceRecord
from quantum_search_api.services.sequence.fasta_parser import parse_fasta
from quantum_search_api.services.sequence.normalizer import normalize_query_input, normalize_target_sequence
from quantum_search_api.services.sequence.reverse_complement import reverse_complement
from quantum_search_api.services.sequence.validator import SequenceValidationError, validate_query_acgt
from quantum_search_api.services.sequence.window_generator import generate_windows


def test_fasta_parsing_and_query_normalization():
    records = parse_fasta(">q1\nacgt\n")
    assert records[0].accession == "q1"
    normalized = normalize_query_input(">q1\nacgt\n", is_fasta=True)
    assert normalized.sequence == "ACGT"


def test_normalization_accepts_one_hundred_thousand_base_fasta_input():
    sequence = "ACGT" * 25_000

    normalized = normalize_query_input(
        f">query length=100000 seed=42\n{sequence}\n",
        is_fasta=True,
    )

    assert normalized.length == 100_000
    assert normalized.sequence == sequence


def test_invalid_query_symbol_reports_position():
    with pytest.raises(SequenceValidationError) as exc:
        validate_query_acgt("ACNT")
    assert exc.value.invalid_symbols[0].position == 2


def test_target_ambiguity_is_counted_not_deleted():
    normalized = normalize_target_sequence("ACNNGT")
    assert normalized.sequence == "ACNNGT"
    assert normalized.ambiguous_bases == 2


def test_reverse_complement():
    assert reverse_complement("ACGTN") == "NACGT"


def test_window_coordinates_and_ambiguity_skip():
    records = [
        SequenceRecord(
            accession="demo",
            title="demo chromosome",
            sequence="ACGTNNACGT",
            sourceDatabase="fixture",
            chromosome="chr1",
        )
    ]
    result = generate_windows(
        records,
        query_length=4,
        stride=1,
        strand="forward",
        max_windows=10,
        max_bases_per_record=100,
        max_total_bases=100,
    )
    assert result.summary.total_windows == 7
    assert result.summary.accepted_windows == 2
    assert result.summary.skipped_windows == 5
    assert result.summary.ambiguous_bases == 2
    assert result.windows[1].start_zero_based == 6
    assert result.windows[1].display_start == 7
