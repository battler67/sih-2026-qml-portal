from __future__ import annotations

import io
import re
import zipfile

from .client import NcbiClient
from .exceptions import NcbiValidationError
from .models import AssemblyRecord, DatabaseScope, RecordMetadata, SearchRequest, SequenceRecord


class NcbiDatasetsProvider:
    def __init__(self, client: NcbiClient | None = None) -> None:
        self.client = client or NcbiClient()

    def search_records(self, request: SearchRequest) -> list[RecordMetadata]:
        assemblies = self.search_assemblies(request)
        return [
            RecordMetadata(
                accession=item.accession,
                title=item.assembly_name,
                organism=item.organism,
                taxId=item.tax_id,
                sourceDatabase=item.source_database,
                moleculeType="genomic DNA",
                assemblyAccession=item.accession,
            )
            for item in assemblies
        ]

    def get_record_metadata(self, accessions: list[str]) -> list[RecordMetadata]:
        request = SearchRequest(
            querySource="pasted",
            querySequence="ACGT",
            algorithm="grover",
            databaseScope="exact_assembly",
            assemblyAccessions=accessions,
        )
        return self.search_records(request)

    def fetch_sequences(self, accessions: list[str], request: SearchRequest | None = None) -> list[SequenceRecord]:
        for accession in accessions:
            if not re.match(r"^GC[AF]_\d+\.\d+$", accession):
                raise NcbiValidationError("Only exact GCA/GCF assembly accessions are accepted for Datasets downloads")
        params = {"include_annotation_type": "GENOME_FASTA", "filename": "ncbi_dataset.zip"}
        data = self.client.get_bytes(
            self.client.datasets_url(f"genome/accession/{','.join(accessions)}/download"),
            params,
            cache_key=f"datasets-download:{','.join(accessions)}",
        )
        return self._parse_genomic_fna_zip(data, accessions)

    def search_assemblies(self, request: SearchRequest) -> list[AssemblyRecord]:
        if request.database_scope == DatabaseScope.exact_assembly:
            accessions = request.assembly_accessions
            path = f"genome/accession/{','.join(accessions)}/dataset_report"
            params = {"page_size": request.max_records}
        else:
            taxon = request.tax_id if request.database_scope == DatabaseScope.taxonomy_assemblies else request.organism
            if not taxon:
                raise NcbiValidationError("Organism or taxonomy ID is required for Datasets genome search")
            path = f"genome/taxon/{taxon}/dataset_report"
            params = {"page_size": request.max_records}
            if request.database_scope in {DatabaseScope.refseq_reference, DatabaseScope.refseq_representative, DatabaseScope.refseq_gcf}:
                params["assembly_source"] = "RefSeq"
            if request.database_scope == DatabaseScope.genbank_gca:
                params["assembly_source"] = "GenBank"
            if request.database_scope == DatabaseScope.refseq_reference:
                params["reference"] = "true"
        data = self.client.get_json(
            self.client.datasets_url(path),
            params,
            cache_key=f"datasets-report:{path}:{params}",
        )
        reports = data.get("reports") or data.get("assemblies") or []
        if not isinstance(reports, list):
            raise NcbiValidationError("NCBI Datasets returned an unexpected assembly report")
        parsed = [self._assembly_from_report(item) for item in reports]
        filtered = [item for item in parsed if self._scope_accepts(item, request.database_scope)]
        if not filtered:
            raise NcbiValidationError("No genomic DNA assemblies matched the selected scope")
        return filtered[: request.max_records]

    def _assembly_from_report(self, item: dict) -> AssemblyRecord:
        assembly = item.get("assembly_info") or item.get("assembly") or item
        org = item.get("organism") or {}
        accession = str(assembly.get("assembly_accession") or assembly.get("accession") or item.get("accession") or "")
        source = "RefSeq" if accession.startswith("GCF_") else "GenBank"
        refcat = str(assembly.get("refseq_category") or "").lower()
        return AssemblyRecord(
            accession=accession,
            assemblyName=str(assembly.get("assembly_name") or assembly.get("name") or accession),
            organism=org.get("organism_name") or item.get("organism_name"),
            taxId=str(org.get("tax_id") or item.get("tax_id") or "") or None,
            sourceDatabase=source,
            reference="reference" in refcat,
            representative="representative" in refcat,
        )

    def _scope_accepts(self, item: AssemblyRecord, scope: DatabaseScope) -> bool:
        if scope == DatabaseScope.genbank_gca:
            return item.source_database == "GenBank" and item.accession.startswith("GCA_")
        if scope in {DatabaseScope.refseq_gcf, DatabaseScope.refseq_reference, DatabaseScope.refseq_representative}:
            if item.source_database != "RefSeq" or not item.accession.startswith("GCF_"):
                return False
            if scope == DatabaseScope.refseq_reference:
                return item.reference
            if scope == DatabaseScope.refseq_representative:
                return item.representative or item.reference
        return bool(item.accession)

    def _parse_genomic_fna_zip(self, data: bytes, accessions: list[str]) -> list[SequenceRecord]:
        records: list[SequenceRecord] = []
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            genomic_names = [
                name for name in archive.namelist() if name.endswith("_genomic.fna") or name.endswith("genomic.fna")
            ]
            if not genomic_names:
                raise NcbiValidationError("NCBI Datasets package did not contain a genomic FASTA file")
            for name in genomic_names:
                if any(bad in name.lower() for bad in ("rna", "protein", "cds", "fastq")):
                    raise NcbiValidationError("NCBI Datasets package contained a non-genomic sequence file")
                text = archive.read(name).decode("utf-8", errors="replace")
                records.extend(self._parse_fasta(text, accessions))
        return records

    def _parse_fasta(self, text: str, accessions: list[str]) -> list[SequenceRecord]:
        records: list[SequenceRecord] = []
        title = ""
        parts: list[str] = []
        for line in text.splitlines():
            if line.startswith(">"):
                if title:
                    records.append(self._record(title, parts, accessions))
                title = line[1:].strip()
                parts = []
            else:
                parts.append(line.strip())
        if title:
            records.append(self._record(title, parts, accessions))
        return records

    def _record(self, title: str, parts: list[str], accessions: list[str]) -> SequenceRecord:
        accession = title.split()[0]
        assembly = next((item for item in accessions if item in title), accessions[0] if accessions else None)
        return SequenceRecord(
            accession=accession,
            title=title,
            sequence="".join(parts).upper(),
            sourceDatabase="NCBI Datasets Genome",
            moleculeType="genomic DNA",
            assemblyAccession=assembly,
        )
