import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { motion, type Variants } from "framer-motion";
import {
  ArrowLeft,
  ChevronDown,
  Database,
  Dna,
  Download,
  ExternalLink,
  FileJson,
  FileText,
  FlaskConical,
  ImageIcon,
  Loader2,
  Network,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { BackgroundFX } from "@/components/BackgroundFX";
import { LoadingInsight } from "@/components/LoadingInsight";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { findDemoGenomeImage } from "@/lib/demo-genome-images";
import { fetchGenomeViewerContext, type GenomeViewerContext } from "@/lib/genome-viewer";

const API_BASE = import.meta.env.VITE_QUANTUM_API_BASE_URL || "http://127.0.0.1:8000";

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 16, filter: "blur(6px)" },
  show: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] as const },
  },
};

type RecordDetail = {
  overview: {
    accession: string;
    recordTitle: string;
    geneName: string;
    source: string;
    moleculeType: string;
    lastUpdated: string;
    sequenceLength: number;
    ncbiUrl: string;
  };
  organism: {
    organismName: string;
    scientificName: string;
    taxonomy: string;
    taxId: string;
  };
  gene: Record<string, unknown>;
  sequence: {
    length: number;
    moleculeType: string;
    unsupportedBases: Array<{ base: string; count: number; firstPositions: number[] }>;
    atgcRegions: Array<{ start: number; end: number; length: number }>;
  };
  references: Array<Record<string, string>>;
  source: Record<string, unknown>;
  fasta: string;
  rawSequence: string;
};

type SectionKey =
  | "overview"
  | "organism"
  | "taxonomy"
  | "gene"
  | "identifiers"
  | "sequence"
  | "references"
  | "fasta"
  | "complete";

const sectionLabels: Array<{ key: SectionKey; label: string }> = [
  { key: "overview", label: "Record overview" },
  { key: "organism", label: "Organism details" },
  { key: "taxonomy", label: "Taxonomy details" },
  { key: "gene", label: "Gene information" },
  { key: "identifiers", label: "Accession and identifiers" },
  { key: "sequence", label: "Sequence metadata" },
  { key: "references", label: "References" },
  { key: "fasta", label: "FASTA sequence" },
  { key: "complete", label: "Complete record" },
];

export function NcbiRecordDetails({ accession }: { accession: string }) {
  const [record, setRecord] = useState<RecordDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [genomeViewer, setGenomeViewer] = useState<GenomeViewerContext | null>(null);
  const [genomeViewerLoading, setGenomeViewerLoading] = useState(false);
  const [genomeViewerError, setGenomeViewerError] = useState("");
  const [format, setFormat] = useState<"json" | "csv" | "txt" | "fasta">("json");
  const [selected, setSelected] = useState<Record<SectionKey, boolean>>({
    overview: true,
    organism: true,
    taxonomy: false,
    gene: true,
    identifiers: true,
    sequence: true,
    references: false,
    fasta: false,
    complete: false,
  });

  useEffect(() => {
    let ignore = false;
    async function loadRecord() {
      setLoading(true);
      setError("");
      try {
        const response = await fetch(
          `${API_BASE}/api/ncbi/entrez/records/${encodeURIComponent(accession)}`,
        );
        const body = await response.json().catch(() => ({ detail: response.statusText }));
        if (!response.ok) throw new Error(String(body.detail || response.statusText));
        if (!ignore) setRecord(body);
      } catch (err) {
        if (!ignore) setError(err instanceof Error ? err.message : "Record lookup failed");
      } finally {
        if (!ignore) setLoading(false);
      }
    }
    loadRecord();
    return () => {
      ignore = true;
    };
  }, [accession]);

  useEffect(() => {
    const taxId = record?.organism.taxId;
    if (!taxId) {
      setGenomeViewer(null);
      setGenomeViewerError("");
      return;
    }
    const selectedTaxId = taxId;
    let ignore = false;
    async function loadGenomeViewer() {
      setGenomeViewerLoading(true);
      setGenomeViewerError("");
      try {
        const body = await fetchGenomeViewerContext(API_BASE, selectedTaxId);
        if (!ignore) setGenomeViewer(body);
      } catch (err) {
        if (!ignore)
          setGenomeViewerError(
            err instanceof Error ? err.message : "Could not load genome viewer context",
          );
      } finally {
        if (!ignore) setGenomeViewerLoading(false);
      }
    }
    loadGenomeViewer();
    return () => {
      ignore = true;
    };
  }, [record?.organism.taxId]);

  const selectedData = useMemo(
    () => (record ? buildSelectedData(record, selected) : {}),
    [record, selected],
  );
  const filename = record ? buildFilename(record, format) : `NCBI_${accession}.${format}`;
  const downloadData = record ? buildDownloadData(record, selectedData, format) : "";
  const canAnalyze = record ? isDnaRecord(record.overview.moleculeType) : false;
  const displayedGenomeViewer = useMemo(() => {
    if (!record || !genomeViewer) return genomeViewer;
    const demoImage = findDemoGenomeImage({
      gene: record.overview.geneName,
      organism: record.organism.organismName,
      scientificName: record.organism.scientificName,
      taxId: record.organism.taxId,
      accession: record.overview.accession,
    });
    return demoImage ? { ...genomeViewer, image: demoImage } : genomeViewer;
  }, [genomeViewer, record]);

  return (
    <div className="relative min-h-screen overflow-x-hidden">
      <BackgroundFX />
      <header className="sticky top-0 z-30 border-b border-white/5 bg-background/60 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-6 py-4">
          <Link
            to="/ncbi/search"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" /> Search results
          </Link>
          <div className="flex items-center gap-2">
            <div className="relative h-8 w-8 rounded-lg bg-gradient-to-br from-emerald to-cyan-glow glow-emerald">
              <Dna className="absolute inset-0 m-auto h-4 w-4 text-background" />
            </div>
            <span className="font-display text-lg font-semibold">NCBI Record</span>
          </div>
          {record ? (
            <a
              href={record.overview.ncbiUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
            >
              NCBI <ExternalLink className="h-3.5 w-3.5" />
            </a>
          ) : (
            <span />
          )}
        </div>
      </header>

      <main className="mx-auto max-w-[1400px] space-y-6 p-6 lg:p-8">
        {loading && (
          <>
            <LoadingInsight title={`Loading NCBI record ${accession}`} />
            <div className="glass rounded-2xl p-6 text-sm text-muted-foreground" role="status">
              <Loader2 className="mr-2 inline h-4 w-4 animate-spin text-emerald" /> Loading complete
              NCBI record
            </div>
          </>
        )}
        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
            {error}
          </div>
        )}
        {record && (
          <>
            <motion.div
              variants={fadeUp}
              initial="hidden"
              animate="show"
              className="flex min-w-0 flex-wrap items-start justify-between gap-4"
            >
              <div className="min-w-0 flex-1">
                <div className="text-xs uppercase tracking-widest text-emerald">
                  {record.overview.accession}
                </div>
                <h1 className="mt-1 max-w-5xl break-words font-display text-3xl font-semibold tracking-tight">
                  {record.overview.recordTitle}
                </h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  {record.organism.organismName} - {record.overview.source} -{" "}
                  {record.overview.sequenceLength.toLocaleString()} bp
                </p>
              </div>
              {canAnalyze ? (
                <a
                  href={`/quantum-search?analysisAccession=${encodeURIComponent(record.overview.accession)}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-full bg-emerald px-4 py-2 text-sm font-semibold text-primary-foreground glow-emerald"
                >
                  <FlaskConical className="h-4 w-4" /> Sequence Analysis
                </a>
              ) : (
                <span className="inline-flex items-center gap-2 rounded-full border border-yellow-400/20 bg-yellow-400/10 px-4 py-2 text-sm text-yellow-100">
                  <FlaskConical className="h-4 w-4" /> Genomic DNA required
                </span>
              )}
            </motion.div>

            <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.46fr)]">
              <div className="min-w-0 space-y-4">
                <Panel title="Overview" eyebrow="Important details" icon={Database}>
                  <InfoGrid
                    rows={[
                      ["Gene", record.overview.geneName || "Not specified"],
                      ["Accession", record.overview.accession],
                      ["Record source", record.overview.source],
                      ["Molecule type", record.overview.moleculeType],
                      ["Last updated", record.overview.lastUpdated || "Not available"],
                      ["Sequence length", `${record.overview.sequenceLength.toLocaleString()} bp`],
                    ]}
                  />
                </Panel>

                <Panel title="Organism and Taxonomy" eyebrow="Biological source" icon={Dna}>
                  <InfoGrid
                    rows={[
                      ["Organism", record.organism.organismName],
                      ["Scientific name", record.organism.scientificName],
                      ["Taxonomy ID", record.organism.taxId || "Not available"],
                    ]}
                  />
                  <CollapsibleSection title="Taxonomy lineage">
                    <p className="text-sm text-muted-foreground">
                      {record.organism.taxonomy || "No taxonomy lineage returned."}
                    </p>
                  </CollapsibleSection>
                </Panel>

                <Panel title="Gene Information" eyebrow="Annotated feature" icon={FileJson}>
                  <JsonBlock
                    data={record.gene}
                    empty="No gene feature was returned in the GenBank record."
                  />
                </Panel>

                <Panel title="Sequence Information" eyebrow="DNA validation" icon={FileJson}>
                  <InfoGrid
                    rows={[
                      ["Length", `${record.sequence.length.toLocaleString()} bp`],
                      ["Molecule type", record.sequence.moleculeType],
                    ]}
                  />
                  <CollapsibleSection title="Unsupported base summary">
                    {record.sequence.unsupportedBases.length > 0 ? (
                      <div className="space-y-2 text-sm">
                        {record.sequence.unsupportedBases.map((item) => (
                          <div
                            key={item.base}
                            className="rounded-lg border border-yellow-400/20 bg-yellow-400/10 p-3 text-yellow-100"
                          >
                            {item.base}: {item.count.toLocaleString()} occurrences; first positions{" "}
                            {item.firstPositions.join(", ")}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        No unsupported bases detected.
                      </p>
                    )}
                  </CollapsibleSection>
                </Panel>

                <Panel
                  title="References and Source"
                  eyebrow="Less frequent metadata"
                  icon={FileText}
                >
                  <CollapsibleSection title="References">
                    {record.references.length > 0 ? (
                      <div className="space-y-3">
                        {record.references.map((reference, index) => (
                          <div
                            key={`${reference.title}-${index}`}
                            className="rounded-lg border border-white/10 bg-white/5 p-3 text-sm"
                          >
                            <div className="font-medium">
                              {reference.title || "Untitled reference"}
                            </div>
                            <div className="mt-1 text-muted-foreground">{reference.journal}</div>
                            {reference.pubmed && (
                              <div className="mt-1 font-mono text-xs text-emerald">
                                PubMed {reference.pubmed}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No references returned.</p>
                    )}
                  </CollapsibleSection>
                  <CollapsibleSection title="Source feature">
                    <JsonBlock data={record.source} empty="No source metadata returned." />
                  </CollapsibleSection>
                </Panel>

                <Panel title="Raw FASTA Sequence" eyebrow="Sequence data" icon={FileText}>
                  <pre className="max-h-96 max-w-full overflow-auto rounded-xl bg-black/40 p-4 font-mono text-xs text-muted-foreground">
                    {record.fasta}
                  </pre>
                </Panel>
              </div>

              <div className="min-w-0 space-y-4">
                <Panel title="Genome Data Viewer" eyebrow="Taxonomy context" icon={Network}>
                  <GenomeViewerPanel
                    record={record}
                    context={displayedGenomeViewer}
                    loading={genomeViewerLoading}
                    error={genomeViewerError}
                  />
                </Panel>

                <Panel title="Download Record" eyebrow="Selective download" icon={Download}>
                  <div className="space-y-3">
                    <div className="grid gap-2">
                      {sectionLabels.map((item) => (
                        <label
                          key={item.key}
                          className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 p-2 text-sm"
                        >
                          <Checkbox
                            checked={selected[item.key]}
                            onCheckedChange={(checked) =>
                              setSelected((current) => ({
                                ...current,
                                [item.key]: checked === true,
                              }))
                            }
                          />
                          {item.label}
                        </label>
                      ))}
                    </div>
                    <select
                      value={format}
                      onChange={(event) =>
                        setFormat(event.target.value as "json" | "csv" | "txt" | "fasta")
                      }
                      className="theme-select w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm"
                    >
                      <option value="json">JSON</option>
                      <option value="csv">CSV metadata</option>
                      <option value="txt">TXT</option>
                      <option value="fasta">FASTA</option>
                    </select>
                    <a
                      href={`data:text/plain;charset=utf-8,${encodeURIComponent(downloadData)}`}
                      download={filename}
                      className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-emerald px-4 py-2 text-sm font-semibold text-primary-foreground glow-emerald"
                    >
                      <Download className="h-4 w-4" /> Download {format.toUpperCase()}
                    </a>
                  </div>
                </Panel>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

function GenomeViewerPanel({
  record,
  context,
  loading,
  error,
}: {
  record: RecordDetail;
  context: GenomeViewerContext | null;
  loading: boolean;
  error: string;
}) {
  if (!record.organism.taxId) {
    return (
      <p className="text-sm text-muted-foreground">No taxonomy ID was returned for this record.</p>
    );
  }
  if (loading) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-muted-foreground">
        <Loader2 className="mr-2 inline h-4 w-4 animate-spin text-emerald" /> Loading taxonomy tree
      </div>
    );
  }
  if (error) {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300">
        {error}
      </div>
    );
  }
  if (!context) {
    return <p className="text-sm text-muted-foreground">Taxonomy context is unavailable.</p>;
  }
  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-xl border border-white/10 bg-black/20">
        {context.image ? (
          <>
            <img
              src={context.image.url}
              alt={context.image.title || context.scientificName}
              className={`h-48 w-full ${
                context.image.source === "Local demo image"
                  ? "bg-white object-contain"
                  : "object-cover"
              }`}
              referrerPolicy="no-referrer"
            />
            {(context.image.title || context.image.description) && (
              <div className="border-t border-white/10 p-3">
                <div className="text-sm font-semibold">
                  {context.image.title || context.scientificName}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {context.image.description || context.image.source}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex h-48 flex-col items-center justify-center gap-2 p-4 text-center text-sm text-muted-foreground">
            <ImageIcon className="h-6 w-6 text-emerald" />
            No free organism image found
          </div>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <MetricBox
          label="Selected organism"
          value={context.scientificName || record.organism.scientificName}
        />
        <MetricBox label="Taxonomy ID" value={context.taxId} />
        <MetricBox label="Rank" value={context.rank || "Not available"} />
        <MetricBox label="Division" value={context.division || "Not available"} />
      </div>

      <TaxonomyTree nodes={context.treeNodes} />

      <div className="flex flex-wrap gap-2">
        <Link
          to="/ncbi/organism/$taxId"
          params={{ taxId: context.taxId }}
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs hover:bg-white/10"
        >
          View Organism Details
        </Link>
        <a
          href={context.links.genomeDataViewer}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs hover:bg-white/10"
        >
          NCBI GDV <ExternalLink className="h-3.5 w-3.5" />
        </a>
        {context.image?.pageUrl ? (
          <a
            href={context.image.pageUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs hover:bg-white/10"
          >
            Image Source <ExternalLink className="h-3.5 w-3.5" />
          </a>
        ) : null}
      </div>
    </div>
  );
}

function TaxonomyTree({ nodes }: { nodes: GenomeViewerContext["treeNodes"] }) {
  const visibleNodes = nodes.filter((node) => node.scientificName);
  if (visibleNodes.length === 0) {
    return <p className="text-sm text-muted-foreground">No taxonomy lineage returned.</p>;
  }
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-4">
      <div className="mb-3 text-xs uppercase tracking-widest text-emerald">
        Phylogenetic placement
      </div>
      <div className="space-y-0">
        {visibleNodes.map((node, index) => (
          <div key={`${node.taxId}-${index}`} className="relative flex gap-3">
            <div className="flex w-8 shrink-0 flex-col items-center">
              <span
                className={`h-4 w-4 rounded-full border ${node.isSelected ? "border-emerald bg-emerald glow-emerald" : "border-emerald/60 bg-background"}`}
              />
              {index < visibleNodes.length - 1 ? (
                <span className="h-10 w-px bg-emerald/40" />
              ) : null}
            </div>
            <div
              className={`mb-3 min-w-0 flex-1 rounded-lg border p-3 ${node.isSelected ? "border-emerald/50 bg-emerald/10" : "border-white/10 bg-black/20"}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0 break-words text-sm font-semibold">
                  {node.scientificName}
                </div>
                {node.isSelected ? (
                  <span className="rounded-full bg-emerald px-2 py-0.5 text-[10px] font-semibold text-primary-foreground">
                    Selected
                  </span>
                ) : null}
              </div>
              <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                <span>{node.rank || "no rank"}</span>
                <span className="font-mono text-emerald">{node.taxId}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-xl border border-white/10 bg-white/5 p-3">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="mt-1 break-words text-sm text-foreground">{value}</div>
    </div>
  );
}

function InfoGrid({ rows }: { rows: Array<[string, string]> }) {
  return (
    <div className="grid min-w-0 gap-3 sm:grid-cols-2">
      {rows.map(([label, value]) => (
        <div key={label} className="min-w-0 rounded-xl border border-white/10 bg-white/5 p-3">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
          <div className="mt-1 break-words text-sm text-foreground">{value}</div>
        </div>
      ))}
    </div>
  );
}

function CollapsibleSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Collapsible className="mt-3 rounded-xl border border-white/10 bg-white/5">
      <CollapsibleTrigger className="flex w-full items-center justify-between px-3 py-2 text-left text-sm">
        {title}
        <ChevronDown className="h-4 w-4 text-muted-foreground" />
      </CollapsibleTrigger>
      <CollapsibleContent className="border-t border-white/10 p-3">{children}</CollapsibleContent>
    </Collapsible>
  );
}

function JsonBlock({ data, empty }: { data: unknown; empty: string }) {
  if (!data || (typeof data === "object" && Object.keys(data).length === 0)) {
    return <p className="text-sm text-muted-foreground">{empty}</p>;
  }
  return (
    <pre className="max-h-80 max-w-full overflow-auto rounded-xl bg-black/40 p-4 font-mono text-xs text-muted-foreground">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

function Panel({
  title,
  eyebrow,
  icon: Icon,
  children,
}: {
  title: string;
  eyebrow: string;
  icon: LucideIcon;
  children: ReactNode;
}) {
  return (
    <motion.section
      variants={fadeUp}
      initial="hidden"
      animate="show"
      className="glass min-w-0 overflow-hidden rounded-2xl p-5"
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-emerald">{eyebrow}</div>
          <h2 className="mt-1 font-display text-xl font-semibold">{title}</h2>
        </div>
        <Icon className="h-5 w-5 text-emerald" />
      </div>
      {children}
    </motion.section>
  );
}

function buildSelectedData(record: RecordDetail, selected: Record<SectionKey, boolean>) {
  if (selected.complete) return record;
  const data: Record<string, unknown> = {};
  if (selected.overview) data.overview = record.overview;
  if (selected.organism)
    data.organism = {
      organismName: record.organism.organismName,
      scientificName: record.organism.scientificName,
    };
  if (selected.taxonomy)
    data.taxonomy = { taxonomy: record.organism.taxonomy, taxId: record.organism.taxId };
  if (selected.gene) data.gene = record.gene;
  if (selected.identifiers)
    data.identifiers = { accession: record.overview.accession, ncbiUrl: record.overview.ncbiUrl };
  if (selected.sequence) data.sequence = record.sequence;
  if (selected.references) data.references = record.references;
  if (selected.fasta) data.fasta = record.fasta;
  return data;
}

function buildDownloadData(
  record: RecordDetail,
  data: Record<string, unknown>,
  format: "json" | "csv" | "txt" | "fasta",
) {
  if (format === "json") return JSON.stringify(data, null, 2);
  if (format === "fasta") return "fasta" in data || "rawSequence" in data ? record.fasta : "";
  if (format === "csv") return toCsv(data);
  return toText(data);
}

function toCsv(data: Record<string, unknown>) {
  const rows = ["section,field,value"];
  Object.entries(data).forEach(([section, value]) => {
    if (typeof value === "object" && value && !Array.isArray(value)) {
      Object.entries(value as Record<string, unknown>).forEach(([field, fieldValue]) => {
        rows.push([section, field, JSON.stringify(fieldValue ?? "")].map(csvCell).join(","));
      });
    } else {
      rows.push([section, "value", JSON.stringify(value ?? "")].map(csvCell).join(","));
    }
  });
  return rows.join("\n");
}

function csvCell(value: string) {
  return `"${value.replace(/"/g, '""')}"`;
}

function toText(data: Record<string, unknown>) {
  return Object.entries(data)
    .map(
      ([section, value]) =>
        `${section.toUpperCase()}\n${typeof value === "string" ? value : JSON.stringify(value, null, 2)}`,
    )
    .join("\n\n");
}

function buildFilename(record: RecordDetail, format: string) {
  const organism = record.organism.scientificName || record.organism.organismName || "NCBI";
  const gene = record.overview.geneName || "record";
  return `${safeName(organism)}_${safeName(gene)}_${safeName(record.overview.accession)}.${format}`;
}

function safeName(value: string) {
  return value.replace(/[^A-Za-z0-9.]+/g, "_").replace(/^_+|_+$/g, "") || "record";
}

function isDnaRecord(moleculeType: string) {
  const molecule = moleculeType.toLowerCase();
  return molecule.includes("dna") && !molecule.includes("rna") && !molecule.includes("protein");
}
