import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { AlertTriangle, ArrowLeft, CheckCircle2, Cpu, Dna, Loader2, Server } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BackgroundFX } from "@/components/BackgroundFX";
import { LoadingInsight } from "@/components/LoadingInsight";

const API_BASE = import.meta.env.VITE_QUANTUM_API_BASE_URL || "http://127.0.0.1:8000";

type DeviceDetails = {
  provider: string;
  deviceId: string;
  name: string;
  qubits: number;
  queueDepth: number;
  status: string;
  deviceType: string;
  free: boolean;
  requiredQubits?: number;
  unusedQubits?: number;
};

type HardwareJobStatus = {
  jobId: string;
  status: string;
  progressPercent: number;
  message: string;
  remoteJobId?: string | null;
  selectedDevice?: DeviceDetails | null;
  providerErrors?: string[];
  error?: string | null;
};

type HardwareResult = {
  jobId: string;
  remoteJobId: string;
  status: string;
  algorithm: string;
  provider: string;
  providerErrors: string[];
  device: DeviceDetails;
  selection: {
    policy: string;
    eligibleDeviceCount: number;
    reason: string;
  };
  query: { sequence: string; length: number };
  representativeWindow: {
    accession: string;
    recordTitle: string;
    organism?: string | null;
    strand: string;
    start: number;
    end: number;
    sequence: string;
    selectionMethod: string;
  };
  retrieval: {
    provider: string;
    recordCount: number;
    totalBases: number;
  };
  execution: {
    requestedShots: number;
    submittedShots: number;
    returnedShots: number;
    counts: Record<string, number>;
    probabilities: Record<string, number>;
    providerStatus: string;
    rawHardwareMeasurements: true;
    errorMitigationApplied: false;
  };
  circuit: {
    logicalQubits: number;
    classicalBits: number;
    depth: number;
    size: number;
    operationCounts: Record<string, number>;
    transpiled?: {
      qubits: number;
      depth: number;
      size: number;
      operationCounts: Record<string, number>;
    } | null;
  };
  limitations: string[];
  warnings: string[];
};

function formatApiError(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

function Panel({
  title,
  eyebrow,
  children,
}: {
  title: string;
  eyebrow: string;
  children: ReactNode;
}) {
  return (
    <section className="glass rounded-2xl border border-white/5 p-5">
      <div className="mb-4">
        <div className="text-[11px] uppercase tracking-[0.22em] text-emerald">{eyebrow}</div>
        <h2 className="mt-1 font-display text-xl font-semibold">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className="mt-1 break-all font-mono text-sm text-foreground">{value}</div>
    </div>
  );
}

export function QuantumHardwareResultsPage({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<HardwareJobStatus | null>(null);
  const [result, setResult] = useState<HardwareResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!jobId) {
      setError("No hardware job was provided. Start from the quantum-search page.");
      return;
    }
    let ignore = false;

    async function poll() {
      while (!ignore) {
        let response: Response;
        try {
          response = await fetch(`${API_BASE}/api/quantum-search/hardware/jobs/${jobId}`);
        } catch {
          throw new Error(`Cannot reach the quantum search API at ${API_BASE}.`);
        }
        const body = await response.json().catch(() => ({ detail: response.statusText }));
        if (!response.ok) {
          throw new Error(formatApiError(body, "Could not load the hardware job"));
        }
        if (ignore) return;
        const snapshot = body as HardwareJobStatus;
        setJob(snapshot);
        if (snapshot.status === "completed") {
          const resultResponse = await fetch(
            `${API_BASE}/api/quantum-search/hardware/jobs/${jobId}/results`,
          );
          const resultBody = await resultResponse
            .json()
            .catch(() => ({ detail: resultResponse.statusText }));
          if (!resultResponse.ok) {
            throw new Error(formatApiError(resultBody, "Could not load hardware results"));
          }
          if (!ignore) setResult(resultBody as HardwareResult);
          return;
        }
        if (snapshot.status === "failed") {
          throw new Error(snapshot.error || "Real-hardware execution failed");
        }
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }
    }

    poll().catch((err) => {
      if (!ignore) {
        setError(err instanceof Error ? err.message : "Real-hardware execution failed");
      }
    });
    return () => {
      ignore = true;
    };
  }, [jobId]);

  const chartData = useMemo(
    () =>
      Object.entries(result?.execution.counts ?? {}).map(([state, count]) => ({
        state,
        count,
      })),
    [result],
  );

  const scientificBoundaryMessages = useMemo(() => {
    if (!result) return [];
    const messages = [...result.limitations, ...result.warnings];
    return [
      messages.find((message) => message.includes("entire-genome coherent search")),
      messages.find((message) => message.includes("raw physical-device measurements")),
    ].filter((message): message is string => Boolean(message));
  }, [result]);

  return (
    <div className="relative min-h-screen">
      <BackgroundFX />
      {jobId && !result && !error && (
        <LoadingInsight title={job?.message || "Preparing real-hardware execution"} />
      )}
      <header className="sticky top-0 z-50 border-b border-white/5 bg-background/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-6 py-4">
          <Link
            to="/quantum-search"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" /> Search
          </Link>
          <div className="flex items-center gap-2">
            <div className="relative h-8 w-8 rounded-lg bg-gradient-to-br from-cyan-glow to-emerald">
              <Cpu className="absolute inset-0 m-auto h-4 w-4 text-background" />
            </div>
            <span className="font-display text-lg font-semibold">Real Hardware Results</span>
          </div>
          <Link to="/dashboard" className="text-sm text-muted-foreground hover:text-foreground">
            Dashboard
          </Link>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1400px] gap-6 px-6 py-8">
        <Panel title="Hardware execution" eyebrow="Raw physical-device run">
          {error && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
              <div className="flex items-center gap-2 font-medium">
                <AlertTriangle className="h-4 w-4" />
                Hardware calls failed
              </div>
              <p className="mt-2">{error}</p>
              {!!job?.providerErrors?.length && (
                <ul className="mt-3 space-y-2 text-xs text-red-200/90">
                  {job.providerErrors.map((providerError) => (
                    <li
                      key={providerError}
                      className="rounded-lg border border-red-500/20 bg-black/20 px-3 py-2"
                    >
                      {providerError}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {!error && !result && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 rounded-xl border border-cyan-glow/20 bg-cyan-glow/10 p-4">
                <Loader2 className="h-5 w-5 animate-spin text-cyan-glow" />
                <div>
                  <div className="font-medium">{job?.message || "Loading hardware job"}</div>
                  <div className="text-xs text-muted-foreground">
                    Provider queues can take longer than local Aer execution. Keep this page open,
                    or retain the provider job ID once it appears.
                  </div>
                </div>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-black/40">
                <div
                  className="h-full rounded-full bg-cyan-glow transition-all duration-500"
                  style={{ width: `${job?.progressPercent ?? 0}%` }}
                />
              </div>
              {job?.selectedDevice && (
                <div className="grid gap-3 sm:grid-cols-4">
                  <Metric label="Provider" value={job.selectedDevice.provider} />
                  <Metric label="Device" value={job.selectedDevice.name} />
                  <Metric label="Qubits" value={job.selectedDevice.qubits} />
                  <Metric label="Queue snapshot" value={job.selectedDevice.queueDepth} />
                </div>
              )}
            </div>
          )}
          {result && (
            <div className="space-y-5">
              <div className="flex items-start gap-3 rounded-xl border border-emerald/20 bg-emerald/10 p-4">
                <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald" />
                <div>
                  <div className="font-medium">Hardware job completed</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    Raw measurements returned with no error mitigation.
                  </div>
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
                <Metric label="Algorithm" value={result.algorithm} />
                <Metric label="Provider" value={result.provider} />
                <Metric label="Device" value={result.device.name} />
                <Metric label="Device qubits" value={result.device.qubits} />
                <Metric label="Required qubits" value={result.circuit.logicalQubits} />
                <Metric label="Returned shots" value={result.execution.returnedShots} />
              </div>
              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Server className="h-4 w-4 text-cyan-glow" /> Resource-aware mapping
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{result.selection.reason}</p>
                <div className="mt-3 grid gap-3 sm:grid-cols-4">
                  <Metric label="Queue snapshot" value={result.device.queueDepth} />
                  <Metric label="Unused qubits" value={result.device.unusedQubits ?? "-"} />
                  <Metric label="Eligible devices" value={result.selection.eligibleDeviceCount} />
                  <Metric label="Remote job ID" value={result.remoteJobId} />
                </div>
              </div>
            </div>
          )}
        </Panel>

        {result && (
          <>
            <div className="grid gap-6 lg:grid-cols-2">
              <Panel title="Representative genomic window" eyebrow="Bounded input">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Metric label="Query" value={result.query.sequence} />
                  <Metric label="Hardware window" value={result.representativeWindow.sequence} />
                  <Metric label="Accession" value={result.representativeWindow.accession} />
                  <Metric
                    label="Coordinates"
                    value={`${result.representativeWindow.start}-${result.representativeWindow.end}`}
                  />
                </div>
                <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
                  {result.representativeWindow.selectionMethod}
                </p>
              </Panel>

              <Panel title="Circuit metrics" eyebrow="Before and after mapping">
                <div className="grid gap-3 sm:grid-cols-3">
                  <Metric label="Logical depth" value={result.circuit.depth} />
                  <Metric label="Logical size" value={result.circuit.size} />
                  <Metric label="Classical bits" value={result.circuit.classicalBits} />
                  <Metric
                    label="ISA depth"
                    value={result.circuit.transpiled?.depth ?? "Provider"}
                  />
                  <Metric label="ISA size" value={result.circuit.transpiled?.size ?? "Provider"} />
                  <Metric
                    label="Mitigation"
                    value={result.execution.errorMitigationApplied ? "Enabled" : "None"}
                  />
                </div>
              </Panel>
            </div>

            <Panel title="Measurement counts" eyebrow="Raw hardware distribution">
              {chartData.length ? (
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                      <XAxis dataKey="state" stroke="rgba(255,255,255,0.45)" />
                      <YAxis stroke="rgba(255,255,255,0.45)" />
                      <Tooltip
                        contentStyle={{
                          background: "hsl(var(--background))",
                          border: "1px solid rgba(255,255,255,0.12)",
                          borderRadius: 12,
                        }}
                      />
                      <Bar dataKey="count" fill="var(--color-cyan-glow)" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">No measurement counts returned.</div>
              )}
              <pre className="mt-4 overflow-x-auto rounded-xl bg-black/30 p-4 text-xs text-cyan-glow">
                {JSON.stringify(result.execution.counts, null, 2)}
              </pre>
            </Panel>

            <Panel title="Limitations and warnings" eyebrow="Scientific boundaries">
              <div className="grid gap-3 lg:grid-cols-2">
                {scientificBoundaryMessages.map((message, index) => (
                  <div
                    key={`${index}-${message}`}
                    className="flex gap-3 rounded-xl border border-yellow-400/20 bg-yellow-400/5 p-3 text-xs text-muted-foreground"
                  >
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-yellow-400" />
                    <span>{message}</span>
                  </div>
                ))}
              </div>
            </Panel>
          </>
        )}
      </main>
    </div>
  );
}
