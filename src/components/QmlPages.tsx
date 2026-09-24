import { lazy, Suspense, useEffect, useMemo, useState, type ReactNode } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  Atom,
  BarChart3,
  CheckCircle2,
  CircleAlert,
  Download,
  FileText,
  FlaskConical,
  HeartPulse,
  Loader2,
  Microscope,
  Upload,
} from "lucide-react";
import { BackgroundFX } from "@/components/BackgroundFX";
import {
  qmlApi,
  parseQmlCsv,
  waitForHardwareResult,
  type HardwareCapabilities,
  type HardwareProvider,
  type QmlPrediction,
  type QmlEvidence as QmlEvidenceData,
  type QmlEvidenceMetric,
  type QmlModel,
  type QmlModelEvidence,
  type QmlReport,
  type QmlSchema,
} from "@/lib/qml-api";
import { useQmlSession } from "@/lib/qml-context";
import { ModelRegistry } from "@/components/ModelRegistry";

const QmlEvidenceChart = lazy(() => import("@/components/QmlEvidenceChart"));

const NOTICE =
  "Research-use prototype. Outputs are educational model scores, not a diagnosis or treatment recommendation.";
export const panel =
  "rounded-2xl border border-white/10 bg-card/70 p-5 shadow-xl shadow-black/10 backdrop-blur-sm";
export const button =
  "inline-flex items-center justify-center gap-2 rounded-full bg-emerald px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald disabled:cursor-not-allowed disabled:opacity-50";
export const subtleButton =
  "inline-flex items-center justify-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-foreground transition hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald";

export function Shell({
  title,
  eyebrow,
  children,
}: {
  title: string;
  eyebrow: string;
  children: ReactNode;
}) {
  return (
    <div className="relative min-h-screen overflow-hidden">
      <BackgroundFX />
      <div className="relative z-10 mx-auto max-w-7xl px-4 pb-16 sm:px-6">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 py-5">
          <Link to="/" className="flex items-center gap-2 font-display text-lg font-semibold">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald to-cyan-glow text-background">
              <Atom size={19} />
            </span>{" "}
            QDNA <span className="text-sm font-normal text-muted-foreground">/ Early-Risk Lab</span>
          </Link>
          <nav aria-label="QML navigation" className="flex flex-wrap items-center gap-2 text-sm">
            <Link to="/qml" className={subtleButton}>
              Overview
            </Link>
            <Link to="/qml/analyze" className={subtleButton}>
              EHR
            </Link>
            <Link to="/qml/genomics/fh" className={subtleButton}>
              FH genomics
            </Link>
            <Link to="/qml/imaging" className={subtleButton}>
              QCNN Imaging
            </Link>
            <Link to="/qml/evidence" className={subtleButton}>
              Model catalogue
            </Link>
            <Link to="/quantum-search" className={subtleButton}>
              Genomic Lab
            </Link>
          </nav>
        </header>
        <main id="main-content" className="py-9">
          <div className="mb-8">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald">
              {eyebrow}
            </p>
            <h1 className="mt-2 max-w-4xl font-display text-3xl font-semibold tracking-tight sm:text-5xl">
              {title}
            </h1>
          </div>
          {children}
        </main>
        <footer className="border-t border-white/10 py-5 text-xs text-muted-foreground">
          {NOTICE}
        </footer>
      </div>
    </div>
  );
}

export function Notice({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return (
    <div
      role={error ? "alert" : "note"}
      className={`flex gap-3 rounded-xl border p-4 text-sm ${error ? "border-red-400/30 bg-red-400/10 text-red-100" : "border-emerald/25 bg-emerald/10 text-muted-foreground"}`}
    >
      <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
      {children}
    </div>
  );
}

type EvidenceTier = "Best observed" | "Moderate" | "Experimental";

const tierClass: Record<EvidenceTier, string> = {
  "Best observed": "border-emerald/35 bg-emerald/15 text-emerald",
  Moderate: "border-amber-300/30 bg-amber-300/10 text-amber-200",
  Experimental: "border-fuchsia-300/30 bg-fuchsia-300/10 text-fuchsia-200",
};

function TierBadge({ tier }: { tier: EvidenceTier }) {
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs ${tierClass[tier]}`}>
      {tier}
    </span>
  );
}

function observedTier(metric: QmlEvidenceMetric, bestAuprc: number): EvidenceTier {
  if (typeof metric.auprc !== "number" || !Number.isFinite(bestAuprc)) return "Experimental";
  const gap = bestAuprc - metric.auprc;
  if (gap <= 1e-12) return "Best observed";
  if (gap <= 0.1) return "Moderate";
  return "Experimental";
}

function runnableTier(model: QmlModel): EvidenceTier {
  if (["framingham-logistic-pca2", "uci-rbf-svm"].includes(model.id)) {
    return "Best observed";
  }
  if (model.id === "framingham-angle-qksvm-pca2") return "Moderate";
  return "Experimental";
}

const runnableFramingham = new Set(["angle_qksvm_pca2", "logistic_pca2"]);
const runnableQcnnRun = "e77cc845e586cfdd";

function useModels() {
  const [models, setModels] = useState<QmlModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    qmlApi
      .models()
      .then((result) => {
        if (active) setModels(result.models);
      })
      .catch((reason) => {
        if (active) setError(reason.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  return { models, loading, error };
}

export function QmlLanding() {
  return (
    <Shell
      eyebrow="Multimodal Early-Risk Research Lab"
      title="Choose the biomedical evidence you want to explore."
    >
      <div className="grid gap-5 lg:grid-cols-3">
        <Link to="/qml/analyze" className={`${panel} group block transition hover:-translate-y-1 hover:border-emerald/35`}>
          <HeartPulse className="text-emerald" size={28} />
          <p className="mt-5 text-xs font-semibold uppercase tracking-[0.18em] text-emerald">EHR</p>
          <h2 className="mt-2 font-display text-2xl font-semibold">Clinical records</h2>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">Run verified Framingham and Cleveland models, then compare every completed EHR experiment.</p>
          <span className="mt-5 inline-flex items-center gap-2 text-sm text-emerald">Enter EHR workflow <ArrowRight size={15} className="transition group-hover:translate-x-1" /></span>
        </Link>
        <Link to="/qml/genomics/fh" className={`${panel} group block border-emerald/25 bg-emerald/[0.07] transition hover:-translate-y-1 hover:border-emerald/50`}>
          <Microscope className="text-cyan-glow" size={28} />
          <p className="mt-5 text-xs font-semibold uppercase tracking-[0.18em] text-cyan-glow">Genomics · first pathway</p>
          <h2 className="mt-2 font-display text-2xl font-semibold">Familial hypercholesterolemia</h2>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">Follow synthetic variant evidence, phenotype and family history through transparent referral rules and matched models.</p>
          <span className="mt-5 inline-flex items-center gap-2 text-sm text-cyan-glow">Open FH pathway <ArrowRight size={15} className="transition group-hover:translate-x-1" /></span>
        </Link>
        <Link to="/qml/imaging" className={`${panel} group block transition hover:-translate-y-1 hover:border-emerald/35`}>
          <Activity className="text-emerald" size={28} />
          <p className="mt-5 text-xs font-semibold uppercase tracking-[0.18em] text-emerald">Medical imaging</p>
          <h2 className="mt-2 font-display text-2xl font-semibold">Breast imaging models</h2>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">Run the saved BreastMNIST QCNN on a synthetic demo image, then compare its evidence with experimental imaging models.</p>
          <span className="mt-5 inline-flex items-center gap-2 text-sm text-emerald">Enter QCNN imaging workflow <ArrowRight size={15} className="transition group-hover:translate-x-1" /></span>
        </Link>
      </div>

      <div className="mt-6"><Notice>All routes are research-only. “Best” means the highest observed primary metric inside one saved dataset and endpoint—not clinical approval or superiority.</Notice></div>

      <section id="model-registry" className="mt-10 scroll-mt-6">
        <div className="mb-4 flex items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald">Complete inventory</p>
            <h2 className="mt-2 font-display text-2xl font-semibold">All completed models</h2>
          </div>
          <Link to="/qml/evidence" className={subtleButton}>Evidence charts <BarChart3 size={15} /></Link>
        </div>
        <ModelRegistry compact />
      </section>
      <div className="mt-8">
        <Notice>
          No experiment was removed. Open Model catalogue to see every audited Framingham,
          Cleveland, BreastMNIST and WDBC result. Cards marked Runnable have complete serving
          bundles; evidence-only models stay visible without a misleading Run control.
        </Notice>
      </div>
    </Shell>
  );
}

export function QmlAnalyze({ initialModelId = "" }: { initialModelId?: string }) {
  const navigate = useNavigate();
  const { setCurrent } = useQmlSession();
  const { models, loading, error: modelsError } = useModels();
  const [workflow, setWorkflow] = useState<"framingham" | "uci">(
    initialModelId.startsWith("uci-") ? "uci" : "framingham",
  );
  const [modelId, setModelId] = useState("");
  const [schema, setSchema] = useState<QmlSchema | null>(null);
  const [values, setValues] = useState<Record<string, number | null>>({});
  const [source, setSource] = useState<"manual" | "synthetic demo" | "uploaded CSV">("manual");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [executionBackend, setExecutionBackend] = useState<"simulator" | HardwareProvider>(
    "simulator",
  );
  const [shots, setShots] = useState(128);
  const [hardwareStatus, setHardwareStatus] = useState("");
  const [capabilities, setCapabilities] = useState<HardwareCapabilities | null>(null);
  const available = useMemo(
    () => models.filter((model) => model.workflow === workflow && model.availability === "runnable"),
    [models, workflow],
  );
  useEffect(() => {
    qmlApi
      .hardwareCapabilities()
      .then(setCapabilities)
      .catch(() => setCapabilities(null));
  }, []);
  useEffect(() => {
    const next =
      available.find((model) => model.id === initialModelId) ||
      available.find((model) => model.recommended) ||
      available[0];
    if (next) setModelId(next.id);
  }, [available, initialModelId]);
  useEffect(() => {
    if (!modelId) return;
    let active = true;
    setSchema(null);
    setValues({});
    qmlApi
      .schema(modelId)
      .then((result) => {
        if (active) setSchema(result);
      })
      .catch((reason) => {
        if (active) setMessage(reason.message);
      });
    return () => {
      active = false;
    };
  }, [modelId]);
  useEffect(() => {
    const selected = models.find((model) => model.id === modelId);
    if (selected?.type === "classical") setExecutionBackend("simulator");
    if (modelId === "framingham-angle-qksvm-pca2" && executionBackend === "qbraid")
      setExecutionBackend("simulator");
  }, [modelId, models, executionBackend]);
  async function upload(file?: File) {
    if (!file) return;
    if (file.size > 16_384) {
      setMessage("CSV must be 16 KB or smaller.");
      return;
    }
    try {
      if (!schema) throw new Error("Wait for the model schema to load.");
      setValues(
        parseQmlCsv(
          await file.text(),
          schema.fields.map((field) => field.name),
        ),
      );
      setSource("uploaded CSV");
      setMessage("");
    } catch (reason) {
      setMessage((reason as Error).message);
    }
  }
  async function submit() {
    if (!schema) return;
    setMessage("");
    const missing = schema.fields.filter((field) => !(field.name in values));
    if (missing.length) {
      setMessage(
        `Enter or load all required fields: ${missing.map((field) => field.name).join(", ")}`,
      );
      return;
    }
    for (const field of schema.fields) {
      const value = values[field.name];
      if (value === null && field.nullable) continue;
      if (
        value === null ||
        !Number.isFinite(value) ||
        value < field.min ||
        value > field.max ||
        (field.allowedCodes && !Number.isInteger(value))
      ) {
        setMessage(
          `${field.label} must be between ${field.min} and ${field.max}${field.allowedCodes ? " and use an integer code" : ""}.`,
        );
        return;
      }
    }
    const request = { modelId, features: values };
    setBusy(true);
    try {
      let prediction: QmlPrediction;
      if (executionBackend === "simulator") {
        setHardwareStatus("");
        prediction = await qmlApi.predict(request);
      } else {
        const preview = await qmlApi.hardwarePreview(modelId, executionBackend);
        const device = (preview.selectedDevice as { name?: string })?.name || executionBackend;
        const circuitCount = Number(preview.circuitCount || 1);
        if (
          !window.confirm(
            `Submit ${circuitCount} circuit${circuitCount === 1 ? "" : "s"}, each with ${shots} shots, to real hardware on ${device}?`,
          )
        ) {
          setBusy(false);
          return;
        }
        const job = await qmlApi.submitHardware(request, executionBackend, shots);
        setHardwareStatus(job.message);
        prediction = await waitForHardwareResult<QmlPrediction>(job.jobId, (state) =>
          setHardwareStatus(state.message),
        );
      }
      setCurrent({ request, prediction });
      await navigate({ to: "/qml/results" });
    } catch (reason) {
      setMessage((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Shell
      eyebrow="Step 01 · Prepare input"
      title="Run a model with exactly the features it expects."
    >
      <div className="grid gap-6 lg:grid-cols-[1fr_1.7fr]">
        <aside className="space-y-5">
          <section className={panel}>
            <h2 className="font-display text-lg font-semibold">Choose a workflow</h2>
            <div className="mt-4 grid gap-2">
              {(["framingham", "uci"] as const).map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => {
                    setWorkflow(item);
                    setMessage("");
                  }}
                  className={`rounded-xl border p-4 text-left transition ${workflow === item ? "border-emerald/60 bg-emerald/10" : "border-white/10 hover:bg-white/5"}`}
                >
                  <span className="block font-medium">
                    {item === "framingham"
                      ? "Future CHD teaching benchmark"
                      : "Cleveland heart disease presence"}
                  </span>
                  <span className="mt-1 block text-xs text-muted-foreground">
                    {item === "framingham"
                      ? "15 baseline features · educational 10-year endpoint"
                      : "13 clinical features · diagnostic smoke run"}
                  </span>
                </button>
              ))}
            </div>
          </section>
          <section className={panel}>
            <label htmlFor="qml-model" className="block font-display text-lg font-semibold">
              Select model
            </label>
            <select
              id="qml-model"
              value={modelId}
              onChange={(event) => setModelId(event.target.value)}
              className="mt-3 w-full rounded-xl border border-white/15 bg-background p-3 text-sm"
              disabled={loading || busy}
            >
              {available.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                  {model.recommended ? " · recommended" : ""}
                </option>
              ))}
            </select>
            <p className="mt-3 text-xs text-muted-foreground">
              {available.find((model) => model.id === modelId)?.limitation}
            </p>
            <label className="mt-5 block text-sm font-medium" htmlFor="qml-execution-backend">
              Execution backend
            </label>
            <select
              id="qml-execution-backend"
              value={executionBackend}
              onChange={(event) =>
                setExecutionBackend(event.target.value as "simulator" | HardwareProvider)
              }
              disabled={
                busy || available.find((model) => model.id === modelId)?.type === "classical"
              }
              className="mt-2 w-full rounded-xl border border-white/15 bg-background p-3 text-sm"
            >
              <option value="simulator">Local ideal simulator (default)</option>
              <option
                value="ibm"
                disabled={capabilities ? !capabilities.providers.ibm.configured : false}
              >
                IBM Quantum hardware
              </option>
              <option value="qbraid" disabled>
                qBraid · unavailable for 256-circuit QKSVM
              </option>
            </select>
            {executionBackend !== "simulator" ? (
              <label className="mt-4 block text-sm">
                <span className="text-xs text-muted-foreground">Shots per circuit</span>
                <input
                  type="number"
                  min={32}
                  max={1024}
                  step={32}
                  value={shots}
                  onChange={(event) => setShots(Number(event.target.value))}
                  className="mt-2 w-full rounded-xl border border-white/15 bg-background p-3"
                />
              </label>
            ) : null}
            <p className="mt-3 text-xs text-muted-foreground">
              Real hardware uses raw finite-shot counts, requires confirmation, and can wait in a
              provider queue. Feature explanations remain local and are labeled accordingly.
            </p>
          </section>
          <Notice>{NOTICE}</Notice>
        </aside>
        <section className={panel}>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="font-display text-xl font-semibold">Measurements</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Use a synthetic example, enter values or upload a one-row CSV.
              </p>
            </div>
            <span className="rounded-full border border-emerald/25 bg-emerald/10 px-3 py-1 text-xs text-emerald">
              {source}
            </span>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <button
              type="button"
              className={subtleButton}
              disabled={!schema || busy}
              onClick={() => {
                if (schema) {
                  setValues(schema.demo);
                  setSource("synthetic demo");
                  setMessage("");
                }
              }}
            >
              <FlaskConical size={15} /> Load synthetic demo
            </button>
            <label className={`${subtleButton} cursor-pointer`}>
              <Upload size={15} /> Upload CSV
              <input
                type="file"
                accept=".csv,text/csv"
                className="sr-only"
                onChange={(event) => void upload(event.target.files?.[0])}
              />
            </label>
            <button
              type="button"
              className={subtleButton}
              onClick={() => {
                setValues({});
                setSource("manual");
              }}
            >
              <ArrowLeft size={15} /> Clear
            </button>
          </div>
          {schema && (
            <p className="mt-4 text-xs text-muted-foreground">
              {schema.rangeNote} Empty Framingham cells use the fitted median imputer.
            </p>
          )}
          {!schema && !modelsError && (
            <p className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="animate-spin" size={16} /> Loading input schema…
            </p>
          )}
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            {schema?.fields.map((field) => (
              <div key={field.name}>
                <label
                  htmlFor={`qml-${field.name}`}
                  className="flex items-center justify-between gap-2 text-sm font-medium"
                >
                  <span>{field.label}</span>
                  <span className="text-xs font-normal text-muted-foreground">{field.unit}</span>
                </label>
                <input
                  id={`qml-${field.name}`}
                  type="number"
                  min={field.min}
                  max={field.max}
                  step="any"
                  value={values[field.name] ?? ""}
                  onChange={(event) => {
                    setSource("manual");
                    setValues((prior) => ({
                      ...prior,
                      [field.name]: event.target.value === "" ? null : Number(event.target.value),
                    }));
                  }}
                  placeholder={`${field.min}–${field.max}`}
                  className="mt-2 w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2.5 text-sm outline-none focus:border-emerald/60 focus:ring-2 focus:ring-emerald/15"
                  aria-describedby={`qml-hint-${field.name}`}
                />
                <p id={`qml-hint-${field.name}`} className="mt-1 text-xs text-muted-foreground">
                  {field.name} · {field.allowedCodes || `${field.min} to ${field.max}`}
                </p>
              </div>
            ))}
          </div>
          {(message || modelsError) && (
            <div className="mt-5">
              <Notice error>{message || modelsError}</Notice>
            </div>
          )}
          <div className="mt-7 flex flex-wrap items-center gap-4">
            <button
              type="button"
              onClick={() => void submit()}
              disabled={!schema || busy}
              className={button}
            >
              {busy ? <Loader2 size={16} className="animate-spin" /> : <Activity size={16} />}
              {busy
                ? hardwareStatus || "Calculating with saved model…"
                : executionBackend === "simulator"
                  ? "Run analysis"
                  : "Submit real-hardware analysis"}
            </button>
            <span className="text-xs text-muted-foreground">No analysis history is stored.</span>
          </div>
        </section>
      </div>
    </Shell>
  );
}

function formatMetric(value: unknown, percent = true) {
  return typeof value === "number" && Number.isFinite(value)
    ? percent
      ? `${(value * 100).toFixed(1)}%`
      : value.toFixed(3)
    : "Unavailable";
}

export function QmlResults() {
  const { current } = useQmlSession();
  const [report, setReport] = useState<QmlReport | null>(null);
  const [reportBusy, setReportBusy] = useState(false);
  const [error, setError] = useState("");
  if (!current)
    return (
      <Shell eyebrow="Step 02 · Result" title="No analysis is open.">
        <Notice>
          Results live only in this browser session. Start a new analysis to view a result.
        </Notice>
        <Link to="/qml/analyze" className={`${button} mt-5`}>
          Start analysis
        </Link>
      </Shell>
    );
  const { prediction, request } = current;
  const maximumContribution = Math.max(
    ...prediction.explainability.features.map((item) => Math.abs(item.modelScoreChange)),
    1e-9,
  );
  async function makeReport() {
    setReportBusy(true);
    setError("");
    try {
      setReport(await qmlApi.report(request));
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setReportBusy(false);
    }
  }
  function download() {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `qml-report-${report.reportId}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }
  return (
    <Shell eyebrow="Step 02 · Result" title="A research score, with its provenance attached.">
      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <section className={`${panel} p-7`}>
          <span className="inline-flex items-center gap-2 rounded-full border border-emerald/30 bg-emerald/10 px-3 py-1 text-xs text-emerald">
            <CheckCircle2 size={14} /> Analysis complete
          </span>
          <h2 className="mt-6 font-display text-3xl font-semibold">{prediction.prediction}</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            The class follows the saved, model-specific decision threshold. It is not a clinical
            risk estimate for an individual.
          </p>
          <div className="mt-7 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white/5 p-4">
              <div className="text-xs text-muted-foreground">Calibrated model probability</div>
              <div className="mt-1 font-display text-2xl">
                {formatMetric(prediction.calibratedProbability)}
              </div>
            </div>
            <div className="rounded-xl bg-white/5 p-4">
              <div className="text-xs text-muted-foreground">Decision threshold</div>
              <div className="mt-1 font-display text-2xl">{formatMetric(prediction.threshold)}</div>
            </div>
            <div className="rounded-xl bg-white/5 p-4">
              <div className="text-xs text-muted-foreground">Decision value</div>
              <div className="mt-1 font-display text-2xl">
                {formatMetric(prediction.score, false)}
              </div>
            </div>
            <div className="rounded-xl bg-white/5 p-4">
              <div className="text-xs text-muted-foreground">Inference + explanation</div>
              <div className="mt-1 font-display text-2xl">
                {prediction.inferenceTimeMs.toFixed(1)} ms
              </div>
            </div>
          </div>
          <div className="mt-6">
            <Notice>{prediction.disclaimer}</Notice>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <Link to="/qml/evidence" className={subtleButton}>
              <BarChart3 size={15} /> Compare evidence
            </Link>
            <Link
              to="/qml/models/$modelId"
              params={{ modelId: prediction.model.id }}
              className={subtleButton}
            >
              <Atom size={15} /> Model details
            </Link>
          </div>
        </section>
        <aside className="space-y-5">
          <section className={panel}>
            <h2 className="font-display text-lg font-semibold">Model provenance</h2>
            <dl className="mt-4 space-y-3 text-sm">
              {[
                ["Model", prediction.model.name],
                ["Bundle version", prediction.model.version],
                ["Research run", prediction.researchRunId],
                ["Seed", prediction.researchSeed],
                ["Preprocessing SHA-256", `${prediction.preprocessingVersion.slice(0, 16)}…`],
                ["Backend", prediction.backend.name],
                ["Qubits", prediction.resources.qubits ?? "Not applicable"],
                ["Shots", prediction.resources.shots ?? "Analytic / not applicable"],
                [
                  "Circuit executions",
                  prediction.resources.circuitExecutionsThisPrediction ?? "Not applicable",
                ],
              ].map(([label, value]) => (
                <div
                  key={String(label)}
                  className="flex justify-between gap-4 border-b border-white/5 pb-2"
                >
                  <dt className="text-muted-foreground">{label}</dt>
                  <dd className="max-w-[60%] break-words text-right">{value}</dd>
                </div>
              ))}
            </dl>
            {prediction.hardwareExecution ? (
              <dl className="mt-4 space-y-2 rounded-xl border border-emerald/25 bg-emerald/5 p-4 text-sm">
                <div>
                  <dt className="text-muted-foreground">Provider / device</dt>
                  <dd>
                    {prediction.hardwareExecution.provider} · {prediction.hardwareExecution.device}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Remote job ID</dt>
                  <dd className="break-all">{prediction.hardwareExecution.jobId}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Provider status</dt>
                  <dd>{prediction.hardwareExecution.providerStatus}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Transpiled depth</dt>
                  <dd>
                    {String(prediction.hardwareExecution.transpilation.maxDepth ?? "Unavailable")}
                  </dd>
                </div>
              </dl>
            ) : null}
          </section>
          <section className={panel}>
            <h2 className="font-display text-lg font-semibold">Report</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              A local structured report includes this output, the saved benchmark record, timestamp
              and disclaimer.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => void makeReport()}
                disabled={reportBusy}
                className={button}
              >
                {reportBusy ? (
                  <Loader2 className="animate-spin" size={15} />
                ) : (
                  <FileText size={15} />
                )}{" "}
                Generate report
              </button>
              {report && (
                <button type="button" onClick={download} className={subtleButton}>
                  <Download size={15} /> Download JSON
                </button>
              )}
            </div>
            {report && (
              <p className="mt-3 text-xs text-emerald">
                Report {report.reportId.slice(0, 12)} ·{" "}
                {new Date(report.generatedAt).toLocaleString()}
              </p>
            )}
            {error && (
              <div className="mt-3">
                <Notice error>{error}</Notice>
              </div>
            )}
          </section>
        </aside>
      </div>
      <section className={`${panel} mt-6`}>
        <h2 className="font-display text-xl font-semibold">Inputs and transformed features</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          PCA components are mathematical reductions, not individual biomarker importance.
        </p>
        <div className="mt-5 grid gap-6 md:grid-cols-2">
          <div>
            <h3 className="text-sm font-semibold text-emerald">Measurements used</h3>
            <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
              {Object.entries(prediction.inputFeatures).map(([name, value]) => (
                <div
                  key={name}
                  className="flex justify-between gap-2 rounded-lg bg-white/5 px-3 py-2"
                >
                  <span className="text-muted-foreground">{name}</span>
                  <span>{value ?? "Imputed"}</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-cyan-glow">Saved preprocessing output</h3>
            <div className="mt-3 space-y-2 text-sm">
              {Object.entries(prediction.transformedFeatures).map(([name, value]) => (
                <div
                  key={name}
                  className="flex justify-between gap-3 rounded-lg bg-white/5 px-3 py-2"
                >
                  <span className="text-muted-foreground">{name}</span>
                  <span>{value.toFixed(3)}</span>
                </div>
              ))}
            </div>
            <ul className="mt-5 list-disc space-y-2 pl-5 text-xs text-muted-foreground">
              {prediction.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>
      <section className={`${panel} mt-6`}>
        <h2 className="font-display text-xl font-semibold">Patient-level model behaviour</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          {prediction.explainability.reference} Positive changes mean the entered value raised this
          model score relative to its training-median reference; negative changes lowered it.
        </p>
        <div className="mt-5 space-y-3">
          {prediction.explainability.features.map((item) => (
            <div key={item.feature} className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="font-medium">
                  {item.label} <span className="text-muted-foreground">({item.feature})</span>
                </span>
                <span className={item.modelScoreChange >= 0 ? "text-rose-300" : "text-cyan-glow"}>
                  {item.modelScoreChange >= 0 ? "+" : ""}
                  {(item.modelScoreChange * 100).toFixed(2)} score points
                </span>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-black/25">
                <div
                  className={`h-full rounded-full ${item.modelScoreChange >= 0 ? "bg-rose-400" : "bg-cyan-glow"}`}
                  style={{
                    width: `${Math.max(2, (Math.abs(item.modelScoreChange) / maximumContribution) * 100)}%`,
                  }}
                />
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                Input {item.inputValue ?? "imputed"} {item.unit} · training median reference{" "}
                {item.referenceValue} {item.unit}
              </p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-muted-foreground">{prediction.explainability.disclaimer}</p>
      </section>
    </Shell>
  );
}

export function QmlEvidence() {
  const [data, setData] = useState<QmlEvidenceData | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    qmlApi
      .evidence()
      .then((result) => {
        if (active) setData(result);
      })
      .catch((reason) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, []);
  const summary: QmlEvidenceMetric[] = Array.isArray(data?.framingham?.summary)
    ? data.framingham.summary
    : [];
  const selected = summary.filter((row) =>
    ["angle_qksvm_pca2", "logistic_pca2", "rbf_svm_full"].includes(row.model),
  );
  const chart = selected.map((row) => ({
    model: row.model.replaceAll("_", " "),
    AUROC: row.auroc,
    AUPRC: row.auprc,
    "Balanced accuracy": row.balanced_accuracy,
  }));
  const bestFraminghamAuprc = Math.max(
    ...summary.map((row) => (typeof row.auprc === "number" ? row.auprc : Number.NEGATIVE_INFINITY)),
  );
  const bestUciAuprc = Math.max(
    ...(data?.uci.models || []).map((row) =>
      typeof row.auprc === "number" ? row.auprc : Number.NEGATIVE_INFINITY,
    ),
  );
  const bestQcnnAuprc = new Map<string, number>();
  for (const row of data?.qcnn.runs || []) {
    const value = row.metrics.auprc;
    if (typeof value === "number" && value > (bestQcnnAuprc.get(row.dataset) ?? -Infinity)) {
      bestQcnnAuprc.set(row.dataset, value);
    }
  }
  return (
    <Shell
      eyebrow="Model catalogue · evidence"
      title="Every audited model, with honest run status."
    >
      {error && <Notice error>{error}</Notice>}
      {!data && !error && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="animate-spin" size={16} /> Loading saved benchmark evidence…
        </p>
      )}
      {data && (
        <>
          <div className="mb-6">
            <Notice>
              Tier rubric: Best observed is the highest saved AUPRC within that benchmark; Moderate
              is within 0.10 AUPRC of it; Experimental covers the remaining smoke results. These are
              descriptive tiers, not statistical significance or clinical validation. Runnable is a
              separate status requiring a replayed checkpoint, preprocessor, schema and endpoint.
            </Notice>
          </div>
          <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
            <section className={panel}>
              <h2 className="font-display text-xl font-semibold">Audited Framingham comparison</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Three repeated seeds. Quantum and PCA-2 logistic models use 256 matched training
                rows. The full-feature RBF model uses a larger training set and is a separate
                reference.
              </p>
              <div
                role="img"
                aria-label="Saved Framingham AUROC, AUPRC and balanced accuracy by model"
                className="mt-5 h-72"
              >
                <Suspense
                  fallback={<p className="p-5 text-sm text-muted-foreground">Loading chart…</p>}
                >
                  <QmlEvidenceChart data={chart} />
                </Suspense>
              </div>
            </section>
            <aside className={`${panel} flex flex-col justify-center`}>
              <Microscope size={30} className="text-emerald" />
              <h2 className="mt-5 font-display text-xl font-semibold">What this evidence means</h2>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                AUROC measures ranking across thresholds. AUPRC highlights positive-case retrieval,
                especially when cases are uncommon. Sensitivity is the share of positives detected;
                specificity is the share of negatives correctly rejected. None is an individual
                confidence score.
              </p>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                The quantum kernel used exact simulated states and classical fidelity. No real
                hardware or general quantum advantage is claimed.
              </p>
            </aside>
          </div>
          <section className={`${panel} mt-6 overflow-x-auto`}>
            <h2 className="font-display text-xl font-semibold">Measured aggregate metrics</h2>
            <table className="mt-4 min-w-[760px] w-full text-left text-sm">
              <thead className="border-b border-white/10 text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  {[
                    "Model",
                    "Tier",
                    "Availability",
                    "AUROC",
                    "AUPRC",
                    "Balanced accuracy",
                    "Sensitivity",
                    "Specificity",
                    "F1",
                    "Fit time",
                  ].map((head) => (
                    <th key={head} className="px-3 py-3 font-medium">
                      {head}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {summary.map((row) => {
                  const runnable = runnableFramingham.has(row.model);
                  return (
                    <tr key={row.model} className="border-b border-white/5">
                      <td className="px-3 py-3 font-medium">
                        {row.model.replaceAll("_", " ")}
                        {row.model === "rbf_svm_full" && (
                          <span className="block text-xs text-cyan-glow">
                            Full-training reference
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-3">
                        <TierBadge tier={observedTier(row, bestFraminghamAuprc)} />
                      </td>
                      <td className="px-3 py-3">
                        {runnable ? (
                          <Link to="/qml/analyze" className="text-emerald hover:underline">
                            Runnable · Open
                          </Link>
                        ) : (
                          <span className="text-muted-foreground">Evidence only</span>
                        )}
                      </td>
                      <td className="px-3 py-3">{formatMetric(row.auroc)}</td>
                      <td className="px-3 py-3">{formatMetric(row.auprc)}</td>
                      <td className="px-3 py-3">{formatMetric(row.balanced_accuracy)}</td>
                      <td className="px-3 py-3">{formatMetric(row.recall_sensitivity)}</td>
                      <td className="px-3 py-3">{formatMetric(row.specificity)}</td>
                      <td className="px-3 py-3">{formatMetric(row.f1)}</td>
                      <td className="px-3 py-3">
                        {typeof row.training_time_seconds === "number"
                          ? `${row.training_time_seconds.toFixed(3)} s`
                          : "Unavailable"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="mt-4 text-xs text-muted-foreground">
              The repeated test splits overlap; their spread is descriptive. Scores are from
              educational data and do not establish clinical performance.
            </p>
          </section>
          <div className="mt-6 grid gap-5 md:grid-cols-2">
            <section className={panel}>
              <h2 className="font-display text-xl font-semibold">Cleveland UCI smoke run</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                One small diagnostic test split. Classical RBF SVM is available for a research
                demonstration; Pauli OQSVM and hybrid QMLP remain evidence only.
              </p>
              <div className="mt-4 space-y-3 text-sm">
                {data.uci.models.map((row) => {
                  const runnable = row.model === "rbf_svm";
                  return (
                    <article
                      key={row.model}
                      className="rounded-xl border border-white/10 bg-white/5 p-3"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-medium">{row.model.replaceAll("_", " ")}</span>
                        <div className="flex flex-wrap gap-2">
                          <TierBadge tier={observedTier(row, bestUciAuprc)} />
                          {runnable ? (
                            <Link
                              to="/qml/analyze"
                              className="rounded-full border border-cyan-glow/30 px-2.5 py-1 text-xs text-cyan-glow hover:bg-cyan-glow/10"
                            >
                              Runnable · Open
                            </Link>
                          ) : (
                            <span className="rounded-full border border-white/15 px-2.5 py-1 text-xs text-muted-foreground">
                              Evidence only
                            </span>
                          )}
                        </div>
                      </div>
                      <p className="mt-2 text-xs text-muted-foreground">
                        AUPRC {formatMetric(row.auprc)} · AUROC {formatMetric(row.auroc)} · F1{" "}
                        {formatMetric(row.f1)}
                      </p>
                    </article>
                  );
                })}
              </div>
            </section>
            <section className={panel}>
              <h2 className="font-display text-xl font-semibold">QCNN and image experiments</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                All ten recorded runs are catalogued. These are smoke/checkpoint experiments; WDBC
                is diagnostic and BreastMNIST uses image inputs.
              </p>
              <div className="mt-4 max-h-[32rem] space-y-3 overflow-y-auto pr-1 text-sm">
                {data.qcnn.runs.map((row) => {
                  const runnable = row.runId === runnableQcnnRun;
                  const best = bestQcnnAuprc.get(row.dataset) ?? Number.NEGATIVE_INFINITY;
                  return (
                    <article
                      key={row.runId}
                      className="rounded-xl border border-white/10 bg-white/5 p-3"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-medium">
                          {row.dataset} · {row.model.replaceAll("_", " ")}
                        </span>
                        <div className="flex flex-wrap gap-2">
                          <TierBadge tier={observedTier(row.metrics, best)} />
                          {runnable ? (
                            <Link
                              to="/qml/imaging"
                              className="rounded-full border border-cyan-glow/30 px-2.5 py-1 text-xs text-cyan-glow hover:bg-cyan-glow/10"
                            >
                              Runnable · Open
                            </Link>
                          ) : (
                            <span className="rounded-full border border-white/15 px-2.5 py-1 text-xs text-muted-foreground">
                              Evidence only
                            </span>
                          )}
                        </div>
                      </div>
                      <p className="mt-2 text-xs text-muted-foreground">
                        Run {row.runId} · AUPRC {formatMetric(row.metrics.auprc)} · AUROC{" "}
                        {formatMetric(row.metrics.auroc)}
                      </p>
                    </article>
                  );
                })}
              </div>
            </section>
          </div>
          <div className="mt-6">
            <Notice>
              Every audited experiment is visible on this catalogue. Only entries labelled Runnable
              appear in an input workflow. Evidence-only entries keep their scores and limitations
              visible, but cannot be executed until their complete serving bundles replay
              successfully.
            </Notice>
          </div>
        </>
      )}
    </Shell>
  );
}

export function QmlModelDetails({ modelId }: { modelId: string }) {
  const [model, setModel] = useState<QmlModel | null>(null);
  const [evidence, setEvidence] = useState<QmlModelEvidence | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    Promise.all([qmlApi.models(), qmlApi.modelEvidence(modelId)])
      .then(([models, result]) => {
        if (active) {
          setModel(models.models.find((item) => item.id === modelId) || null);
          setEvidence(result);
        }
      })
      .catch((reason) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, [modelId]);
  return (
    <Shell eyebrow="Model file · provenance" title={model?.name || "Model details"}>
      {error && <Notice error>{error}</Notice>}
      {!model && !error && (
        <p className="flex items-center gap-2 text-muted-foreground">
          <Loader2 size={16} className="animate-spin" /> Loading model details…
        </p>
      )}
      {model && evidence && (
        <div className="grid gap-5 lg:grid-cols-2">
          <section className={panel}>
            <div className="flex items-center gap-2 text-emerald">
              <Atom size={20} />
              <span className="text-xs uppercase tracking-widest">
                {model.modality} · {model.type.replaceAll("_", " ")}
              </span>
            </div>
            <div className="mt-4 flex flex-wrap gap-2 text-xs">
              <span className="rounded-full border border-emerald/30 bg-emerald/10 px-2.5 py-1 text-emerald">
                {model.performanceTag === "best" ? "Best observed" : model.performanceTag}
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-muted-foreground">
                {model.availability === "runnable"
                  ? "Runnable"
                  : model.availability === "configured_not_run"
                    ? "Configured, not run"
                    : model.availability === "unavailable"
                      ? "Unavailable"
                      : "Evidence only"}
              </span>
            </div>
            <h2 className="mt-4 font-display text-xl font-semibold">How it works</h2>
            <p className="mt-3 text-sm leading-7 text-muted-foreground">
              {model.modality === "genomics"
                ? "This model receives the same four features produced by the synthetic FH evidence pathway: untreated LDL-C, genomic evidence strength, family history and phenotype. It reproduces synthetic referral rules and is not an independently validated FH detector."
                : model.modality === "imaging"
                  ? model.availability === "runnable"
                    ? "This saved BreastMNIST QCNN has a verified serving bundle and can run on a synthetic demo image or a PNG/JPEG. Its uncalibrated score is research-only, not a diagnosis."
                    : "This saved BreastMNIST or WDBC experiment remains visible for comparison. Live image inference is not enabled because its exact weights and preprocessing have not been promoted and replay-verified."
                  : model.type === "quantum_kernel"
                    ? "Clinical inputs pass through the experiment's fitted preprocessing and a bounded quantum feature map. Saved benchmark evidence remains separate from clinical interpretation, and ideal-simulator results are not hardware or quantum-advantage evidence."
                    : model.workflow === "framingham"
                      ? "This model belongs to the audited Framingham teaching benchmark. The registry preserves its dataset-qualified metrics, representation and evidence limitations."
                      : "This model belongs to the single-seed Cleveland heart-disease presence benchmark. It is a diagnostic classification experiment, not future-event prediction."}
            </p>
            <div className="mt-5">
              <Notice>{model.limitation}</Notice>
            </div>
          </section>
          <section className={panel}>
            <h2 className="font-display text-xl font-semibold">Saved configuration</h2>
            <dl className="mt-4 space-y-3 text-sm">
              {[
                ["Model version", model.version],
                ["Research model", model.research_model],
                ["Endpoint", model.endpoint],
                ["Availability", model.availability.replaceAll("_", " ")],
                [
                  "Backend",
                  ["quantum_kernel", "hybrid_qml", "qcnn"].includes(model.type)
                    ? "Ideal local simulator + classical fidelity"
                    : model.type === "quantum_convolutional"
                      ? "PennyLane default.qubit analytic CPU simulator"
                      : "Classical CPU",
                ],
                [
                  "Qubits",
                  model.type === "quantum_kernel"
                    ? "2"
                    : model.type === "quantum_convolutional"
                      ? "4"
                      : "Not applicable",
                ],
                [
                  "Evidence maturity",
                  model.evidenceMaturity,
                ],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="flex justify-between gap-4 border-b border-white/5 pb-2"
                >
                  <dt className="text-muted-foreground">{label}</dt>
                  <dd className="text-right">{value}</dd>
                </div>
              ))}
            </dl>
            <h3 className="mt-6 font-semibold">Selected test evidence</h3>
            <div className="mt-3 grid grid-cols-3 gap-2">
              {[
                ["AUROC", evidence.selectedRun.auroc],
                ["AUPRC", evidence.selectedRun.auprc],
                [
                  "Sensitivity",
                  evidence.selectedRun.recall_sensitivity ?? evidence.selectedRun.sensitivity,
                ],
              ].map(([label, value]) => (
                <div key={String(label)} className="rounded-lg bg-white/5 p-3">
                  <div className="text-xs text-muted-foreground">{label}</div>
                  <div className="mt-1 font-display text-lg">{formatMetric(value)}</div>
                </div>
              ))}
            </div>
            <p className="mt-4 text-xs text-muted-foreground">
              These are benchmark group metrics, not confidence for one prediction.
            </p>
          </section>
          {model.availability === "runnable" && model.modality === "ehr" && (
            <Link to="/qml/analyze" search={{ modelId: model.id }} className={button}>Run this EHR model <ArrowRight size={15} /></Link>
          )}
          {model.availability === "runnable" && model.modality === "genomics" && (
            <Link to="/qml/genomics/fh" className={button}>Use the FH pathway <ArrowRight size={15} /></Link>
          )}
          {model.availability === "runnable" && model.modality === "imaging" && (
            <Link to="/qml/imaging" className={button}>Use this imaging workflow <ArrowRight size={15} /></Link>
          )}
          {model.availability !== "runnable" && (
            <Notice>
              {model.availability === "configured_not_run"
                ? "This configuration has not produced a verified run. It cannot be launched from the portal yet."
                : model.availability === "unavailable"
                  ? "This model is unavailable for portal execution."
                  : "This completed model is preserved as evidence-only until its exact weights and preprocessing replay are promoted into the inference bundle."}
            </Notice>
          )}
        </div>
      )}
    </Shell>
  );
}
