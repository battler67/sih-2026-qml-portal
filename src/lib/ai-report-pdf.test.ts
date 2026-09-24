import { describe, expect, test } from "bun:test";
import { buildAiReportPdf } from "./ai-report-pdf";
import type { AiAnalysisReport } from "./ai-report";

const report: AiAnalysisReport = {
  reportId: "abc",
  jobId: "job-1",
  algorithm: "hybrid",
  model: "gpt-test",
  generatedAt: "2026-07-30T00:00:00Z",
  measuredFacts: {
    algorithm: "hybrid",
    measuredMismatchCandidatePositionsZeroBased: [1, 3],
    ylcIterations: 2,
  },
  aiInterpretations: {
    executive_summary: "A bounded simulator result was analyzed.",
    dna_interpretation: "Positions 1 and 3 are measured candidates.",
    circuit_resource_analysis: "The supplied resource values bound this interpretation.",
    noise_mitigation_comparison: "No noise comparison was available.",
    reliability_limitations_conclusion: "This is not a medical conclusion.",
  },
  disclaimer: "Research use only.",
};

describe("AI report PDF", () => {
  test("creates a downloadable PDF containing facts and interpretation sections", async () => {
    const blob = buildAiReportPdf(report);
    const text = await blob.text();

    expect(blob.type).toBe("application/pdf");
    expect(text.startsWith("%PDF-1.4")).toBe(true);
    expect(text).toContain("MEASURED FACTS");
    expect(text).toContain("AI INTERPRETATIONS");
    expect(text).toContain("EXECUTIVE SUMMARY");
    expect(text).toContain("startxref");
  });
});
