import { describe, expect, test } from "bun:test";

import {
  DEFAULT_SCALING_ASSUMPTIONS,
  DEFAULT_SCALING_FORMULAS,
  buildScalingChartData,
  calculateScalingComparison,
} from "./scaling-formulas";

describe("classical versus quantum scaling formulas", () => {
  test("Hybrid N=4, M=1 keeps the classical scan linear", () => {
    const result = calculateScalingComparison({
      mode: "hybrid",
      referenceLength: 4,
      queryLength: 4,
      markedCount: 1,
      averageGateDurationNs: 100,
    });

    expect(result.valid).toBe(true);
    expect(result.classicalOperations).toBe(4);
    expect(result.idealQuantumQueries).toBe(2);
    expect(result.fixedPointPredicateQueries).toBeGreaterThan(0);
    expect(result.projectedQuantumTimeNs).toBe(result.projectedSearchStageGateCount! * 100);
  });

  test("more marked Hybrid positions reduce the ideal known-M query reference", () => {
    const oneMutation = calculateScalingComparison({
      mode: "hybrid",
      referenceLength: 32,
      queryLength: 32,
      markedCount: 1,
      averageGateDurationNs: 100,
    });
    const eightMutations = calculateScalingComparison({
      mode: "hybrid",
      referenceLength: 32,
      queryLength: 32,
      markedCount: 8,
      averageGateDurationNs: 100,
    });

    expect(eightMutations.idealQuantumQueries!).toBeLessThan(oneMutation.idealQuantumQueries!);
    expect(eightMutations.fixedPointPredicateQueries).toBe(oneMutation.fixedPointPredicateQueries);
  });

  test("Hybrid rejects unequal lengths and impossible M", () => {
    const result = calculateScalingComparison({
      mode: "hybrid",
      referenceLength: 8,
      queryLength: 7,
      markedCount: 9,
      averageGateDurationNs: 100,
    });

    expect(result.valid).toBe(false);
    expect(result.errors.join(" ")).toContain("equal");
    expect(result.errors.join(" ")).toContain("cannot exceed");
  });

  test("Grover uses the valid candidate-position search space", () => {
    const result = calculateScalingComparison({
      mode: "grover",
      referenceLength: 20,
      queryLength: 5,
      markedCount: 1,
      averageGateDurationNs: 100,
    });

    expect(result.valid).toBe(true);
    expect(result.searchSpace).toBe(16);
    expect(result.classicalOperations).toBe(80);
    expect(result.classicalBestCaseOperations).toBe(5);
    expect(result.idealQuantumQueries).toBe(4);
  });

  test("Grover best case becomes constant when every candidate is marked", () => {
    const result = calculateScalingComparison({
      mode: "grover",
      referenceLength: 8,
      queryLength: 3,
      markedCount: 6,
      averageGateDurationNs: 100,
    });

    expect(result.searchSpace).toBe(6);
    expect(result.idealQuantumQueries).toBe(1);
    expect(result.quantumBestCaseComplexity).toContain("O(1)");
  });

  test("FRQI shows linear classical work and one prepared-state comparison query", () => {
    const result = calculateScalingComparison({
      mode: "frqi",
      referenceLength: 8,
      queryLength: 8,
      markedCount: 2,
      averageGateDurationNs: 100,
    });

    expect(result.valid).toBe(true);
    expect(result.classicalOperations).toBe(8);
    expect(result.idealQuantumQueries).toBe(1);
    expect(result.quantumComplexity).toContain("O(1)");
  });

  test("zero marked items never fabricates a quantum time", () => {
    const result = calculateScalingComparison({
      mode: "grover",
      referenceLength: 20,
      queryLength: 5,
      markedCount: 0,
      averageGateDurationNs: 100,
    });

    expect(result.idealQuantumQueries).toBeNull();
    expect(result.projectedSearchStageGateCount).toBeNull();
    expect(result.projectedQuantumTimeNs).toBeNull();
  });

  test("formula set can be replaced without changing consumers", () => {
    const result = calculateScalingComparison(
      {
        mode: "hybrid",
        referenceLength: 8,
        queryLength: 8,
        markedCount: 2,
        averageGateDurationNs: 5,
      },
      {
        ...DEFAULT_SCALING_FORMULAS,
        hybridGatesPerQuery: () => 3,
      },
      {
        ...DEFAULT_SCALING_ASSUMPTIONS,
        classicalComparisonDurationNs: 2,
      },
    );

    expect(result.gatesPerQuery).toBe(3);
    expect(result.projectedClassicalTimeNs).toBe(16);
  });

  test("chart responds to different N and M values", () => {
    const short = buildScalingChartData({
      mode: "hybrid",
      referenceLength: 8,
      queryLength: 8,
      markedCount: 1,
      averageGateDurationNs: 100,
    });
    const long = buildScalingChartData({
      mode: "hybrid",
      referenceLength: 32,
      queryLength: 32,
      markedCount: 4,
      averageGateDurationNs: 100,
    });

    expect(short.at(-1)?.length).toBe(8);
    expect(long.at(-1)?.length).toBe(32);
    expect(long.at(-1)?.classical).toBe(32);
  });
});
