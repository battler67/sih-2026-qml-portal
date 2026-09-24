from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Algorithm(str, Enum):
    frqi = "frqi"
    grover = "grover"
    hybrid = "hybrid"


class QuerySource(str, Enum):
    pasted = "pasted"
    uploaded_fasta = "uploaded_fasta"
    ncbi_accession = "ncbi_accession"


class DatabaseScope(str, Enum):
    refseq_reference = "refseq_reference"
    refseq_representative = "refseq_representative"
    genbank_gca = "genbank_gca"
    refseq_gcf = "refseq_gcf"
    organism_assemblies = "organism_assemblies"
    taxonomy_assemblies = "taxonomy_assemblies"
    exact_assembly = "exact_assembly"
    exact_genomic_nucleotide = "exact_genomic_nucleotide"
    gene_on_assembly = "gene_on_assembly"
    uploaded_fasta = "uploaded_fasta"
    pasted_sequence = "pasted_sequence"


class SequenceRecord(BaseModel):
    accession: str
    title: str
    organism: str | None = None
    tax_id: str | None = Field(default=None, alias="taxId")
    sequence: str
    source_database: str = Field(default="NCBI", alias="sourceDatabase")
    molecule_type: str = Field(default="genomic DNA", alias="moleculeType")
    chromosome: str | None = None
    assembly_accession: str | None = Field(default=None, alias="assemblyAccession")

    model_config = ConfigDict(populate_by_name=True)


class RecordMetadata(BaseModel):
    accession: str
    title: str
    organism: str | None = None
    tax_id: str | None = Field(default=None, alias="taxId")
    source_database: str = Field(default="NCBI", alias="sourceDatabase")
    molecule_type: str = Field(default="genomic DNA", alias="moleculeType")
    assembly_accession: str | None = Field(default=None, alias="assemblyAccession")

    model_config = ConfigDict(populate_by_name=True)


class AssemblyRecord(BaseModel):
    accession: str
    assembly_name: str = Field(alias="assemblyName")
    organism: str | None = None
    tax_id: str | None = Field(default=None, alias="taxId")
    source_database: Literal["RefSeq", "GenBank"] = Field(alias="sourceDatabase")
    reference: bool = False
    representative: bool = False
    model_config = ConfigDict(populate_by_name=True)


class SearchRequest(BaseModel):
    query_source: QuerySource = Field(default=QuerySource.pasted, alias="querySource")
    query_sequence: str | None = Field(default=None, alias="querySequence")
    reference_sequence: str | None = Field(default=None, alias="referenceSequence")
    query_accession: str | None = Field(default=None, alias="queryAccession")
    uploaded_fasta: str | None = Field(default=None, alias="uploadedFasta")
    algorithm: Algorithm = Algorithm.grover
    database_scope: DatabaseScope = Field(default=DatabaseScope.organism_assemblies, alias="databaseScope")
    organism: str | None = None
    tax_id: str | None = Field(default=None, alias="taxId")
    gene: str | None = None
    assembly_accessions: list[str] = Field(default_factory=list, alias="assemblyAccessions")
    nucleotide_accessions: list[str] = Field(default_factory=list, alias="nucleotideAccessions")
    max_records: int = Field(default=25, ge=1, le=100, alias="maxRecords")
    max_bases_per_record: int = Field(default=10000, ge=1, le=1000000, alias="maxBasesPerRecord")
    max_total_bases: int = Field(default=50000, ge=1, le=1000000, alias="maxTotalBases")
    max_windows: int = Field(default=64, ge=1, le=512, alias="maxWindows")
    max_query_length: int = Field(default=32, ge=1, le=128, alias="maxQueryLength")
    strand: Literal["forward", "both"] = "both"
    window_stride: int = Field(default=1, ge=1, le=1000, alias="windowStride")
    shots: int = Field(default=1024, ge=1, le=8192)
    simulator: Literal["aer"] = "aer"
    grover_boundary_mode: Literal["boundary_safe", "paper_cyclic"] = Field(
        default="boundary_safe",
        alias="groverBoundaryMode",
    )
    mismatch_threshold: int = Field(default=0, ge=0, le=0, alias="mismatchThreshold")
    enable_classical_validation: bool = Field(default=False, alias="enableClassicalValidation")
    enable_blast_baseline: bool = Field(default=False, alias="enableBlastBaseline")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("organism", "gene", mode="before")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_scope(self) -> "SearchRequest":
        if self.query_source == QuerySource.pasted and not self.query_sequence:
            raise ValueError("querySequence is required for pasted queries")
        if self.query_source == QuerySource.uploaded_fasta and not self.uploaded_fasta:
            raise ValueError("uploadedFasta is required for uploaded FASTA queries")
        if self.query_source == QuerySource.ncbi_accession and not self.query_accession:
            raise ValueError("queryAccession is required for NCBI accession queries")
        if self.database_scope == DatabaseScope.organism_assemblies and not self.organism:
            raise ValueError("organism is required for organism assembly searches")
        if self.database_scope == DatabaseScope.taxonomy_assemblies and not self.tax_id:
            raise ValueError("taxId is required for taxonomy assembly searches")
        if self.database_scope == DatabaseScope.exact_assembly and not self.assembly_accessions:
            raise ValueError("assemblyAccessions must contain at least one GCA/GCF accession")
        if self.database_scope == DatabaseScope.exact_genomic_nucleotide and not self.nucleotide_accessions:
            raise ValueError("nucleotideAccessions must contain exact nucleotide accessions")
        if self.database_scope == DatabaseScope.gene_on_assembly and (not self.gene or not self.assembly_accessions):
            raise ValueError("gene searches require a gene and a user-selected genome assembly")
        if self.database_scope == DatabaseScope.uploaded_fasta and not self.uploaded_fasta:
            raise ValueError("uploadedFasta is required for the uploaded FASTA reference scope")
        if self.database_scope == DatabaseScope.pasted_sequence and not self.reference_sequence:
            raise ValueError("referenceSequence is required for the pasted genomic DNA scope")
        if self.algorithm == Algorithm.hybrid:
            if (
                self.query_source != QuerySource.pasted
                or self.database_scope != DatabaseScope.pasted_sequence
            ):
                raise ValueError(
                    "Hybrid mode requires pasted query and reference sequences"
                )
            query = "".join((self.query_sequence or "").split()).upper()
            reference = "".join((self.reference_sequence or "").split()).upper()
            if len(query) != len(reference):
                raise ValueError(
                    "Hybrid mismatch comparison requires equal-length query and reference sequences"
                )
        return self


class WindowRecord(BaseModel):
    accession: str
    record_title: str = Field(alias="recordTitle")
    organism: str | None = None
    tax_id: str | None = Field(default=None, alias="taxId")
    source_database: str = Field(alias="sourceDatabase")
    chromosome: str | None = None
    strand: Literal["forward", "reverse"]
    start_zero_based: int = Field(alias="startZeroBased")
    end_zero_based: int = Field(alias="endZeroBased")
    sequence: str

    model_config = ConfigDict(populate_by_name=True)

    @property
    def display_start(self) -> int:
        return self.start_zero_based + 1

    @property
    def display_end(self) -> int:
        return self.end_zero_based


class RetrievalSummary(BaseModel):
    provider: str
    record_count: int = Field(alias="recordCount")
    total_bases: int = Field(alias="totalBases")
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), alias="retrievedAt")

    model_config = ConfigDict(populate_by_name=True)


class SearchEstimate(BaseModel):
    input_query_length: int = Field(alias="inputQueryLength")
    quantum_window_length: int = Field(alias="quantumWindowLength")
    input_truncated_for_quantum: bool = Field(alias="inputTruncatedForQuantum")
    record_count: int = Field(alias="recordCount")
    total_bases: int = Field(alias="totalBases")
    total_windows: int = Field(alias="totalWindows")
    accepted_windows: int = Field(alias="acceptedWindows")
    skipped_windows: int = Field(alias="skippedWindows")
    ambiguous_bases: int = Field(alias="ambiguousBases")
    estimated_quantum_runs: int = Field(alias="estimatedQuantumRuns")
    estimated_shots: int = Field(alias="estimatedShots")
    estimated_logical_qubits: int = Field(alias="estimatedLogicalQubits")
    estimated_grover_iterations: int = Field(alias="estimatedGroverIterations")
    exceeds_simulator_limits: bool = Field(alias="exceedsSimulatorLimits")
    hardware_eligible: bool = Field(alias="hardwareEligible")
    hardware_qubit_capacity: int = Field(alias="hardwareQubitCapacity")
    hardware_eligibility_note: str = Field(alias="hardwareEligibilityNote")
    sampling_or_truncation: bool = Field(alias="samplingOrTruncation")
    warnings: list[str]
    estimate_mode: Literal["metadata_only"] = Field(
        default="metadata_only", alias="estimateMode"
    )
    estimated_simulation_seconds_min: int = Field(
        alias="estimatedSimulationSecondsMin"
    )
    estimated_simulation_seconds_max: int = Field(
        alias="estimatedSimulationSecondsMax"
    )
    estimated_end_to_end_seconds_min: int = Field(
        alias="estimatedEndToEndSecondsMin"
    )
    estimated_end_to_end_seconds_max: int = Field(
        alias="estimatedEndToEndSecondsMax"
    )
    runtime_estimate_note: str = Field(alias="runtimeEstimateNote")
    quantum_alphabet: Literal["ACGT"] = Field(default="ACGT", alias="quantumAlphabet")

    model_config = ConfigDict(populate_by_name=True)
