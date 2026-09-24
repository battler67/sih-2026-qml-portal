import {
  Activity,
  Atom,
  CheckCircle2,
  CircleAlert,
  Download,
  FlaskConical,
  Image as ImageIcon,
  Loader2,
  RotateCcw,
  Upload,
} from "lucide-react";
import { Link } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState, type DragEvent, type ReactNode } from "react";
import { BackgroundFX } from "@/components/BackgroundFX";
import {
  qmlApi,
  waitForHardwareResult,
  type HardwareCapabilities,
  type HardwareProvider,
  type QcnnPrediction,
} from "@/lib/qml-api";

const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(["image/png", "image/jpeg"]);
const FLOW = [
  "Medical image",
  "28×28 grayscale",
  "2×2 spatial pooling",
  "RY angle encoding",
  "QCNN 4→2→1",
  "Pauli-Z measurement",
  "Model prediction",
];
const panel =
  "rounded-2xl border border-white/10 bg-card/70 p-5 shadow-xl shadow-black/10 backdrop-blur-sm";
const button =
  "inline-flex items-center justify-center gap-2 rounded-full bg-emerald px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald disabled:cursor-not-allowed disabled:opacity-50";
const subtleButton =
  "inline-flex items-center justify-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-foreground transition hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald";

function Notice({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return (
    <div
      role={error ? "alert" : "note"}
      className={`flex gap-3 rounded-xl border p-4 text-sm ${error ? "border-red-400/30 bg-red-400/10 text-red-100" : "border-emerald/25 bg-emerald/10 text-muted-foreground"}`}
    >
      <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
      <div>{children}</div>
    </div>
  );
}

function formatScore(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

async function createSyntheticDemoImage(): Promise<File> {
  const size = 28;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("This browser cannot create the synthetic demo image.");
  const pixels = context.createImageData(size, size);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const leftLobe = Math.exp(-((x - 9) ** 2 + (y - 14) ** 2) / 52);
      const rightLobe = Math.exp(-((x - 19) ** 2 + (y - 13) ** 2) / 42);
      const texture = 10 * Math.sin(x * 0.65) * Math.cos(y * 0.48);
      const intensity = Math.max(
        0,
        Math.min(255, Math.round(24 + 126 * leftLobe + 92 * rightLobe + texture)),
      );
      const offset = (y * size + x) * 4;
      pixels.data[offset] = intensity;
      pixels.data[offset + 1] = intensity;
      pixels.data[offset + 2] = intensity;
      pixels.data[offset + 3] = 255;
    }
  }
  context.putImageData(pixels, 0, 0);
  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (value) =>
        value ? resolve(value) : reject(new Error("Could not encode the synthetic demo image.")),
      "image/png",
    );
  });
  return new File([blob], "synthetic-qcnn-demo.png", { type: "image/png" });
}

export function QcnnImaging() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [result, setResult] = useState<QcnnPrediction | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [syntheticDemo, setSyntheticDemo] = useState(false);
  const [executionBackend, setExecutionBackend] = useState<"simulator" | HardwareProvider>(
    "simulator",
  );
  const [shots, setShots] = useState(128);
  const [hardwareStatus, setHardwareStatus] = useState("");
  const [capabilities, setCapabilities] = useState<HardwareCapabilities | null>(null);

  useEffect(() => {
    qmlApi
      .hardwareCapabilities()
      .then(setCapabilities)
      .catch(() => setCapabilities(null));
  }, []);

  useEffect(() => {
    if (!file) {
      setPreview("");
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const selectFile = useCallback((candidate?: File, isSyntheticDemo = false) => {
    setError("");
    setResult(null);
    setSyntheticDemo(false);
    if (!candidate) return;
    if (!ACCEPTED_TYPES.has(candidate.type)) {
      setError("Choose a PNG or JPEG image.");
      return;
    }
    if (candidate.size === 0) {
      setError("The selected file is empty.");
      return;
    }
    if (candidate.size > MAX_IMAGE_BYTES) {
      setError("The image must be 5 MB or smaller.");
      return;
    }
    setFile(candidate);
    setSyntheticDemo(isSyntheticDemo);
  }, []);

  async function loadSyntheticDemo() {
    try {
      selectFile(await createSyntheticDemoImage(), true);
    } catch (reason) {
      setError((reason as Error).message);
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    selectFile(event.dataTransfer.files[0]);
  }

  async function predict() {
    if (!file) {
      setError("Select an image before running the QCNN.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      if (executionBackend === "simulator") {
        setHardwareStatus("");
        setResult(await qmlApi.predictQcnn(file));
      } else {
        const preview = await qmlApi.hardwarePreview("breastmnist-qcnn", executionBackend);
        const device = (preview.selectedDevice as { name?: string })?.name || executionBackend;
        if (
          !window.confirm(
            `Submit one ${shots}-shot QCNN circuit to real hardware on ${device}? Raw image pixels are processed locally; only the four encoded angles enter the circuit.`,
          )
        ) {
          setBusy(false);
          return;
        }
        const job = await qmlApi.submitQcnnHardware(file, executionBackend, shots);
        setHardwareStatus(job.message);
        setResult(
          await waitForHardwareResult<QcnnPrediction>(job.jobId, (state) =>
            setHardwareStatus(state.message),
          ),
        );
      }
    } catch (reason) {
      setResult(null);
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function downloadReport() {
    if (!result) return;
    const report = {
      generatedAt: new Date().toISOString(),
      sourceFile: file ? { mediaType: file.type, sizeBytes: file.size } : null,
      prediction: result,
      disclaimer: result.disclaimer,
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `qcnn-report-${result.researchRunId}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function reset() {
    setFile(null);
    setResult(null);
    setError("");
    setSyntheticDemo(false);
    if (inputRef.current) inputRef.current.value = "";
  }

  const maximumRegionChange = result
    ? Math.max(
        ...result.explainability.regions.map((item) => Math.abs(item.modelScoreChange)),
        1e-9,
      )
    : 1;

  return (
    <div className="relative min-h-screen overflow-hidden">
      <BackgroundFX />
      <div className="relative z-10 mx-auto max-w-7xl px-4 pb-16 sm:px-6">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 py-5">
          <Link to="/" className="flex items-center gap-2 font-display text-lg font-semibold">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald to-cyan-glow text-background">
              <Atom size={19} />
            </span>
            QDNA <span className="text-sm font-normal text-muted-foreground">/ Clinical Lab</span>
          </Link>
          <nav aria-label="QML navigation" className="flex flex-wrap items-center gap-2 text-sm">
            <Link to="/qml" className={subtleButton}>
              Overview
            </Link>
            <Link to="/qml/analyze" className={subtleButton}>
              Tabular analysis
            </Link>
            <Link to="/qml/evidence" className={subtleButton}>
              Evidence
            </Link>
          </nav>
        </header>

        <main className="py-9">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald">
            Breast imaging · QCNN research demo
          </p>
          <h1 className="mt-2 max-w-4xl font-display text-3xl font-semibold tracking-tight sm:text-5xl">
            Upload an image and run the trained four-qubit QCNN.
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-muted-foreground">
            The service converts one PNG or JPEG to the exact 28×28 grayscale representation used by
            the BreastMNIST smoke experiment, reduces it to four angles, and runs the saved
            checkpoint on the local analytic simulator or, when configured and confirmed, a
            compatible real QPU.
          </p>

          <div className="mt-8 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
            <section className={panel}>
              <h2 className="font-display text-xl font-semibold">Medical-image input</h2>
              <div
                onDragEnter={(event) => {
                  event.preventDefault();
                  setDragging(true);
                }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                className={`mt-5 rounded-2xl border-2 border-dashed p-6 text-center transition ${dragging ? "border-emerald bg-emerald/10" : "border-white/15 bg-white/5"}`}
              >
                {preview ? (
                  <img
                    src={preview}
                    alt="Selected medical image preview"
                    className="mx-auto h-52 w-full rounded-xl object-contain"
                  />
                ) : (
                  <div className="flex h-52 flex-col items-center justify-center text-muted-foreground">
                    <ImageIcon size={38} className="text-emerald" />
                    <p className="mt-4 text-sm">Drag and drop a PNG or JPEG here</p>
                    <p className="mt-1 text-xs">Maximum file size: 5 MB</p>
                  </div>
                )}
                <input
                  ref={inputRef}
                  type="file"
                  accept="image/png,image/jpeg"
                  onChange={(event) => selectFile(event.target.files?.[0])}
                  className="sr-only"
                  id="qcnn-image"
                />
                <div className="mt-4 flex flex-wrap justify-center gap-3">
                  <button
                    type="button"
                    onClick={() => void loadSyntheticDemo()}
                    className={subtleButton}
                  >
                    <FlaskConical size={15} /> Load synthetic demo image
                  </button>
                  <label htmlFor="qcnn-image" className={`${subtleButton} cursor-pointer`}>
                    <Upload size={15} /> Choose image
                  </label>
                </div>
              </div>
              {file ? (
                <dl className="mt-4 grid grid-cols-2 gap-3 rounded-xl bg-white/5 p-4 text-sm">
                  <div>
                    <dt className="text-muted-foreground">File</dt>
                    <dd className="mt-1 break-all">{file.name}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Size</dt>
                    <dd className="mt-1">{(file.size / 1024).toFixed(1)} KB</dd>
                  </div>
                </dl>
              ) : null}
              {syntheticDemo ? (
                <div className="mt-4">
                  <Notice>
                    Synthetic technical test pattern generated locally in this browser. It is not a
                    BreastMNIST datapoint, patient scan, or medically meaningful example.
                  </Notice>
                </div>
              ) : null}
              {error ? (
                <div className="mt-4">
                  <Notice error>{error}</Notice>
                </div>
              ) : null}
              <div className="mt-5 grid gap-3 rounded-xl border border-white/10 bg-white/5 p-4 sm:grid-cols-2">
                <label className="text-sm">
                  <span className="block text-xs text-muted-foreground">Execution backend</span>
                  <select
                    value={executionBackend}
                    onChange={(event) =>
                      setExecutionBackend(event.target.value as "simulator" | HardwareProvider)
                    }
                    disabled={busy}
                    className="mt-2 w-full rounded-lg border border-white/15 bg-background px-3 py-2"
                  >
                    <option value="simulator">Local ideal simulator (default)</option>
                    <option
                      value="ibm"
                      disabled={capabilities ? !capabilities.providers.ibm.configured : false}
                    >
                      IBM Quantum hardware
                    </option>
                    <option
                      value="qbraid"
                      disabled={capabilities ? !capabilities.providers.qbraid.configured : false}
                    >
                      qBraid hardware (free QPU only)
                    </option>
                  </select>
                </label>
                <label className="text-sm">
                  <span className="block text-xs text-muted-foreground">Shots</span>
                  <input
                    type="number"
                    min={32}
                    max={1024}
                    step={32}
                    value={shots}
                    onChange={(event) => setShots(Number(event.target.value))}
                    disabled={busy || executionBackend === "simulator"}
                    className="mt-2 w-full rounded-lg border border-white/15 bg-background px-3 py-2"
                  />
                </label>
                <p className="text-xs text-muted-foreground sm:col-span-2">
                  Real hardware requires confirmation, uses raw finite-shot counts, and may wait in
                  a provider queue. No automatic paid-device selection.
                </p>
              </div>
              <div className="mt-5 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => void predict()}
                  disabled={!file || busy}
                  className={button}
                >
                  {busy ? <Loader2 size={16} className="animate-spin" /> : <Activity size={16} />}
                  {busy
                    ? hardwareStatus || "Running QCNN…"
                    : executionBackend === "simulator"
                      ? "Run QCNN prediction"
                      : "Submit real-hardware QCNN"}
                </button>
                {file ? (
                  <button type="button" onClick={reset} className={subtleButton}>
                    <RotateCcw size={15} /> Reset
                  </button>
                ) : null}
              </div>
            </section>

            <section className={panel} aria-live="polite">
              <h2 className="font-display text-xl font-semibold">Prediction output</h2>
              {!result && !busy ? (
                <div className="mt-5 flex min-h-80 flex-col items-center justify-center rounded-xl border border-white/10 bg-white/5 text-center text-muted-foreground">
                  <Atom size={36} className="text-cyan-glow" />
                  <p className="mt-4 text-sm">
                    Select an image to view the real checkpoint output.
                  </p>
                </div>
              ) : null}
              {busy ? (
                <div className="mt-5 flex min-h-80 items-center justify-center gap-3 text-muted-foreground">
                  <Loader2 className="animate-spin text-emerald" /> Simulating the four-qubit
                  circuit…
                </div>
              ) : null}
              {result ? (
                <div className="mt-5">
                  <div className="inline-flex items-center gap-2 rounded-full bg-emerald/10 px-3 py-1 text-xs text-emerald">
                    <CheckCircle2 size={14} /> Real checkpoint inference complete
                  </div>
                  <h3 className="mt-5 font-display text-3xl font-semibold capitalize">
                    {result.prediction.replaceAll("_", " / ")}
                  </h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Experimental model prediction; this is not a confirmed diagnosis.
                  </p>
                  <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-xl bg-white/5 p-4">
                      <div className="text-xs text-muted-foreground">Malignant model score</div>
                      <div className="mt-1 font-display text-2xl">
                        {formatScore(result.malignantScore)}
                      </div>
                    </div>
                    <div className="rounded-xl bg-white/5 p-4">
                      <div className="text-xs text-muted-foreground">Saved threshold</div>
                      <div className="mt-1 font-display text-2xl">
                        {formatScore(result.threshold)}
                      </div>
                    </div>
                    <div className="rounded-xl bg-white/5 p-4">
                      <div className="text-xs text-muted-foreground">Pauli-Z expectation</div>
                      <div className="mt-1 font-display text-2xl">
                        {result.measurementExpectationZ.toFixed(3)}
                      </div>
                    </div>
                    <div className="rounded-xl bg-white/5 p-4">
                      <div className="text-xs text-muted-foreground">Inference + explanation</div>
                      <div className="mt-1 font-display text-2xl">
                        {result.inferenceTimeMs.toFixed(1)} ms
                      </div>
                    </div>
                  </div>
                  <dl className="mt-5 grid gap-2 text-sm sm:grid-cols-2">
                    <div className="rounded-lg bg-white/5 px-3 py-2">
                      <dt className="text-muted-foreground">Original shape</dt>
                      <dd>{result.input.originalShape.join(" × ")}</dd>
                    </div>
                    <div className="rounded-lg bg-white/5 px-3 py-2">
                      <dt className="text-muted-foreground">Processed shape</dt>
                      <dd>{result.input.processedShape.join(" × ")}</dd>
                    </div>
                    <div className="rounded-lg bg-white/5 px-3 py-2">
                      <dt className="text-muted-foreground">Backend</dt>
                      <dd>{result.backend.name}</dd>
                    </div>
                    <div className="rounded-lg bg-white/5 px-3 py-2">
                      <dt className="text-muted-foreground">Run</dt>
                      <dd>{result.researchRunId}</dd>
                    </div>
                  </dl>
                  {result.hardwareExecution ? (
                    <dl className="mt-4 grid gap-2 rounded-xl border border-emerald/25 bg-emerald/5 p-4 text-sm sm:grid-cols-2">
                      <div>
                        <dt className="text-muted-foreground">Provider / device</dt>
                        <dd>
                          {result.hardwareExecution.provider} · {result.hardwareExecution.device}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-muted-foreground">Remote job ID</dt>
                        <dd className="break-all">{result.hardwareExecution.jobId}</dd>
                      </div>
                      <div>
                        <dt className="text-muted-foreground">Shots / circuits</dt>
                        <dd>
                          {result.hardwareExecution.shots} / {result.hardwareExecution.circuitCount}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-muted-foreground">Provider status</dt>
                        <dd>{result.hardwareExecution.providerStatus}</dd>
                      </div>
                    </dl>
                  ) : null}
                  <div className="mt-5">
                    <Notice>{result.disclaimer}</Notice>
                  </div>
                  <button type="button" onClick={downloadReport} className={`${subtleButton} mt-4`}>
                    <Download size={15} /> Download JSON report
                  </button>
                </div>
              ) : null}
            </section>
          </div>

          <section className={`${panel} mt-6`}>
            <h2 className="font-display text-xl font-semibold">What enters the quantum model</h2>
            <div className="mt-5 grid gap-2 md:grid-cols-7">
              {FLOW.map((step, index) => (
                <div
                  key={step}
                  className="relative rounded-xl border border-white/10 bg-white/5 p-3 text-center text-xs"
                >
                  <span className="block text-emerald">{String(index + 1).padStart(2, "0")}</span>
                  <span className="mt-1 block">{step}</span>
                </div>
              ))}
            </div>
            {result ? (
              <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_1.2fr]">
                <div>
                  <h3 className="text-sm font-semibold text-cyan-glow">Four encoded angles</h3>
                  <div className="mt-3 grid grid-cols-2 gap-2">
                    {Object.entries(result.transformedFeatures).map(([name, value]) => (
                      <div
                        key={name}
                        className="flex justify-between rounded-lg bg-white/5 px-3 py-2 text-sm"
                      >
                        <span className="text-muted-foreground">{name}</span>
                        <span>{value.toFixed(4)}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-emerald">Quantum configuration</h3>
                  <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                    <div className="rounded-lg bg-white/5 px-3 py-2">
                      <dt className="text-muted-foreground">Qubits</dt>
                      <dd>{result.quantum.qubits}</dd>
                    </div>
                    <div className="rounded-lg bg-white/5 px-3 py-2">
                      <dt className="text-muted-foreground">Stages</dt>
                      <dd>{result.quantum.stages}</dd>
                    </div>
                    <div className="rounded-lg bg-white/5 px-3 py-2">
                      <dt className="text-muted-foreground">Active path</dt>
                      <dd>{result.quantum.activeQubits}</dd>
                    </div>
                    <div className="rounded-lg bg-white/5 px-3 py-2">
                      <dt className="text-muted-foreground">Circuit depth</dt>
                      <dd>{result.quantum.circuitDepth}</dd>
                    </div>
                  </dl>
                  <ul className="mt-4 list-disc space-y-1 pl-5 text-xs text-muted-foreground">
                    {result.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : null}
            {result ? (
              <div className="mt-7 border-t border-white/10 pt-6">
                <h3 className="text-sm font-semibold text-rose-200">2x2 occlusion sensitivity</h3>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">
                  {result.explainability.reference}
                </p>
                <div className="mt-4 grid max-w-sm grid-cols-2 gap-2">
                  {result.explainability.regions.map((region) => {
                    const strength = Math.abs(region.modelScoreChange) / maximumRegionChange;
                    const positive = region.modelScoreChange >= 0;
                    return (
                      <div
                        key={region.id}
                        className="aspect-square rounded-xl border border-white/15 p-3 text-xs"
                        style={{
                          backgroundColor: positive
                            ? `rgba(251, 113, 133, ${0.12 + strength * 0.58})`
                            : `rgba(34, 211, 238, ${0.12 + strength * 0.58})`,
                        }}
                      >
                        <span className="block capitalize">{region.id.replaceAll("_", " ")}</span>
                        <span className="mt-2 block font-semibold">
                          {region.modelScoreChange >= 0 ? "+" : ""}
                          {(region.modelScoreChange * 100).toFixed(2)} points
                        </span>
                      </div>
                    );
                  })}
                </div>
                <p className="mt-3 text-xs text-muted-foreground">
                  Rose regions raised the model score relative to mid-gray occlusion; cyan regions
                  lowered it. {result.explainability.disclaimer}
                </p>
              </div>
            ) : null}
          </section>
        </main>
      </div>
    </div>
  );
}
