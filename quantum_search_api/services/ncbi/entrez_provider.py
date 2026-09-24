from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .client import NcbiClient
from .exceptions import NcbiValidationError
from .models import RecordMetadata, SearchRequest, SequenceRecord


UNSUPPORTED_RECORD_HINTS = (
    "mrna",
    "messenger rna",
    "ncrna",
    "transcript",
    "protein",
    "sra",
    "geo",
    "fastq",
)


class NcbiEntrezProvider:
    def __init__(self, client: NcbiClient | None = None) -> None:
        self.client = client or NcbiClient()

    def search_records(self, request: SearchRequest) -> list[RecordMetadata]:
        accessions = request.nucleotide_accessions or ([request.query_accession] if request.query_accession else [])
        if not accessions:
            return []
        term = " OR ".join(f"{acc}[ACCN]" for acc in accessions)
        term = f"({term}) AND biomol_genomic[PROP]"
        if "refseq" in request.database_scope.value:
            term = f"({term}) AND srcdb_refseq[PROP]"
        data = self.client.get_json(
            self.client.eutils_url("esearch"),
            {
                "db": "nuccore",
                "term": term,
                "retmode": "json",
                "retmax": request.max_records,
                "idtype": "acc",
                "usehistory": "y",
            },
            cache_key=f"esearch:{term}:{request.max_records}",
        )
        ids = data.get("esearchresult", {}).get("idlist", [])
        if not isinstance(ids, list) or not ids:
            raise NcbiValidationError("No exact genomic nucleotide records matched the requested accessions")
        return self.get_record_metadata([str(item) for item in ids])

    def get_record_metadata(self, accessions: list[str]) -> list[RecordMetadata]:
        if not accessions:
            return []
        data = self.client.get_json(
            self.client.eutils_url("esummary"),
            {"db": "nuccore", "id": ",".join(accessions), "retmode": "json"},
            cache_key=f"esummary:{','.join(accessions)}",
        )
        result = data.get("result", {})
        records: list[RecordMetadata] = []
        for uid in result.get("uids", accessions):
            doc = result.get(str(uid), {})
            title = str(doc.get("title") or doc.get("caption") or uid)
            self._validate_genomic_metadata(title, doc)
            records.append(
                RecordMetadata(
                    accession=str(doc.get("caption") or uid),
                    title=title,
                    organism=doc.get("organism"),
                    taxId=str(doc.get("taxid")) if doc.get("taxid") is not None else None,
                    sourceDatabase="NCBI Nucleotide",
                    moleculeType="genomic DNA",
                )
            )
        return records

    def fetch_sequences(self, accessions: list[str], request: SearchRequest | None = None) -> list[SequenceRecord]:
        if not accessions:
            return []
        fasta = self.client.get_text(
            self.client.eutils_url("efetch"),
            {"db": "nuccore", "id": ",".join(accessions), "rettype": "fasta", "retmode": "text"},
            cache_key=f"efetch:fasta:{','.join(accessions)}",
        )
        genbank = self.client.get_text(
            self.client.eutils_url("efetch"),
            {"db": "nuccore", "id": ",".join(accessions), "rettype": "gb", "retmode": "text"},
            cache_key=f"efetch:gb:{','.join(accessions)}",
        )
        self._validate_genbank_is_genomic_dna(genbank)
        return self._parse_fasta_records(fasta)

    def _validate_genomic_metadata(self, title: str, doc: dict) -> None:
        haystack = " ".join([title, str(doc.get("moltype", "")), str(doc.get("biomol", ""))]).lower()
        if any(hint in haystack for hint in UNSUPPORTED_RECORD_HINTS):
            raise NcbiValidationError("NCBI metadata identifies a non-genomic DNA record")

    def _validate_genbank_is_genomic_dna(self, text: str) -> None:
        lowered = text.lower()
        if any(hint in lowered for hint in UNSUPPORTED_RECORD_HINTS):
            raise NcbiValidationError("Retrieved record is not genomic DNA")
        if "mol_type=\"genomic dna\"" not in lowered and "/mol_type=\"genomic dna\"" not in lowered:
            raise NcbiValidationError("Retrieved record did not explicitly validate as genomic DNA")

    def _parse_fasta_records(self, text: str) -> list[SequenceRecord]:
        records: list[SequenceRecord] = []
        title = ""
        seq_parts: list[str] = []
        for line in text.splitlines():
            if line.startswith(">"):
                if title:
                    records.append(self._record_from_parts(title, seq_parts))
                title = line[1:].strip()
                seq_parts = []
            else:
                seq_parts.append(line.strip())
        if title:
            records.append(self._record_from_parts(title, seq_parts))
        return records

    def _record_from_parts(self, title: str, seq_parts: list[str]) -> SequenceRecord:
        accession = title.split()[0]
        chromosome_match = re.search(r"(chromosome|chr)\s+([^,\s]+)", title, re.IGNORECASE)
        return SequenceRecord(
            accession=accession,
            title=title,
            organism=None,
            taxId=None,
            sequence="".join(seq_parts).upper(),
            sourceDatabase="NCBI Nucleotide",
            moleculeType="genomic DNA",
            chromosome=chromosome_match.group(2) if chromosome_match else None,
        )
