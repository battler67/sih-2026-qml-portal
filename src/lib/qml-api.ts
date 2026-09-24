export const QML_API_BASE = import.meta.env.VITE_QML_API_BASE_URL || "http://127.0.0.1:8010";
const PREFIX = QML_API_BASE.endsWith("/api/qml") ? "/v1" : "/api/qml/v1";

export type QmlField = {
  name: string;
  label: string;
  unit: string;
  min: number;
  max: number;
  allowedCodes: string | null;
  required: boolean;
  nullable: boolean;
};
export type QmlSchema = {
  modelId: string;
  workflow: string;
  fields: QmlField[];
  demo: Record<string, number>;
  demoLabel: string;
  rangeNote: string;
  disclaimer: string;
};
export type QmlModel = {
  id: string;
  name: string;
  modality: "ehr" | "genomics" | "imaging";
  workflow: string;
  type:
    | "classical"
    | "quantum_kernel"
    | "quantum_convolutional"
    | "hybrid_qml"
    | "qcnn"
    | "deep_learning";
  family: string;
  research_model: string;
  recommended: boolean;
  limitation: string;
  version: string;
  ready: boolean;
  availability: "runnable" | "evidence_only" | "unavailable" | "configured_not_run";
  performanceTag: "best" | "moderate" | "experimental";
  evidenceMaturity: string;
  endpoint: string;
  metric: QmlEvidenceMetric;
};
export type QmlFeatureContribution = {
  feature: string;
  label: string;
  unit: string;
  inputValue: number | null;
  referenceValue: number;
  modelScoreChange: number;
  scoreAtReference: number;
  direction: "raises_model_score" | "lowers_model_score" | "no_change";
};
export type QmlPrediction = {
  prediction: string;
  predictedClass: number;
  score: number;
  scoreType: string;
  calibratedProbability: number;
  threshold: number;
  inferenceTimeMs: number;
  model: { id: string; name: string; version: string; type: string };
  preprocessingVersion: string;
  researchRunId: string;
  researchSeed: number;
  backend: { type: string; name: string };
  hardwareExecution?: HardwareExecution;
  resources: {
    qubits: number | null;
    shots: number | null;
    circuitDepth: number | null;
    circuitExecutionsThisPrediction?: number;
  };
  inputFeatures: Record<string, number | null>;
  transformedFeatures: Record<string, number>;
  explainability: {
    method: "single_feature_training_median_perturbation";
    scope: "patient_level_model_behaviour";
    reference: string;
    features: QmlFeatureContribution[];
    disclaimer: string;
    executionBackend?: string;
  };
  warnings: string[];
  disclaimer: string;
};
export type QcnnPrediction = {
  model: { id: string; name: string; version: string; type: string };
  prediction: "malignant" | "normal_or_benign";
  predictedClass: number;
  classId: number;
  probabilities: { normal_or_benign: number; malignant: number };
  malignantScore: number;
  scoreType: "sigmoid_model_score_uncalibrated";
  threshold: number;
  measurementExpectationZ: number;
  logit: number;
  inferenceTimeMs: number;
  input: { originalShape: number[]; originalMode: string; processedShape: number[] };
  transformedFeatures: Record<string, number>;
  preprocessing: {
    grayscale: boolean;
    resize: string;
    reduction: string;
    scaling: string;
    versionSha256: string;
  };
  researchRunId: string;
  researchSeed: number;
  backend: { type: string; name: string };
  hardwareExecution?: HardwareExecution;
  quantum: {
    qubits: number;
    stages: number;
    activeQubits: string;
    circuitDepth: number;
    totalGates: number;
    twoQubitGates: number;
    shots: number | null;
    measurement: string;
    circuitExecutionsThisPrediction: number;
  };
  explainability: {
    method: "four_region_midgray_occlusion";
    scope: "patient_level_model_behaviour";
    reference: string;
    regions: Array<{
      id: string;
      row: number;
      column: number;
      modelScoreChange: number;
      scoreWhenOccluded: number;
    }>;
    disclaimer: string;
    executionBackend?: string;
  };
  warnings: string[];
  disclaimer: string;
};

export type HardwareProvider = "ibm" | "qbraid";
export type HardwareExecution = {
  provider: HardwareProvider;
  device: string;
  deviceId: string;
  jobId: string;
  jobIds: string[];
  providerStatus: string;
  shots: number;
  qubits: number;
  circuitCount: number;
  executionTimeMsIncludingQueue: number;
  transpilation: Record<string, unknown>;
  rawHardwareMeasurements: boolean;
  errorMitigationApplied: boolean;
};
export type HardwareJob = {
  jobId: string;
  modelId: string;
  provider: HardwareProvider;
  shots: number;
  status: "queued" | "preparing" | "submitting" | "running" | "completed" | "failed";
  message: string;
  progressPercent: number;
  remoteJobId: string | null;
  remoteJobIds: string[];
  hasResults: boolean;
  error: string | null;
  selectedDevice: null | {
    provider: HardwareProvider;
    deviceId: string;
    name: string;
    qubits: number;
    requiredQubits: number;
    queueDepth: number;
    status: string;
  };
};
export type HardwareCapabilities = {
  simulatorDefault: boolean;
  providers: Record<HardwareProvider, { configured: boolean; realHardwareOnly: boolean }>;
  models: Record<
    string,
    {
      qubits: number;
      circuitCount: number;
      providers: Record<HardwareProvider, { supported: boolean; reason?: string }>;
    }
  >;
  credentialPolicy: string;
};

export type QmlRequest = { modelId: string; features: Record<string, number | null> };
export type QmlReport = {
  reportId: string;
  generatedAt: string;
  prediction: QmlPrediction;
  benchmark: Record<string, unknown>;
  disclaimer: string;
};
export type QmlEvidenceMetric = {
  model: string;
  auroc?: number;
  auprc?: number;
  balanced_accuracy?: number;
  recall_sensitivity?: number;
  sensitivity?: number;
  specificity?: number;
  f1?: number;
  mcc?: number;
  training_time_seconds?: number;
  qubits?: number;
};
export type QmlEvidence = {
  framingham: { summary: QmlEvidenceMetric[]; perSeed: QmlEvidenceMetric[]; limitation: string };
  uci: { models: QmlEvidenceMetric[]; limitation: string };
  qcnn: {
    runs: { runId: string; dataset: string; model: string; metrics: QmlEvidenceMetric }[];
    limitation: string;
  };
};
export type QmlModelEvidence = {
  modelId: string;
  model: QmlModel;
  selectedRun: QmlEvidenceMetric;
  comparisons: QmlEvidence;
  disclaimer: string;
};

export type FhRecord = {
  synthetic: true;
  exampleId: string;
  ageYears: number;
  sexAtBirth: "female" | "male" | "not_specified";
  untreatedLdlCMgDl: number;
  familyHistoryPrematureAscvd: boolean;
  familyHistoryHighLdl: boolean;
  personalHistoryPrematureAscvd: boolean;
  tendonXanthomas: boolean;
  cornealArcusBefore45: boolean;
  secondaryCausesReviewed: boolean;
  variantId: string;
};

export type FhSchema = {
  schemaVersion: number;
  syntheticOnly: true;
  population: string;
  snapshotId: string;
  variantOptions: { id: string; gene: string; classification: string; label: string }[];
  examples: { id: string; label: string; record: FhRecord }[];
  disclaimer: string;
};

export type FhResult = {
  synthetic: true;
  inputQuality: { status: string; secondaryCausesReviewed: boolean };
  evidence: {
    id: string;
    gene: string;
    condition: string;
    classification: string;
    reviewStatus: string;
    snapshotId: string;
    snapshotCreatedAt: string;
    isQualifyingPositive: boolean;
    interpretation: string;
  };
  clinicalSuspicion: {
    method: string;
    score: number;
    category: string;
    breakdown: Record<string, number>;
  };
  referral: { category: string; requiresHumanReview: boolean; message: string };
  researchModels: {
    id: string;
    name: string;
    type: string;
    performanceTag: string;
    probability: number;
    threshold: number;
    metrics: QmlEvidenceMetric;
    resources: Record<string, unknown>;
  }[];
  derivedFeatures: Record<string, number>;
  warnings: string[];
  disclaimer: string;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${QML_API_BASE}${PREFIX}${path}`, { cache: "no-store", ...options });
  } catch {
    throw new Error(
      "QML inference service is unavailable. Start the Python 3.12 service and retry.",
    );
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `QML request failed (${response.status})`);
  return data as T;
}

export const qmlApi = {
  health: () => request<{ status: string; bundleVersion: string }>("/health"),
  models: () => request<{ models: QmlModel[] }>("/models"),
  labModels: (modality?: QmlModel["modality"]) =>
    request<{ models: QmlModel[] }>(`/lab/models${modality ? `?modality=${modality}` : ""}`),
  modalities: () =>
    request<{ modalities: { id: QmlModel["modality"]; name: string; modelCount: number; status: string }[] }>("/lab/modalities"),
  schema: (id: string) => request<QmlSchema>(`/models/${encodeURIComponent(id)}/schema`),
  evidence: () => request<QmlEvidence>("/evidence"),
  modelEvidence: (id: string) =>
    request<QmlModelEvidence>(`/models/${encodeURIComponent(id)}/evidence`),
  hardwareCapabilities: () => request<HardwareCapabilities>("/hardware/capabilities"),
  hardwarePreview: (modelId: string, provider: HardwareProvider) =>
    request<Record<string, unknown>>("/hardware/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ modelId, provider }),
    }),
  hardwareJob: (jobId: string) =>
    request<HardwareJob>(`/hardware/jobs/${encodeURIComponent(jobId)}`),
  hardwareResult: <T>(jobId: string) =>
    request<T>(`/hardware/jobs/${encodeURIComponent(jobId)}/results`),
  submitHardware: (body: QmlRequest, provider: HardwareProvider, shots: number) =>
    request<HardwareJob>("/hardware/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, provider, shots, confirmRealHardware: true }),
    }),
  submitQcnnHardware: (file: File, provider: HardwareProvider, shots: number) =>
    request<HardwareJob>(
      `/hardware/qcnn/breastmnist/jobs?provider=${encodeURIComponent(provider)}&shots=${shots}&confirmRealHardware=true`,
      { method: "POST", headers: { "Content-Type": file.type }, body: file },
    ),
  predict: (body: QmlRequest) =>
    request<QmlPrediction>("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  predictQcnn: (file: File) =>
    request<QcnnPrediction>("/qcnn/breastmnist/predict", {
      method: "POST",
      headers: { "Content-Type": file.type },
      body: file,
    }),
  report: (body: QmlRequest) =>
    request<QmlReport>("/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  fhSchema: () => request<FhSchema>("/lab/genomics/fh/schema"),
  fhAnalyze: (record: FhRecord) =>
    request<FhResult>("/lab/genomics/fh/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ record }),
    }),
};

/** Single-row CSV with quoted fields. It never leaves the browser until prediction. */
export function parseQmlCsv(text: string, expected: string[]): Record<string, number | null> {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;
  const normalized = text.replace(/\r\n/g, "\n").trim();
  for (let i = 0; i < normalized.length; i++) {
    const char = normalized[i];
    if (char === '"') {
      if (quoted && normalized[i + 1] === '"') {
        cell += '"';
        i++;
      } else quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(cell.trim());
      cell = "";
    } else if (char === "\n" && !quoted) {
      row.push(cell.trim());
      rows.push(row);
      row = [];
      cell = "";
    } else cell += char;
  }
  if (quoted) throw new Error("CSV has an unclosed quoted value.");
  row.push(cell.trim());
  rows.push(row);
  if (rows.length !== 2) throw new Error("Upload exactly one data row with a header.");
  const [header, values] = rows;
  if (
    header.length !== expected.length ||
    values.length !== header.length ||
    new Set(header).size !== header.length ||
    expected.some((name) => !header.includes(name))
  ) {
    throw new Error(`CSV must contain exactly these headers: ${expected.join(", ")}`);
  }
  return Object.fromEntries(
    header.map((name, i) => {
      if (values[i] === "") return [name, null];
      const numeric = Number(values[i]);
      if (!Number.isFinite(numeric)) throw new Error(`${name} must be numeric.`);
      return [name, numeric];
    }),
  );
}

export async function waitForHardwareResult<T>(
  jobId: string,
  onStatus?: (job: HardwareJob) => void,
): Promise<T> {
  const deadline = Date.now() + 86_400_000;
  while (Date.now() < deadline) {
    const job = await qmlApi.hardwareJob(jobId);
    onStatus?.(job);
    if (job.status === "failed") throw new Error(job.error || "Hardware execution failed.");
    if (job.status === "completed") return qmlApi.hardwareResult<T>(jobId);
    await new Promise((resolve) => setTimeout(resolve, 3000));
  }
  throw new Error("Hardware job is still pending after the portal polling limit.");
}
