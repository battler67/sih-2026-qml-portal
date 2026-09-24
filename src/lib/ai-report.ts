export type AiReportInterpretations = {
  executive_summary: string;
  dna_interpretation: string;
  circuit_resource_analysis: string;
  noise_mitigation_comparison: string;
  reliability_limitations_conclusion: string;
};

export type AiAnalysisReport = {
  reportId: string;
  jobId: string;
  algorithm: "grover" | "frqi" | "hybrid";
  model: string;
  generatedAt: string;
  measuredFacts: Record<string, unknown>;
  aiInterpretations: AiReportInterpretations;
  disclaimer: string;
};

export type ReportFactRow = {
  category: string;
  label: string;
  value: string;
};

export const AI_REPORT_SECTIONS: Array<{
  key: keyof AiReportInterpretations;
  title: string;
}> = [
  { key: "executive_summary", title: "Executive summary" },
  { key: "dna_interpretation", title: "DNA match / mutation interpretation" },
  { key: "circuit_resource_analysis", title: "Quantum circuit and resource analysis" },
  { key: "noise_mitigation_comparison", title: "Ideal vs noisy vs mitigated comparison" },
  {
    key: "reliability_limitations_conclusion",
    title: "Reliability, limitations, and conclusion",
  },
];

export function reportFactRows(facts: Record<string, unknown>): ReportFactRow[] {
  const rows: ReportFactRow[] = [];
  Object.entries(facts).forEach(([key, value]) => {
    appendFactRows(rows, [key], value);
  });
  return rows;
}

function appendFactRows(rows: ReportFactRow[], path: string[], value: unknown) {
  if (value == null) return;
  if (Array.isArray(value) || shouldKeepObjectTogether(path, value)) {
    rows.push({
      category: humanize(path[0]),
      label: humanize(path.slice(1).join(" ") || path[0]),
      value: formatFactValue(value),
    });
    return;
  }
  if (typeof value === "object") {
    Object.entries(value as Record<string, unknown>).forEach(([key, child]) => {
      appendFactRows(rows, [...path, key], child);
    });
    return;
  }
  rows.push({
    category: humanize(path[0]),
    label: humanize(path.slice(1).join(" ") || path[0]),
    value: formatFactValue(value),
  });
}

function shouldKeepObjectTogether(path: string[], value: unknown) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const last = path.at(-1);
  return last === "values" || last === "noiseParameters";
}

function formatFactValue(value: unknown) {
  if (typeof value === "number") {
    return Number.isInteger(value) ? value.toLocaleString() : String(value);
  }
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "string") return value || "Not provided";
  return JSON.stringify(value);
}

function humanize(value: string) {
  const text = value
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "Value";
}
