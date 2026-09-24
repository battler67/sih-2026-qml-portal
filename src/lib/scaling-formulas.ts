export type ScalingMode = "frqi" | "grover" | "hybrid";

export type ScalingInputs = {
  mode: ScalingMode;
  referenceLength: number;
  queryLength: number;
  markedCount: number;
  averageGateDurationNs: number;
};

export type ScalingAssumptions = {
  classicalComparisonDurationNs: number;
  fixedPointDelta: number;
  hybridPredicateGatesPerQuery: number;
};

export type ScalingFormulaSet = {
  candidateSpace(referenceLength: number, queryLength: number): number;
  idealAmplitudeQueries(searchSpace: number, markedCount: number): number | null;
  frqiComparisonQueries(sequenceLength: number): number;
  groverGatesPerQuery(queryLength: number, searchSpace: number): number;
  hybridGatesPerQuery(sequenceLength: number): number;
  classicalOperations(mode: ScalingMode, referenceLength: number, queryLength: number): number;
};

export type ScalingComparison = {
  valid: boolean;
  errors: string[];
  mode: ScalingMode;
  referenceLength: number;
  queryLength: number;
  markedCount: number;
  searchSpace: number;
  classicalOperations: number;
  classicalBestCaseOperations: number;
  idealQuantumQueries: number | null;
  fixedPointPredicateQueries: number | null;
  gatesPerQuery: number;
  projectedSearchStageGateCount: number | null;
  projectedClassicalTimeNs: number;
  projectedQuantumTimeNs: number | null;
  classicalComplexity: string;
  quantumComplexity: string;
  quantumBestCaseComplexity: string;
  projectionNote: string;
};

export type ScalingChartPoint = {
  length: number;
  classical: number;
  quantum: number | null;
  fixedPoint?: number;
};

export const DEFAULT_SCALING_ASSUMPTIONS: ScalingAssumptions = {
  classicalComparisonDurationNs: 1,
  fixedPointDelta: 0.2,
  // One target-query model: mismatch compute (7), phase (1), and uncompute (7).
  // This is a high-level search-stage count, not a transpiled hardware gate count.
  hybridPredicateGatesPerQuery: 15,
};

export const DEFAULT_SCALING_FORMULAS: ScalingFormulaSet = {
  candidateSpace(referenceLength, queryLength) {
    return Math.max(0, referenceLength - queryLength + 1);
  },
  idealAmplitudeQueries(searchSpace, markedCount) {
    if (searchSpace < 1 || markedCount < 1) return null;
    const boundedMarkedCount = Math.min(searchSpace, markedCount);
    return Math.max(1, Math.ceil((Math.PI / 4) * Math.sqrt(searchSpace / boundedMarkedCount)));
  },
  frqiComparisonQueries(sequenceLength) {
    return sequenceLength > 0 ? 1 : 0;
  },
  groverGatesPerQuery(queryLength, searchSpace) {
    const indexQubits = Math.max(1, Math.ceil(Math.log2(Math.max(1, searchSpace))));
    // Replaceable unit-cost model: pattern checks plus index reflection work.
    return Math.max(1, queryLength + 2 * indexQubits);
  },
  hybridGatesPerQuery() {
    return DEFAULT_SCALING_ASSUMPTIONS.hybridPredicateGatesPerQuery;
  },
  classicalOperations(mode, referenceLength, queryLength) {
    if (mode !== "grover") return referenceLength;
    return Math.max(0, referenceLength - queryLength + 1) * queryLength;
  },
};

function positiveInteger(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.floor(value));
}

function positiveNumber(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, value);
}

function fixedPointPredicateQueries(sequenceLength: number, delta: number): number | null {
  if (sequenceLength < 1 || !(delta > 0 && delta < 1)) return null;
  const lambdaMin = 1 / sequenceLength;
  let scheduleLength = 1;
  while (scheduleLength < 100_001) {
    const gamma = 1 / Math.cosh(Math.acosh(1 / delta) / scheduleLength);
    const width = 1 - gamma * gamma;
    if (width <= lambdaMin + 1e-15) return scheduleLength - 1;
    scheduleLength += 2;
  }
  return null;
}

export function calculateScalingComparison(
  rawInputs: ScalingInputs,
  formulas: ScalingFormulaSet = DEFAULT_SCALING_FORMULAS,
  assumptions: ScalingAssumptions = DEFAULT_SCALING_ASSUMPTIONS,
): ScalingComparison {
  const referenceLength = positiveInteger(rawInputs.referenceLength);
  const queryLength = positiveInteger(rawInputs.queryLength);
  const markedCount = positiveInteger(rawInputs.markedCount);
  const averageGateDurationNs = positiveNumber(rawInputs.averageGateDurationNs);
  const errors: string[] = [];

  if (referenceLength < 1) errors.push("Reference length must be at least 1.");
  if (queryLength < 1) errors.push("Query length must be at least 1.");
  if (rawInputs.mode !== "grover" && referenceLength !== queryLength) {
    errors.push(
      `${rawInputs.mode === "hybrid" ? "Hybrid Mutation Mode" : "FRQI"} requires equal reference and query lengths.`,
    );
  }
  if (rawInputs.mode === "grover" && queryLength > referenceLength) {
    errors.push("Grover query length cannot exceed the reference length.");
  }

  const searchSpace =
    rawInputs.mode !== "grover"
      ? referenceLength
      : formulas.candidateSpace(referenceLength, queryLength);
  if (markedCount > searchSpace) {
    errors.push(`Marked count cannot exceed the ${searchSpace}-item search space.`);
  }
  if (averageGateDurationNs <= 0) {
    errors.push("Average gate duration must be greater than zero.");
  }

  const classicalOperations = formulas.classicalOperations(
    rawInputs.mode,
    referenceLength,
    queryLength,
  );
  const idealQuantumQueries =
    rawInputs.mode === "frqi"
      ? formulas.frqiComparisonQueries(referenceLength)
      : formulas.idealAmplitudeQueries(searchSpace, markedCount);
  const ylcPredicateQueries =
    rawInputs.mode === "hybrid"
      ? fixedPointPredicateQueries(referenceLength, assumptions.fixedPointDelta)
      : null;
  const queryCountForProjection =
    rawInputs.mode === "hybrid" ? ylcPredicateQueries : idealQuantumQueries;
  const gatesPerQuery =
    rawInputs.mode === "hybrid"
      ? formulas.hybridGatesPerQuery(referenceLength)
      : rawInputs.mode === "grover"
        ? formulas.groverGatesPerQuery(queryLength, searchSpace)
        : 1;
  const projectedSearchStageGateCount =
    queryCountForProjection == null ? null : queryCountForProjection * gatesPerQuery;

  return {
    valid: errors.length === 0,
    errors,
    mode: rawInputs.mode,
    referenceLength,
    queryLength,
    markedCount,
    searchSpace,
    classicalOperations,
    classicalBestCaseOperations: rawInputs.mode === "grover" ? queryLength : referenceLength,
    idealQuantumQueries,
    fixedPointPredicateQueries: ylcPredicateQueries,
    gatesPerQuery,
    projectedSearchStageGateCount,
    projectedClassicalTimeNs: classicalOperations * assumptions.classicalComparisonDurationNs,
    projectedQuantumTimeNs:
      projectedSearchStageGateCount == null
        ? null
        : projectedSearchStageGateCount * averageGateDurationNs,
    classicalComplexity: rawInputs.mode === "grover" ? "Θ((N − m + 1) · m)" : "Θ(N)",
    quantumComplexity:
      rawInputs.mode === "hybrid"
        ? "O(√(N / M)) ideal query reference; implemented YLC uses λmin = 1/N"
        : rawInputs.mode === "grover"
          ? "O(√((N − m + 1) / K)) oracle queries"
          : "O(1) strip-interference comparison after state preparation",
    quantumBestCaseComplexity:
      rawInputs.mode === "frqi"
        ? "O(1) comparison-stage strip operation after equal-length states are prepared"
        : markedCount === searchSpace && searchSpace > 0
          ? "O(1) oracle queries when every candidate is marked"
          : rawInputs.mode === "hybrid"
            ? "O(√(N / M)) ideal marked-position query complexity"
            : "O(√((N − m + 1) / K)) oracle queries; O(1) when K = S",
    projectionNote:
      "Projected search-stage model only. It is not Qiskit simulation time or measured hardware time.",
  };
}

export function buildScalingChartData(
  inputs: ScalingInputs,
  formulas: ScalingFormulaSet = DEFAULT_SCALING_FORMULAS,
  assumptions: ScalingAssumptions = DEFAULT_SCALING_ASSUMPTIONS,
): ScalingChartPoint[] {
  const upperLength = Math.max(4, positiveInteger(inputs.referenceLength));
  const sampleCount = Math.min(10, upperLength);
  const lengths = Array.from(
    new Set(
      Array.from({ length: sampleCount }, (_, index) =>
        Math.max(1, Math.round(1 + ((upperLength - 1) * index) / (sampleCount - 1))),
      ),
    ),
  );

  return lengths.map((length) => {
    const queryLength =
      inputs.mode === "grover" ? Math.min(Math.max(1, inputs.queryLength), length) : length;
    const searchSpace =
      inputs.mode === "grover" ? formulas.candidateSpace(length, queryLength) : length;
    const markedCount = Math.min(Math.max(1, inputs.markedCount), Math.max(1, searchSpace));
    const comparison = calculateScalingComparison(
      {
        ...inputs,
        referenceLength: length,
        queryLength,
        markedCount,
      },
      formulas,
      assumptions,
    );
    return {
      length,
      classical: comparison.classicalOperations,
      quantum: comparison.idealQuantumQueries,
      ...(comparison.fixedPointPredicateQueries == null
        ? {}
        : { fixedPoint: comparison.fixedPointPredicateQueries }),
    };
  });
}
