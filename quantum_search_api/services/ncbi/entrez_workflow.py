from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Any
from urllib.parse import quote

import httpx

from .client import NcbiClient
from .exceptions import NcbiUnavailableError, NcbiValidationError


REFSEQ_PREFIXES = ("AC_", "NC_", "NG_", "NM_", "NR_", "NT_", "NW_", "XM_", "XR_", "YP_", "XP_")
DNA_AMBIGUITY = set("NRYKMSWBDHV")


class NcbiEntrezWorkflow:
    def __init__(self, client: NcbiClient | None = None) -> None:
        self.client = client or NcbiClient()

    def search_gene(
        self,
        *,
        gene: str,
        organism: str | None = None,
        source: str = "all",
        min_length: int | None = None,
        max_length: int | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:
        cleaned_gene = gene.strip()
        if not cleaned_gene:
            raise NcbiValidationError("Gene name is required")
        if source not in {"all", "refseq", "genbank"}:
            raise NcbiValidationError("source must be all, refseq, or genbank")

        page = max(1, page)
        page_size = min(50, max(1, page_size))
        term = self._gene_search_term(cleaned_gene, organism, source, min_length, max_length)
        data = self.client.get_json(
            self.client.eutils_url("esearch"),
            {
                "db": "nuccore",
                "term": term,
                "retmode": "json",
                "retstart": (page - 1) * page_size,
                "retmax": page_size,
            },
            cache_key=f"entrez_gene_search:{term}:{page}:{page_size}",
        )
        result = data.get("esearchresult", {})
        ids = [str(item) for item in result.get("idlist", [])]
        records = self._summaries(ids, fallback_gene=cleaned_gene) if ids else []
        return {
            "query": cleaned_gene,
            "count": int(result.get("count", 0) or 0),
            "page": page,
            "pageSize": page_size,
            "records": records,
        }

    def search_taxa(self, query: str, *, limit: int = 10) -> dict[str, Any]:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise NcbiValidationError("Organism name or taxonomy ID is required")
        limit = min(20, max(1, limit))
        if cleaned_query.isdigit():
            tax_ids = [cleaned_query]
            count = 1
        else:
            data = self.client.get_json(
                self.client.eutils_url("esearch"),
                {
                    "db": "taxonomy",
                    "term": f'"{cleaned_query}"[All Names]',
                    "retmode": "json",
                    "retmax": limit,
                },
                cache_key=f"entrez_taxonomy_search:{cleaned_query.lower()}:{limit}",
            )
            result = data.get("esearchresult", {})
            tax_ids = [str(item) for item in result.get("idlist", [])]
            count = int(result.get("count", 0) or 0)
        records = [self.organism_details(tax_id) for tax_id in tax_ids[:limit]]
        records.sort(
            key=lambda record: (
                str(record.get("scientificName") or "").lower() != cleaned_query.lower(),
                str(record.get("scientificName") or ""),
            )
        )
        return {
            "query": cleaned_query,
            "count": count,
            "records": records,
        }

    def record_details(self, accession: str) -> dict[str, Any]:
        uid = self._uid_for_accession(accession)
        summary = self._summaries([uid], fallback_gene="")[0]
        gb_xml = self.client.get_text(
            self.client.eutils_url("efetch"),
            {"db": "nuccore", "id": uid, "rettype": "gb", "retmode": "xml"},
            cache_key=f"entrez_record_gbxml:{uid}",
        )
        fasta = self.client.get_text(
            self.client.eutils_url("efetch"),
            {"db": "nuccore", "id": uid, "rettype": "fasta", "retmode": "text"},
            cache_key=f"entrez_record_fasta:{uid}",
        )
        parsed = self._parse_genbank_xml(gb_xml)
        sequence = self._sequence_from_fasta(fasta) or str(parsed.get("sequence") or "").upper()
        accession_version = str(parsed.get("accessionVersion") or summary["accession"])
        return {
            "overview": {
                "accession": accession_version,
                "recordTitle": parsed.get("definition") or summary["recordTitle"],
                "geneName": parsed.get("geneName") or summary.get("geneName") or "",
                "source": summary["source"],
                "moleculeType": parsed.get("moleculeType") or summary["moleculeType"],
                "lastUpdated": parsed.get("lastUpdated") or summary["lastUpdated"],
                "sequenceLength": int(parsed.get("sequenceLength") or len(sequence) or summary["sequenceLength"]),
                "ncbiUrl": f"https://www.ncbi.nlm.nih.gov/nuccore/{accession_version}",
            },
            "organism": {
                "organismName": parsed.get("organism") or summary["organismName"],
                "scientificName": parsed.get("organism") or summary["scientificName"],
                "taxonomy": parsed.get("taxonomy") or "",
                "taxId": parsed.get("taxId") or summary.get("taxId") or "",
            },
            "gene": parsed.get("gene") or {},
            "sequence": {
                "length": len(sequence),
                "moleculeType": parsed.get("moleculeType") or summary["moleculeType"],
                "unsupportedBases": self._unsupported_base_summary(sequence),
                "atgcRegions": self._atgc_regions(sequence),
            },
            "references": parsed.get("references") or [],
            "source": {
                "database": summary["source"],
                "keywords": parsed.get("keywords") or [],
                "sourceFeature": parsed.get("sourceFeature") or {},
            },
            "fasta": self._normalise_fasta(accession_version, parsed.get("definition") or summary["recordTitle"], sequence),
            "rawSequence": sequence,
        }

    def analysis_sequence(self, accession: str) -> dict[str, Any]:
        detail = self.record_details(accession)
        sequence = str(detail["rawSequence"]).upper()
        molecule_type = str(detail["overview"]["moleculeType"])
        if not self._looks_like_dna(sequence, molecule_type):
            raise NcbiValidationError("Selected NCBI record does not contain DNA sequence data")
        unsupported = self._unsupported_base_summary(sequence)
        warnings: list[str] = []
        if unsupported:
            warnings.append("Unsupported ambiguity bases were detected. Select an ATGC-only region before analysis.")
        regions = self._atgc_regions(sequence)
        if not regions:
            raise NcbiValidationError("No ATGC-only region is available for quantum sequence analysis")
        return {
            "accession": detail["overview"]["accession"],
            "recordTitle": detail["overview"]["recordTitle"],
            "organismName": detail["organism"]["organismName"],
            "geneName": detail["overview"]["geneName"],
            "moleculeType": molecule_type,
            "sequenceLength": len(sequence),
            "sequence": sequence,
            "unsupportedBases": unsupported,
            "atgcRegions": regions[:100],
            "warnings": warnings,
        }

    def organism_details(self, tax_id: str) -> dict[str, Any]:
        cleaned = tax_id.strip()
        if not cleaned:
            raise NcbiValidationError("Taxonomy ID is required")
        xml_text = self.client.get_text(
            self.client.eutils_url("efetch"),
            {"db": "taxonomy", "id": cleaned, "retmode": "xml"},
            cache_key=f"entrez_taxonomy:{cleaned}",
        )
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise NcbiUnavailableError("NCBI returned unreadable taxonomy XML") from exc
        taxon = root.find(".//Taxon")
        if taxon is None:
            raise NcbiValidationError(f"NCBI taxonomy ID {cleaned} was not found")
        lineage = [
            {
                "taxId": self._text(item, "TaxId"),
                "scientificName": self._text(item, "ScientificName"),
                "rank": self._text(item, "Rank"),
            }
            for item in taxon.findall(".//LineageEx/Taxon")
        ]
        return {
            "taxId": self._text(taxon, "TaxId") or cleaned,
            "scientificName": self._text(taxon, "ScientificName"),
            "commonName": self._text(taxon, "OtherNames/CommonName"),
            "rank": self._text(taxon, "Rank"),
            "division": self._text(taxon, "Division"),
            "parentTaxId": self._text(taxon, "ParentTaxId"),
            "lineage": self._text(taxon, "Lineage"),
            "lineageTaxa": lineage,
            "geneticCode": {
                "id": self._text(taxon, "GeneticCode/GCId"),
                "name": self._text(taxon, "GeneticCode/GCName"),
            },
            "mitochondrialGeneticCode": {
                "id": self._text(taxon, "MitoGeneticCode/MGCId"),
                "name": self._text(taxon, "MitoGeneticCode/MGCName"),
            },
            "ncbiUrl": f"https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id={cleaned}",
        }

    def organism_genome_viewer(self, tax_id: str) -> dict[str, Any]:
        details = self.organism_details(tax_id)
        selected_name = str(details.get("scientificName") or "")
        tree_nodes = [
            {
                "taxId": item["taxId"],
                "scientificName": item["scientificName"],
                "rank": item["rank"] or "no rank",
                "isSelected": False,
            }
            for item in details.get("lineageTaxa", [])
            if item.get("taxId") and item.get("scientificName")
        ]
        tree_nodes.append(
            {
                "taxId": details["taxId"],
                "scientificName": selected_name or "Selected organism",
                "rank": details.get("rank") or "species",
                "isSelected": True,
            }
        )
        return {
            "taxId": details["taxId"],
            "scientificName": selected_name,
            "commonName": details.get("commonName") or "",
            "rank": details.get("rank") or "",
            "division": details.get("division") or "",
            "parentTaxId": details.get("parentTaxId") or "",
            "treeNodes": tree_nodes,
            "lineage": details.get("lineage") or "",
            "image": self._wikimedia_image(selected_name or str(details.get("commonName") or "")),
            "links": {
                "taxonomy": details["ncbiUrl"],
                "genomeDataViewer": self._gdv_url(selected_name),
            },
        }

    def _gene_search_term(
        self,
        gene: str,
        organism: str | None,
        source: str,
        min_length: int | None,
        max_length: int | None,
    ) -> str:
        escaped_gene = gene.replace('"', "")
        parts = [
            f'("{escaped_gene}"[Gene Name] OR "{escaped_gene}"[Title])',
            "biomol_genomic[PROP]",
            'NOT ("mRNA"[Title] OR "transcript"[Title] OR "protein"[Title])',
        ]
        if organism:
            parts.append(f'"{organism.strip().replace(chr(34), "")}"[Organism]')
        if source == "refseq":
            parts.append("srcdb_refseq[PROP]")
        elif source == "genbank":
            parts.append("NOT srcdb_refseq[PROP]")
        if min_length is not None or max_length is not None:
            low = max(1, int(min_length or 1))
            high = max(low, int(max_length or 1_000_000_000))
            parts.append(f"{low}:{high}[SLEN]")
        return " AND ".join(parts)

    def _uid_for_accession(self, accession: str) -> str:
        cleaned = accession.strip()
        if not cleaned:
            raise NcbiValidationError("Accession is required")
        data = self.client.get_json(
            self.client.eutils_url("esearch"),
            {"db": "nuccore", "term": f"{cleaned}[ACCN]", "retmode": "json", "retmax": 1},
            cache_key=f"entrez_accession_uid:{cleaned}",
        )
        ids = data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            raise NcbiValidationError(f"NCBI accession {cleaned} was not found")
        return str(ids[0])

    def _summaries(self, ids: list[str], *, fallback_gene: str) -> list[dict[str, Any]]:
        if not ids:
            return []
        data = self.client.get_json(
            self.client.eutils_url("esummary"),
            {"db": "nuccore", "id": ",".join(ids), "retmode": "json"},
            cache_key=f"entrez_gene_summaries:{','.join(ids)}",
        )
        result = data.get("result", {})
        records: list[dict[str, Any]] = []
        for uid in result.get("uids", ids):
            doc = result.get(str(uid), {})
            accession = str(doc.get("accessionversion") or doc.get("caption") or uid)
            organism = str(doc.get("organism") or "Unknown organism")
            source = self._source_label(doc, accession)
            records.append(
                {
                    "uid": str(uid),
                    "organismName": organism,
                    "scientificName": organism,
                    "geneName": self._gene_from_summary(doc, fallback_gene),
                    "accession": accession,
                    "recordTitle": str(doc.get("title") or doc.get("caption") or accession),
                    "sequenceLength": int(doc.get("slen") or 0),
                    "source": source,
                    "moleculeType": str(doc.get("moltype") or doc.get("biomol") or "nucleotide"),
                    "lastUpdated": str(doc.get("updatedate") or doc.get("createdate") or ""),
                    "taxId": str(doc.get("taxid") or ""),
                }
            )
        return records

    def _source_label(self, doc: dict[str, Any], accession: str) -> str:
        source = str(doc.get("sourcedb") or "").strip()
        if source:
            return "RefSeq" if source.lower() == "refseq" else source
        return "RefSeq" if accession.startswith(REFSEQ_PREFIXES) else "GenBank"

    def _gene_from_summary(self, doc: dict[str, Any], fallback_gene: str) -> str:
        title = str(doc.get("title") or "")
        match = re.search(r"\(([^()]+)\)", title)
        if match:
            return match.group(1).split(",")[0].strip()
        return fallback_gene

    def _parse_genbank_xml(self, text: str) -> dict[str, Any]:
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise NcbiUnavailableError("NCBI returned an unreadable GenBank XML record") from exc
        seq = root.find(".//GBSeq")
        if seq is None:
            raise NcbiValidationError("NCBI did not return a GenBank record for this accession")
        parsed: dict[str, Any] = {
            "accessionVersion": self._text(seq, "GBSeq_accession-version"),
            "definition": self._text(seq, "GBSeq_definition"),
            "organism": self._text(seq, "GBSeq_organism"),
            "taxonomy": self._text(seq, "GBSeq_taxonomy"),
            "moleculeType": self._text(seq, "GBSeq_moltype"),
            "lastUpdated": self._text(seq, "GBSeq_update-date"),
            "sequenceLength": int(self._text(seq, "GBSeq_length") or 0),
            "sequence": self._text(seq, "GBSeq_sequence").upper(),
            "keywords": [node.text or "" for node in seq.findall(".//GBKeyword")],
        }
        parsed["references"] = self._references(seq)
        parsed["gene"] = self._gene_info(seq)
        parsed["geneName"] = parsed["gene"].get("name", "")
        parsed["taxId"] = self._tax_id(seq)
        parsed["sourceFeature"] = self._source_feature(seq)
        return parsed

    def _text(self, element: ET.Element, path: str) -> str:
        node = element.find(path)
        return (node.text or "").strip() if node is not None else ""

    def _references(self, seq: ET.Element) -> list[dict[str, str]]:
        refs: list[dict[str, str]] = []
        for ref in seq.findall(".//GBReference"):
            refs.append(
                {
                    "title": self._text(ref, "GBReference_title"),
                    "authors": self._text(ref, "GBReference_authors"),
                    "journal": self._text(ref, "GBReference_journal"),
                    "pubmed": self._text(ref, "GBReference_pubmed"),
                }
            )
        return refs

    def _gene_info(self, seq: ET.Element) -> dict[str, Any]:
        for feature in seq.findall(".//GBFeature"):
            if self._text(feature, "GBFeature_key") != "gene":
                continue
            quals = self._feature_quals(feature)
            return {
                "name": (quals.get("gene") or [""])[0],
                "locusTag": (quals.get("locus_tag") or [""])[0],
                "location": self._text(feature, "GBFeature_location"),
                "synonyms": (quals.get("gene_synonym") or [""])[0],
                "dbXrefs": quals.get("db_xref") or [],
                "notes": quals.get("note") or [],
            }
        return {}

    def _source_feature(self, seq: ET.Element) -> dict[str, Any]:
        for feature in seq.findall(".//GBFeature"):
            if self._text(feature, "GBFeature_key") != "source":
                continue
            return self._feature_quals(feature)
        return {}

    def _feature_quals(self, feature: ET.Element) -> dict[str, list[str]]:
        quals: dict[str, list[str]] = {}
        for qualifier in feature.findall(".//GBQualifier"):
            name = self._text(qualifier, "GBQualifier_name")
            value = self._text(qualifier, "GBQualifier_value")
            if name:
                quals.setdefault(name, []).append(value)
        return quals

    def _tax_id(self, seq: ET.Element) -> str:
        for xref in seq.findall(".//GBQualifier"):
            if self._text(xref, "GBQualifier_name") == "db_xref":
                value = self._text(xref, "GBQualifier_value")
                if value.startswith("taxon:"):
                    return value.split(":", 1)[1]
        return ""

    def _sequence_from_fasta(self, fasta: str) -> str:
        return "".join(line.strip() for line in fasta.splitlines() if not line.startswith(">")).upper()

    def _normalise_fasta(self, accession: str, title: str, sequence: str) -> str:
        lines = [f">{accession} {title}".strip()]
        lines.extend(sequence[i : i + 70] for i in range(0, len(sequence), 70))
        return "\n".join(lines)

    def _unsupported_base_summary(self, sequence: str) -> list[dict[str, Any]]:
        counts = Counter(base for base in sequence.upper() if base not in {"A", "T", "G", "C"})
        return [
            {
                "base": base,
                "count": count,
                "firstPositions": [idx + 1 for idx, char in enumerate(sequence.upper()) if char == base][:20],
                "knownAmbiguity": base in DNA_AMBIGUITY,
            }
            for base, count in sorted(counts.items())
        ]

    def _atgc_regions(self, sequence: str) -> list[dict[str, int]]:
        regions: list[dict[str, int]] = []
        start: int | None = None
        for index, base in enumerate(sequence.upper(), start=1):
            if base in {"A", "T", "G", "C"}:
                if start is None:
                    start = index
            elif start is not None:
                regions.append({"start": start, "end": index - 1, "length": index - start})
                start = None
        if start is not None:
            regions.append({"start": start, "end": len(sequence), "length": len(sequence) - start + 1})
        return regions

    def _looks_like_dna(self, sequence: str, molecule_type: str) -> bool:
        if "rna" in molecule_type.lower() or "protein" in molecule_type.lower():
            return False
        return bool(sequence) and "U" not in set(sequence.upper())

    def _gdv_url(self, scientific_name: str) -> str:
        slug = scientific_name.strip().lower().replace(" ", "-")
        return f"https://www.ncbi.nlm.nih.gov/gdv?org={quote(slug)}" if slug else "https://www.ncbi.nlm.nih.gov/gdv"

    def _wikimedia_image(self, scientific_name: str) -> dict[str, str] | None:
        query = scientific_name.strip()
        if not query:
            return None
        try:
            response = self.client.http.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": query,
                    "gsrlimit": 1,
                    "prop": "pageimages|description|info",
                    "piprop": "thumbnail|original",
                    "pithumbsize": 700,
                    "inprop": "url",
                    "format": "json",
                    "origin": "*",
                },
                timeout=self.client.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            return None
        pages = (data.get("query") or {}).get("pages") or {}
        if not pages:
            return None
        page = next(iter(pages.values()))
        image_url = ((page.get("thumbnail") or {}).get("source") or (page.get("original") or {}).get("source") or "")
        if not image_url:
            return None
        return {
            "url": str(image_url),
            "source": "Wikimedia/Wikipedia",
            "title": str(page.get("title") or query),
            "description": str(page.get("description") or ""),
            "pageUrl": str(page.get("fullurl") or ""),
        }
