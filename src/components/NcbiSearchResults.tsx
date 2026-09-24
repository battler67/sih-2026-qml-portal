import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { motion, type Variants } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Database,
  Dna,
  Eye,
  ExternalLink,
  FlaskConical,
  ImageIcon,
  Loader2,
  Network,
  Search,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { BackgroundFX } from "@/components/BackgroundFX";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

type SourceFilter = "all" | "refseq" | "genbank";

type NcbiSearchRecord = {
  organismName: string;
  scientificName: string;
  geneName: string;
  accession: string;
  recordTitle: string;
  sequenceLength: number;
  source: string;
  moleculeType: string;
  lastUpdated: string;
  taxId?: string;
};

type NcbiSearchResponse = {
  query: string;
  count: number;
  page: number;
  pageSize: number;
  records: NcbiSearchRecord[];
};

export function NcbiSearchResults() {
  const [gene, setGene] = useState("BRCA1");
  const [organism, setOrganism] = useState("Mus caroli");
  const [source, setSource] = useState<SourceFilter>("all");
  const [minLength, setMinLength] = useState("10000");
  const [maxLength, setMaxLength] = useState("250000");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<NcbiSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedTaxId, setSelectedTaxId] = useState("");
  const [selectedTreeAccession, setSelectedTreeAccession] = useState("");
  const [genomeViewer, setGenomeViewer] = useState<GenomeViewerContext | null>(null);
  const [genomeViewerLoading, setGenomeViewerLoading] = useState(false);
  const [genomeViewerError, setGenomeViewerError] = useState("");
  const [executedGene, setExecutedGene] = useState("");
  const [executedOrganism, setExecutedOrganism] = useState("");

  const totalPages = useMemo(() => {
    if (!data) return 1;
    return Math.max(1, Math.ceil(data.count / data.pageSize));
  }, [data]);

  const selectedRecord = useMemo(
    () => data?.records.find((record) => record.accession === selectedTreeAccession),
    [data, selectedTreeAccession],
  );

  const displayedGenomeViewer = useMemo(() => {
    if (!genomeViewer) return null;
    const demoImage = findDemoGenomeImage({
      gene: selectedRecord?.geneName || executedGene,
      organism: executedOrganism,
      scientificName: selectedRecord?.scientificName || genomeViewer.scientificName,
      taxId: selectedRecord?.taxId || genomeViewer.taxId,
      accession: selectedRecord?.accession,
    });
    return demoImage ? { ...genomeViewer, image: demoImage } : genomeViewer;
  }, [executedGene, executedOrganism, genomeViewer, selectedRecord]);

  async function runSearch(nextPage = 1) {
    if (!gene.trim()) {
      setError("Enter a gene name before searching.");
      return;
    }
    setLoading(true);
    setError("");
    setPage(nextPage);
    try {
      const params = new URLSearchParams({
        gene: gene.trim(),
        source,
        page: String(nextPage),
        page_size: "10",
      });
      if (organism.trim()) params.set("organism", organism.trim());
      if (minLength.trim()) params.set("min_length", minLength.trim());
      if (maxLength.trim()) params.set("max_length", maxLength.trim());
      const response = await fetch(`${API_BASE}/api/ncbi/entrez/search?${params.toString()}`);
      const body = await response.json().catch(() => ({ detail: response.statusText }));
      if (!response.ok) throw new Error(String(body.detail || response.statusText));
      const nextData = body as NcbiSearchResponse;
      setData(nextData);
      setExecutedGene(gene.trim());
      setExecutedOrganism(organism.trim());
      const firstTreeRecord = nextData.records.find((record) => record.taxId);
      setSelectedTaxId(firstTreeRecord?.taxId || "");
      setSelectedTreeAccession(firstTreeRecord?.accession || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "NCBI search failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!selectedTaxId) {
      setGenomeViewer(null);
      setGenomeViewerError("");
      return;
    }
    let ignore = false;
    async function loadGenomeViewer() {
      setGenomeViewerLoading(true);
      setGenomeViewerError("");
      try {
        const body = await fetchGenomeViewerContext(API_BASE, selectedTaxId);
        if (!ignore) setGenomeViewer(body);
      } catch (err) {
        if (!ignore) setGenomeViewerError(err instanceof Error ? err.message : "Could not load genome viewer context");
      } finally {
        if (!ignore) setGenomeViewerLoading(false);
      }
    }
    loadGenomeViewer();
    return () => {
      ignore = true;
    };
  }, [selectedTaxId]);

  return (
    <div className="relative min-h-screen">
      <BackgroundFX />
      <header className="sticky top-0 z-30 border-b border-white/5 bg-background/60 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-6 py-4">
          <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" /> Home
          </Link>
          <div className="flex items-center gap-2">
            <div className="relative h-8 w-8 rounded-lg bg-gradient-to-br from-emerald to-cyan-glow glow-emerald">
              <Dna className="absolute inset-0 m-auto h-4 w-4 text-background" />
            </div>
            <span className="font-display text-lg font-semibold">QDNA NCBI Search</span>
          </div>
          <Link to="/quantum-search" className="text-sm text-muted-foreground hover:text-foreground">
            Quantum Search
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-[1400px] space-y-6 p-6 lg:p-8">
        <motion.div variants={fadeUp} initial="hidden" animate="show" className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-widest text-emerald">NCBI Entrez workflow</div>
            <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight">Gene nucleotide search results</h1>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Search NCBI nucleotide records through the backend and open selected records or sequence analysis in a new tab.
            </p>
          </div>
          <Button onClick={() => runSearch(1)} disabled={loading} className="rounded-full bg-emerald text-primary-foreground glow-emerald">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />} Search
          </Button>
        </motion.div>

        <Panel title="Search and Filters" eyebrow="Input" icon={Database}>
          <div className="grid gap-3 md:grid-cols-[1.2fr_1fr_0.8fr_0.7fr_0.7fr]">
            <Input value={gene} onChange={(event) => setGene(event.target.value)} placeholder="Gene name, e.g. BRCA1" className="border-white/10 bg-black/30" />
            <Input value={organism} onChange={(event) => setOrganism(event.target.value)} placeholder="Organism filter" className="border-white/10 bg-black/30" />
            <select value={source} onChange={(event) => setSource(event.target.value as SourceFilter)} className="theme-select rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm">
              <option value="all">RefSeq + GenBank</option>
              <option value="refseq">RefSeq only</option>
              <option value="genbank">GenBank only</option>
            </select>
            <Input type="number" min={1} value={minLength} onChange={(event) => setMinLength(event.target.value)} placeholder="Min length" className="border-white/10 bg-black/30" />
            <Input type="number" min={1} value={maxLength} onChange={(event) => setMaxLength(event.target.value)} placeholder="Max length" className="border-white/10 bg-black/30" />
          </div>
        </Panel>

        <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
          <Panel title="Results" eyebrow={data ? `${data.count.toLocaleString()} records found` : "Search-result count"} icon={BarChart3}>
            {error && (
              <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300">
                {error}
              </div>
            )}
            {loading && (
              <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-sm text-muted-foreground">
                <Loader2 className="mr-2 inline h-4 w-4 animate-spin text-emerald" /> Loading NCBI search results
              </div>
            )}
            {!loading && data && data.records.length === 0 && (
              <div className="rounded-xl border border-dashed border-white/10 bg-white/5 p-6 text-center text-sm text-muted-foreground">
                No nucleotide records matched the current search and filters.
              </div>
            )}
            {!loading && !data && !error && (
              <div className="rounded-xl border border-dashed border-white/10 bg-white/5 p-6 text-center text-sm text-muted-foreground">
                Search for a gene to load organism and nucleotide record summaries.
              </div>
            )}
            {!loading && data && data.records.length > 0 && (
              <div className="space-y-3">
                {data.records.map((record) => (
                  <ResultCard
                    key={record.accession}
                    record={record}
                    selectedTreeAccession={selectedTreeAccession}
                    onPreviewTree={(taxId, accession) => {
                      setSelectedTaxId(taxId);
                      setSelectedTreeAccession(accession);
                    }}
                  />
                ))}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-3 text-sm">
                  <div className="text-muted-foreground">
                    Page {page} of {totalPages}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" disabled={loading || page <= 1} onClick={() => runSearch(page - 1)} className="rounded-full border-white/10 bg-white/5">
                      Previous
                    </Button>
                    <Button variant="outline" disabled={loading || page >= totalPages} onClick={() => runSearch(page + 1)} className="rounded-full border-white/10 bg-white/5">
                      Next
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </Panel>

          <Panel title="Genome Data Viewer" eyebrow="Taxonomy tree" icon={Network}>
            <GenomeViewerPanel context={displayedGenomeViewer} loading={genomeViewerLoading} error={genomeViewerError} />
          </Panel>
        </div>

        <div className="glass rounded-2xl p-4 text-sm text-muted-foreground">
          <div className="flex gap-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-yellow-400" />
            <span>Search summaries are fetched with ESearch and ESummary. Complete sequences are fetched only when opening record details or analysis.</span>
          </div>
        </div>
      </main>
    </div>
  );
}

function ResultCard({
  record,
  selectedTreeAccession,
  onPreviewTree,
}: {
  record: NcbiSearchRecord;
  selectedTreeAccession: string;
  onPreviewTree: (taxId: string, accession: string) => void;
}) {
  const recordHref = `/ncbi/record/${encodeURIComponent(record.accession)}`;
  const analysisHref = `/quantum-search?analysisAccession=${encodeURIComponent(record.accession)}`;
  const analysisReady = isGenomicDnaRecord(record.moleculeType, record.recordTitle);
  const treeSelected = record.accession === selectedTreeAccession;
  return (
    <article className="rounded-xl border border-white/10 bg-white/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full border border-emerald/30 bg-emerald/10 px-2 py-0.5 text-emerald">{record.source}</span>
            <span className="font-mono text-muted-foreground">{record.accession}</span>
            <span className="text-muted-foreground">{record.lastUpdated || "No update date"}</span>
          </div>
          <h2 className="mt-2 line-clamp-2 font-display text-lg font-semibold">{record.recordTitle}</h2>
          <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Organism" value={record.organismName} />
            <Metric label="Scientific name" value={record.scientificName} />
            <Metric label="Gene" value={record.geneName || "Not specified"} />
            <Metric label="Length" value={`${record.sequenceLength.toLocaleString()} bp`} />
            <Metric label="Molecule" value={record.moleculeType || "nucleotide"} />
          </div>
        </div>
        <div className="grid w-full shrink-0 gap-2 sm:w-48">
          {record.taxId ? (
            <button
              type="button"
              onClick={() => onPreviewTree(record.taxId || "", record.accession)}
              className={`inline-flex w-full items-center justify-center gap-2 rounded-full border px-4 py-2 text-sm ${
                treeSelected
                  ? "border-emerald/40 bg-emerald/15 text-emerald"
                  : "border-white/10 bg-white/5 hover:bg-white/10"
              }`}
            >
              <Network className="h-4 w-4" /> Preview Tree
            </button>
          ) : null}
          <a href={recordHref} target="_blank" rel="noreferrer" className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm hover:bg-white/10">
            <Eye className="h-4 w-4" /> View Record
          </a>
          {record.taxId ? (
            <Link to="/ncbi/organism/$taxId" params={{ taxId: record.taxId }} className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm hover:bg-white/10">
              View Organism
            </Link>
          ) : null}
          {analysisReady ? (
            <a href={analysisHref} target="_blank" rel="noreferrer" className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-emerald px-4 py-2 text-sm font-semibold text-primary-foreground glow-emerald">
              <FlaskConical className="h-4 w-4" /> Sequence Analysis
            </a>
          ) : (
            <span className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-yellow-400/20 bg-yellow-400/10 px-4 py-2 text-sm text-yellow-100">
              <AlertTriangle className="h-4 w-4" /> Genomic DNA required
            </span>
          )}
        </div>
      </div>
    </article>
  );
}

function GenomeViewerPanel({
  context,
  loading,
  error,
}: {
  context: GenomeViewerContext | null;
  loading: boolean;
  error: string;
}) {
  if (loading) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-muted-foreground">
        <Loader2 className="mr-2 inline h-4 w-4 animate-spin text-emerald" /> Loading taxonomy tree
      </div>
    );
  }
  if (error) {
    return <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300">{error}</div>;
  }
  if (!context) {
    return <p className="text-sm text-muted-foreground">Select a result with a taxonomy ID to preview its tree.</p>;
  }
  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-xl border border-white/10 bg-black/20">
        {context.image ? (
          <>
            <img
              src={context.image.url}
              alt={context.image.title || context.scientificName}
              className={`h-44 w-full ${context.image.source === "Local demo image" ? "bg-white object-contain" : "object-cover"}`}
              referrerPolicy="no-referrer"
            />
            {(context.image.title || context.image.description) && (
              <div className="border-t border-white/10 p-3">
                <div className="text-sm font-semibold">{context.image.title || context.scientificName}</div>
                <div className="mt-1 text-xs text-muted-foreground">{context.image.description || context.image.source}</div>
              </div>
            )}
          </>
        ) : (
          <div className="flex h-44 flex-col items-center justify-center gap-2 p-4 text-center text-sm text-muted-foreground">
            <ImageIcon className="h-6 w-6 text-emerald" />
            No free organism image found
          </div>
        )}
      </div>

      <TaxonomyTree nodes={context.treeNodes} />

      <div className="flex flex-wrap gap-2">
        <Link to="/ncbi/organism/$taxId" params={{ taxId: context.taxId }} className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs hover:bg-white/10">
          View Details
        </Link>
        <a href={context.links.genomeDataViewer} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs hover:bg-white/10">
          NCBI GDV <ExternalLink className="h-3.5 w-3.5" />
        </a>
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
      <div className="mb-3 text-xs uppercase tracking-widest text-emerald">Phylogenetic placement</div>
      <div>
        {visibleNodes.map((node, index) => (
          <div key={`${node.taxId}-${index}`} className="relative flex gap-3">
            <div className="flex w-8 shrink-0 flex-col items-center">
              <span className={`h-4 w-4 rounded-full border ${node.isSelected ? "border-emerald bg-emerald glow-emerald" : "border-emerald/60 bg-background"}`} />
              {index < visibleNodes.length - 1 ? <span className="h-8 w-px bg-emerald/40" /> : null}
            </div>
            <div className={`mb-2 min-w-0 flex-1 rounded-lg border p-2.5 ${node.isSelected ? "border-emerald/50 bg-emerald/10" : "border-white/10 bg-black/20"}`}>
              <div className="break-words text-sm font-semibold">{node.scientificName}</div>
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="truncate text-sm text-foreground">{value}</div>
    </div>
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
    <motion.section variants={fadeUp} initial="hidden" animate="show" className="glass min-w-0 overflow-hidden rounded-2xl p-5">
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

function isGenomicDnaRecord(moleculeType: string, title: string) {
  const text = `${moleculeType} ${title}`.toLowerCase();
  return /\bdna\b/.test(text) && !/(^|\W)(m?rna|transcript|protein)(\W|$)/.test(text);
}
