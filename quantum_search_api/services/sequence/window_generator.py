from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from quantum_search_api.services.ncbi.models import SequenceRecord, WindowRecord

from .reverse_complement import reverse_complement
from .validator import ACGT, validate_target_iupac


@dataclass(frozen=True)
class WindowGenerationSummary:
    total_windows: int
    accepted_windows: int
    skipped_windows: int
    ambiguous_bases: int
    truncated: bool
    warnings: list[str]


@dataclass(frozen=True)
class WindowGenerationResult:
    windows: list[WindowRecord]
    summary: WindowGenerationSummary


def generate_windows(
    records: list[SequenceRecord],
    *,
    query_length: int,
    stride: int,
    strand: Literal["forward", "both"],
    max_windows: int,
    max_bases_per_record: int,
    max_total_bases: int,
) -> WindowGenerationResult:
    windows: list[WindowRecord] = []
    total_windows = 0
    skipped = 0
    ambiguous_total = 0
    warnings: list[str] = []
    total_bases = 0
    truncated = False

    for record in records:
        sequence, ambiguous = validate_target_iupac(record.sequence)
        ambiguous_total += ambiguous
        if len(sequence) > max_bases_per_record:
            sequence = sequence[:max_bases_per_record]
            truncated = True
            warnings.append(f"{record.accession} was truncated to {max_bases_per_record} bases before windowing")
        if total_bases + len(sequence) > max_total_bases:
            allowed = max(0, max_total_bases - total_bases)
            sequence = sequence[:allowed]
            truncated = True
            warnings.append("Downloaded genomic bases were truncated to the configured total-base limit")
        total_bases += len(sequence)
        if len(sequence) < query_length:
            continue
        directions = [("forward", sequence)]
        if strand == "both":
            directions.append(("reverse", reverse_complement(sequence)))
        for direction, oriented in directions:
            for start in range(0, len(oriented) - query_length + 1, stride):
                total_windows += 1
                end = start + query_length
                window_seq = oriented[start:end]
                if any(base not in ACGT for base in window_seq):
                    skipped += 1
                    continue
                global_start = start
                global_end = end
                if direction == "reverse":
                    global_start = len(oriented) - end
                    global_end = len(oriented) - start
                if len(windows) < max_windows:
                    windows.append(
                        WindowRecord(
                            accession=record.accession,
                            recordTitle=record.title,
                            organism=record.organism,
                            taxId=record.tax_id,
                            sourceDatabase=record.source_database,
                            chromosome=record.chromosome,
                            strand=direction,
                            startZeroBased=global_start,
                            endZeroBased=global_end,
                            sequence=window_seq,
                        )
                    )
                else:
                    truncated = True
        if total_bases >= max_total_bases:
            break

    if truncated:
        warnings.append("Window generation used configured limits; sampling/truncation occurred")
    return WindowGenerationResult(
        windows=windows,
        summary=WindowGenerationSummary(
            total_windows=total_windows,
            accepted_windows=len(windows),
            skipped_windows=skipped + max(0, total_windows - skipped - len(windows)),
            ambiguous_bases=ambiguous_total,
            truncated=truncated,
            warnings=warnings,
        ),
    )
