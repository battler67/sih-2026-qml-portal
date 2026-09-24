from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedFastaRecord:
    title: str
    sequence: str

    @property
    def accession(self) -> str:
        return self.title.split()[0] if self.title else "local_sequence"


def parse_fasta(text: str) -> list[ParsedFastaRecord]:
    records: list[ParsedFastaRecord] = []
    title = ""
    parts: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if title:
                records.append(ParsedFastaRecord(title=title, sequence="".join(parts)))
            title = line[1:].strip()
            parts = []
        else:
            parts.append(line)
    if title:
        records.append(ParsedFastaRecord(title=title, sequence="".join(parts)))
    if not records and text.strip():
        records.append(ParsedFastaRecord(title="local_sequence", sequence="".join(text.split())))
    return records
