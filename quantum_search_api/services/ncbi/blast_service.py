from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Any

from .client import NcbiClient
from .exceptions import NcbiUnavailableError, NcbiValidationError


DEFAULT_GENBANK_GENOMIC_QUERY = "genbank[blast database source] AND genomic[blast sequence type]"


class NcbiBlastService:
    blast_url = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"

    def __init__(self, client: NcbiClient | None = None) -> None:
        self.client = client or NcbiClient()

    def check_result(
        self,
        result: dict[str, Any],
        *,
        max_records: int = 25,
        entrez_query: str | None = None,
        poll_attempts: int = 18,
    ) -> dict[str, Any]:
        query = self._query_from_result(result)
        max_records = min(100, max(1, int(max_records)))
        blast = self.search_sequence(
            query,
            max_records=max_records,
            entrez_query=entrez_query or DEFAULT_GENBANK_GENOMIC_QUERY,
            poll_attempts=poll_attempts,
        )
        quantum_accessions = {
            self._accession_key(str(hit.get("accession") or ""))
            for hit in result.get("hits", [])
            if hit.get("accession")
        }
        for record in blast["records"]:
            record_key = self._accession_key(record["accession"])
            record["alsoReturnedByQuantum"] = record_key in quantum_accessions
        return {
            "queryLength": len(query),
            "database": "nt",
            "entrezQuery": entrez_query or DEFAULT_GENBANK_GENOMIC_QUERY,
            "maxRecords": max_records,
            "records": blast["records"],
            "organisms": blast["organisms"],
            "quantumAccessionsChecked": sorted(quantum_accessions),
            "matchingQuantumAccessions": sorted(
                {
                    self._accession_key(record["accession"])
                    for record in blast["records"]
                    if self._accession_key(record["accession"]) in quantum_accessions
                }
            ),
        }

    def search_sequence(
        self,
        query_sequence: str,
        *,
        max_records: int = 25,
        entrez_query: str = DEFAULT_GENBANK_GENOMIC_QUERY,
        poll_attempts: int = 18,
    ) -> dict[str, Any]:
        sequence = re.sub(r"\s+", "", query_sequence.upper())
        if not sequence or not re.fullmatch(r"[ACGT]+", sequence):
            raise NcbiValidationError("BLAST validation requires an ATGC-only DNA query sequence")

        put_text = self.client.post_text(
            self.blast_url,
            {
                "CMD": "Put",
                "PROGRAM": "blastn",
                "DATABASE": "nt",
                "QUERY": sequence,
                "ENTREZ_QUERY": entrez_query,
                "HITLIST_SIZE": str(max_records),
                "MEGABLAST": "on",
            },
        )
        rid = self._field(put_text, "RID")
        rtoe = self._field(put_text, "RTOE")
        if not rid:
            raise NcbiUnavailableError("NCBI BLAST did not return a request ID")

        wait_seconds = min(15, max(2, int(rtoe or "3")))
        for _ in range(poll_attempts):
            time.sleep(wait_seconds)
            status_text = self.client.get_text(
                self.blast_url,
                {"CMD": "Get", "RID": rid, "FORMAT_OBJECT": "SearchInfo"},
            )
            status = self._field(status_text, "Status")
            if status == "FAILED":
                raise NcbiUnavailableError("NCBI BLAST search failed")
            if status == "UNKNOWN":
                raise NcbiUnavailableError("NCBI BLAST search expired or was not found")
            if status == "READY":
                if self._field(status_text, "ThereAreHits") == "no":
                    return {"records": [], "organisms": []}
                xml_text = self.client.get_text(
                    self.blast_url,
                    {"CMD": "Get", "RID": rid, "FORMAT_TYPE": "XML"},
                )
                records = self._parse_xml(xml_text)[:max_records]
                return {"records": records, "organisms": self._group_organisms(records)}

        raise NcbiUnavailableError("NCBI BLAST search did not finish before the polling limit")

    def _parse_xml(self, text: str) -> list[dict[str, Any]]:
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise NcbiUnavailableError("NCBI BLAST returned unreadable XML") from exc

        records: list[dict[str, Any]] = []
        for hit in root.findall(".//Hit"):
            accession = self._text(hit, "Hit_accession")
            title = self._text(hit, "Hit_def")
            hsp = hit.find(".//Hsp")
            identity = int(self._text(hsp, "Hsp_identity") or 0) if hsp is not None else 0
            align_len = int(self._text(hsp, "Hsp_align-len") or 0) if hsp is not None else 0
            percent_identity = round((identity / align_len) * 100, 3) if align_len else 0.0
            records.append(
                {
                    "accession": accession,
                    "recordTitle": title,
                    "organismName": self._organism_from_title(title),
                    "source": "GenBank",
                    "sequenceLength": int(self._text(hit, "Hit_len") or 0),
                    "percentIdentity": percent_identity,
                    "alignmentLength": align_len,
                    "eValue": self._text(hsp, "Hsp_evalue") if hsp is not None else "",
                    "bitScore": self._text(hsp, "Hsp_bit-score") if hsp is not None else "",
                    "queryRange": self._range(hsp, "Hsp_query-from", "Hsp_query-to"),
                    "subjectRange": self._range(hsp, "Hsp_hit-from", "Hsp_hit-to"),
                }
            )
        return records

    def _group_organisms(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            grouped[record["organismName"] or "Unknown organism"].append(record)
        return [
            {
                "organismName": organism,
                "recordCount": len(items),
                "bestPercentIdentity": max(float(item["percentIdentity"]) for item in items),
                "records": items,
            }
            for organism, items in sorted(
                grouped.items(),
                key=lambda pair: max(float(item["percentIdentity"]) for item in pair[1]),
                reverse=True,
            )
        ]

    def _query_from_result(self, result: dict[str, Any]) -> str:
        for hit in result.get("hits", []):
            query = str(hit.get("querySequence") or "")
            if query:
                return query
        query = result.get("query", {})
        preview = str(query.get("sequencePreview") or "") if isinstance(query, dict) else ""
        if preview and "..." not in preview:
            return preview
        raise NcbiValidationError("Completed result does not include the full query sequence for BLAST validation")

    def _field(self, text: str, name: str) -> str:
        match = re.search(rf"^\s*{re.escape(name)}\s*=\s*(.+?)\s*$", text, re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _text(self, element: ET.Element | None, path: str) -> str:
        if element is None:
            return ""
        node = element.find(path)
        return (node.text or "").strip() if node is not None else ""

    def _range(self, element: ET.Element | None, start_path: str, end_path: str) -> dict[str, int | None]:
        start = self._text(element, start_path)
        end = self._text(element, end_path)
        return {"start": int(start) if start else None, "end": int(end) if end else None}

    def _organism_from_title(self, title: str) -> str:
        matches = re.findall(r"\[([^\[\]]+)\]", title)
        return matches[-1] if matches else "Unknown organism"

    def _accession_key(self, accession: str) -> str:
        return accession.split(".", 1)[0].upper()
