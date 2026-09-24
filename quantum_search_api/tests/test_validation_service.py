from quantum_search_api.services.ncbi.models import SequenceRecord
from quantum_search_api.services.search.validation_service import validate_hit_against_records


def test_validation_uses_source_sequence_coordinate_range():
    records = [
        SequenceRecord(
            accession="U00096.3",
            title="Escherichia coli K-12 complete genome",
            sequence="AGCTTTTCATTCTGACTGCA",
            sourceDatabase="fixture",
        )
    ]
    hit = {
        "accession": "U00096.3",
        "strand": "forward",
        "start": 14,
        "end": 17,
        "matchedWindow": "WRNG",
    }

    validation = validate_hit_against_records(
        "GACT",
        hit,
        records,
        max_bases_per_record=100,
        max_total_bases=100,
    )

    assert validation["matches"] is True
    assert validation["validatedWindow"] == "GACT"
    assert validation["positionsWithinWindow"] == [0]
    assert validation["storedWindowMatchesCoordinate"] is False


def test_validation_rejects_real_coordinate_mismatch():
    records = [
        SequenceRecord(
            accession="U00096.3",
            title="Escherichia coli K-12 complete genome",
            sequence="AGCTTTTCATTCTGACTGCA",
            sourceDatabase="fixture",
        )
    ]
    hit = {
        "accession": "U00096.3",
        "strand": "forward",
        "start": 7,
        "end": 10,
        "matchedWindow": "TCAT",
    }

    validation = validate_hit_against_records(
        "GACT",
        hit,
        records,
        max_bases_per_record=100,
        max_total_bases=100,
    )

    assert validation["matches"] is False
    assert validation["validatedWindow"] == "TCAT"
