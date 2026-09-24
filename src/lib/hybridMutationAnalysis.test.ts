import { describe, expect, test } from "bun:test";
import { analyzeHybridMutations, classifySubstitution } from "./hybridMutationAnalysis";

describe("Hybrid classical mutation analysis", () => {
  test("classifies transitions and transversions", () => {
    expect(classifySubstitution("A", "G")).toBe("transition");
    expect(classifySubstitution("C", "T")).toBe("transition");
    expect(classifySubstitution("A", "C")).toBe("transversion");
    expect(classifySubstitution("G", "T")).toBe("transversion");
  });

  test("derives identities, coordinates, contexts, rate, and spectrum", () => {
    const analysis = analyzeHybridMutations("ACGTACGT", "ATGTACAT");

    expect(analysis.sequenceLength).toBe(8);
    expect(analysis.mutationCount).toBe(2);
    expect(analysis.mutationRate).toBe(0.25);
    expect(analysis.mutations).toEqual([
      {
        positionZeroBased: 1,
        positionOneBased: 2,
        referenceBase: "C",
        alternateBase: "T",
        substitution: "C>T",
        mutationClass: "transition",
        referenceContext: "A[C]GT",
        queryContext: "A[T]GT",
      },
      {
        positionZeroBased: 6,
        positionOneBased: 7,
        referenceBase: "G",
        alternateBase: "A",
        substitution: "G>A",
        mutationClass: "transition",
        referenceContext: "AC[G]T",
        queryContext: "AC[A]T",
      },
    ]);
    expect(analysis.transitionCount).toBe(2);
    expect(analysis.transversionCount).toBe(0);
    expect(analysis.transitionTransversionRatio).toBeNull();
    expect(analysis.spectrum.find((entry) => entry.substitution === "C>T")?.count).toBe(1);
    expect(analysis.spectrum.find((entry) => entry.substitution === "G>A")?.count).toBe(1);
  });

  test("reports an all-match comparison without mutations", () => {
    const analysis = analyzeHybridMutations("ACGT", "ACGT");

    expect(analysis.mutations).toEqual([]);
    expect(analysis.mutationRate).toBe(0);
    expect(analysis.transitionCount).toBe(0);
    expect(analysis.transversionCount).toBe(0);
    expect(analysis.spectrum.every((entry) => entry.count === 0)).toBe(true);
  });

  test("rejects unequal lengths and unsupported bases", () => {
    expect(() => analyzeHybridMutations("ACGT", "ACG")).toThrow("equal-length");
    expect(() => analyzeHybridMutations("ACNT", "ACGT")).toThrow("A, C, G, and T");
  });
});
