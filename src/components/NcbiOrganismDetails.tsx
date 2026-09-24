import { useEffect, useState, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { motion, type Variants } from "framer-motion";
import { ArrowLeft, Database, Dna, ExternalLink, Loader2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { BackgroundFX } from "@/components/BackgroundFX";

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

type OrganismDetails = {
  taxId: string;
  scientificName: string;
  commonName: string;
  rank: string;
  division: string;
  lineage: string;
  lineageTaxa: Array<{ taxId: string; scientificName: string; rank: string }>;
  geneticCode: { id: string; name: string };
  mitochondrialGeneticCode: { id: string; name: string };
  ncbiUrl: string;
};

export function NcbiOrganismDetails({ taxId }: { taxId: string }) {
  const [organism, setOrganism] = useState<OrganismDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let ignore = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const response = await fetch(`${API_BASE}/api/ncbi/organisms/${encodeURIComponent(taxId)}`);
        const body = await response.json().catch(() => ({ detail: response.statusText }));
        if (!response.ok) throw new Error(String(body.detail || response.statusText));
        if (!ignore) setOrganism(body as OrganismDetails);
      } catch (err) {
        if (!ignore) setError(err instanceof Error ? err.message : "Could not load organism details");
      } finally {
        if (!ignore) setLoading(false);
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, [taxId]);

  return (
    <div className="relative min-h-screen">
      <BackgroundFX />
      <header className="sticky top-0 z-30 border-b border-white/5 bg-background/60 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-6 py-4">
          <Link to="/quantum-search" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" /> Quantum Search
          </Link>
          <div className="flex items-center gap-2">
            <div className="relative h-8 w-8 rounded-lg bg-gradient-to-br from-emerald to-cyan-glow glow-emerald">
              <Dna className="absolute inset-0 m-auto h-4 w-4 text-background" />
            </div>
            <span className="font-display text-lg font-semibold">NCBI Organism Details</span>
          </div>
          <a href={`https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=${encodeURIComponent(taxId)}`} target="_blank" rel="noreferrer" className="text-sm text-muted-foreground hover:text-foreground">
            NCBI
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-[1400px] space-y-6 p-6 lg:p-8">
        <Panel title="Organism Overview" eyebrow={`Taxonomy ID ${taxId}`} icon={Database}>
          {loading && (
            <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-sm text-muted-foreground">
              <Loader2 className="mr-2 inline h-4 w-4 animate-spin text-emerald" /> Loading organism details
            </div>
          )}
          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300">
              {error}
            </div>
          )}
          {organism && (
            <div className="space-y-5">
              <div>
                <h1 className="font-display text-3xl font-semibold">{organism.scientificName || "Unknown organism"}</h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  {organism.commonName || "No common name returned"} - {organism.rank || "rank unavailable"} - {organism.division || "division unavailable"}
                </p>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <Metric label="Taxonomy ID" value={organism.taxId} />
                <Metric label="Genetic code" value={organism.geneticCode.name || organism.geneticCode.id || "Not available"} />
                <Metric label="Mito genetic code" value={organism.mitochondrialGeneticCode.name || organism.mitochondrialGeneticCode.id || "Not available"} />
              </div>
              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="text-xs uppercase tracking-widest text-emerald">Lineage</div>
                <p className="mt-2 text-sm text-muted-foreground">{organism.lineage || "No lineage returned."}</p>
              </div>
              {organism.lineageTaxa.length > 0 && (
                <div className="overflow-x-auto rounded-xl border border-white/10">
                  <table className="w-full min-w-[700px] text-left text-sm">
                    <thead className="bg-white/5 text-xs uppercase tracking-wider text-muted-foreground">
                      <tr>
                        <th className="px-3 py-3">Rank</th>
                        <th className="px-3 py-3">Scientific name</th>
                        <th className="px-3 py-3">Taxonomy ID</th>
                      </tr>
                    </thead>
                    <tbody>
                      {organism.lineageTaxa.map((item) => (
                        <tr key={`${item.rank}-${item.taxId}`} className="border-t border-white/5">
                          <td className="px-3 py-3">{item.rank || "No rank"}</td>
                          <td className="px-3 py-3">{item.scientificName}</td>
                          <td className="px-3 py-3 font-mono text-emerald">{item.taxId}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <a href={organism.ncbiUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-full bg-emerald px-4 py-2 text-sm font-semibold text-primary-foreground glow-emerald">
                <ExternalLink className="h-4 w-4" /> View on NCBI
              </a>
            </div>
          )}
        </Panel>
      </main>
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
    <motion.section variants={fadeUp} initial="hidden" animate="show" className="glass rounded-2xl p-5">
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm text-foreground">{value}</div>
    </div>
  );
}
