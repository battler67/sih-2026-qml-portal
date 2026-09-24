export type MutationClass = "transition" | "transversion";

export type ClassicalMutation = {
  positionZeroBased: number;
  positionOneBased: number;
  referenceBase: string;
  alternateBase: string;
  substitution: string;
  mutationClass: MutationClass;
  referenceContext: string;
  queryContext: string;
};

export type MutationSpectrumEntry = {
  substitution: string;
  count: number;
};

export type HybridMutationAnalysis = {
  sequenceLength: number;
  mutationCount: number;
  mutationRate: number;
  transitionCount: number;
  transversionCount: number;
  transitionTransversionRatio: number | null;
  mutations: ClassicalMutation[];
  spectrum: MutationSpectrumEntry[];
};

const SUBSTITUTIONS = [
  "A>C",
  "A>G",
  "A>T",
  "C>A",
  "C>G",
  "C>T",
  "G>A",
  "G>C",
  "G>T",
  "T>A",
  "T>C",
  "T>G",
] as const;

const TRANSITIONS = new Set(["A>G", "G>A", "C>T", "T>C"]);

function normalizedSequence(value: string): string {
  return value.replace(/\s/g, "").toUpperCase();
}

function sequenceContext(sequence: string, position: number, flankSize: number): string {
  const start = Math.max(0, position - flankSize);
  const end = Math.min(sequence.length, position + flankSize + 1);
  return `${sequence.slice(start, position)}[${sequence[position]}]${sequence.slice(
    position + 1,
    end,
  )}`;
}

export function classifySubstitution(referenceBase: string, alternateBase: string): MutationClass {
  return TRANSITIONS.has(`${referenceBase}>${alternateBase}`) ? "transition" : "transversion";
}

export function analyzeHybridMutations(
  referenceInput: string,
  queryInput: string,
  flankSize = 2,
): HybridMutationAnalysis {
  const reference = normalizedSequence(referenceInput);
  const query = normalizedSequence(queryInput);

  if (reference.length !== query.length) {
    throw new Error("Hybrid mutation analysis requires equal-length sequences");
  }
  if (!/^[ACGT]*$/.test(reference) || !/^[ACGT]*$/.test(query)) {
    throw new Error("Hybrid mutation analysis supports A, C, G, and T only");
  }
  if (!Number.isInteger(flankSize) || flankSize < 0) {
    throw new Error("Sequence-context flank size must be a non-negative integer");
  }

  const mutations: ClassicalMutation[] = [];
  const spectrumCounts = new Map<string, number>(SUBSTITUTIONS.map((key) => [key, 0]));

  for (let position = 0; position < reference.length; position += 1) {
    const referenceBase = reference[position];
    const alternateBase = query[position];
    if (referenceBase === alternateBase) continue;

    const substitution = `${referenceBase}>${alternateBase}`;
    const mutationClass = classifySubstitution(referenceBase, alternateBase);
    spectrumCounts.set(substitution, (spectrumCounts.get(substitution) ?? 0) + 1);
    mutations.push({
      positionZeroBased: position,
      positionOneBased: position + 1,
      referenceBase,
      alternateBase,
      substitution,
      mutationClass,
      referenceContext: sequenceContext(reference, position, flankSize),
      queryContext: sequenceContext(query, position, flankSize),
    });
  }

  const transitionCount = mutations.filter(
    (mutation) => mutation.mutationClass === "transition",
  ).length;
  const transversionCount = mutations.length - transitionCount;

  return {
    sequenceLength: reference.length,
    mutationCount: mutations.length,
    mutationRate: reference.length > 0 ? mutations.length / reference.length : 0,
    transitionCount,
    transversionCount,
    transitionTransversionRatio: transversionCount > 0 ? transitionCount / transversionCount : null,
    mutations,
    spectrum: SUBSTITUTIONS.map((substitution) => ({
      substitution,
      count: spectrumCounts.get(substitution) ?? 0,
    })),
  };
}
