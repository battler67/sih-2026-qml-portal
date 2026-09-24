import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, BarChart3 } from "lucide-react";

import { ScalingComparisonCard } from "@/components/ScalingComparisonCard";
import { ScalingComparisonChart } from "@/components/ScalingComparisonChart";
import { Input } from "@/components/ui/input";
import {
  buildScalingChartData,
  calculateScalingComparison,
  type ScalingMode,
} from "@/lib/scaling-formulas";

type ClassicalQuantumScalingProps = {
  mode: ScalingMode;
  referenceLength: number;
  queryLength: number;
  markedCount: number;
};

const MODE_OPTIONS: Array<{ value: ScalingMode; label: string }> = [
  { value: "frqi", label: "FRQI Similarity" },
  { value: "grover", label: "Grover DNA Search" },
  { value: "hybrid", label: "Hybrid Mutation" },
];

function numericInput(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function ClassicalQuantumScaling({
  mode,
  referenceLength,
  queryLength,
  markedCount,
}: ClassicalQuantumScalingProps) {
  const [selectedMode, setSelectedMode] = useState<ScalingMode>(mode);
  const [referenceN, setReferenceN] = useState(Math.max(1, referenceLength));
  const [queryN, setQueryN] = useState(Math.max(1, queryLength));
  const [markedM, setMarkedM] = useState(Math.max(0, markedCount));

  useEffect(() => {
    setSelectedMode(mode);
  }, [mode]);

  useEffect(() => {
    setReferenceN(Math.max(1, referenceLength));
  }, [referenceLength]);

  useEffect(() => {
    setQueryN(Math.max(1, queryLength));
  }, [queryLength]);

  useEffect(() => {
    setMarkedM(Math.max(0, markedCount));
  }, [markedCount]);

  const inputs = useMemo(
    () => ({
      mode: selectedMode,
      referenceLength: referenceN,
      queryLength: queryN,
      markedCount: markedM,
      // Retained only for the reusable formula API; projected time is not shown.
      averageGateDurationNs: 100,
    }),
    [markedM, queryN, referenceN, selectedMode],
  );
  const comparison = useMemo(() => calculateScalingComparison(inputs), [inputs]);
  const chartData = useMemo(() => buildScalingChartData(inputs), [inputs]);
  const isHybrid = selectedMode === "hybrid";
  const isGrover = selectedMode === "grover";
  const markedLabel = isHybrid
    ? "Mutations M"
    : isGrover
      ? "Exact matches K"
      : "Different positions K";

  const modeDescription = isHybrid
    ? "Equal-length mutation-position query complexity with the implemented fixed-point schedule."
    : isGrover
      ? "Exact DNA pattern-search complexity over valid candidate positions."
      : "Equal-length FRQI strip-comparison complexity after sequence-state preparation.";

  return (
    <section className="glass rounded-2xl p-5 sm:p-6">
      <div className="flex gap-3">
        <div className="rounded-xl border border-emerald/20 bg-emerald/10 p-2.5">
          <BarChart3 className="h-5 w-5 text-emerald" />
        </div>
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-emerald">
            Complexity comparison
          </div>
          <h2 className="mt-1 font-display text-xl font-semibold">Classical vs Quantum Scaling</h2>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{modeDescription}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <label className="rounded-xl border border-white/10 bg-black/30 p-3">
          <span className="text-xs font-medium text-foreground">Algorithm</span>
          <select
            value={selectedMode}
            onChange={(event) => setSelectedMode(event.target.value as ScalingMode)}
            className="theme-select mt-2 h-10 w-full rounded-md border border-white/10 bg-black/30 px-3 text-sm focus:border-emerald/40 focus:outline-none"
          >
            {MODE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <span className="mt-1 block text-[11px] text-muted-foreground">
            Select one of the three portal modes
          </span>
        </label>
        <ScalingField
          label="Reference length N"
          value={referenceN}
          min={1}
          onChange={setReferenceN}
          detail={isGrover ? "Target DNA length" : "Must equal query length"}
        />
        <ScalingField
          label="Query length m"
          value={queryN}
          min={1}
          onChange={setQueryN}
          detail={isGrover ? "Exact pattern length" : "Equal comparison length"}
        />
        <ScalingField
          label={markedLabel}
          value={markedM}
          min={0}
          max={Math.max(0, comparison.searchSpace)}
          onChange={setMarkedM}
          detail={
            isHybrid
              ? "Marked substitution positions"
              : isGrover
                ? "Marked exact-match candidates"
                : "Input difference count; FRQI score remains angle weighted"
          }
        />
      </div>

      {comparison.errors.length > 0 && (
        <div className="mt-4 rounded-xl border border-amber-400/30 bg-amber-400/10 p-3 text-xs text-amber-100">
          <div className="flex gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{comparison.errors.join(" ")}</span>
          </div>
        </div>
      )}

      <div className="mt-5 grid gap-4 md:grid-cols-3">
        <ScalingComparisonCard
          eyebrow="Classical"
          title={isGrover ? "Exhaustive character work" : "Character comparisons"}
          value={comparison.classicalOperations.toLocaleString()}
          formula={
            isGrover ? `S = N - m + 1; C = S * m (${comparison.searchSpace} candidates)` : "C = N"
          }
          description={
            isGrover
              ? `Direct exhaustive complexity ${comparison.classicalComplexity}; best case Theta(m).`
              : `Equal-length direct comparison complexity ${comparison.classicalComplexity}.`
          }
          accent="amber"
        />
        <ScalingComparisonCard
          eyebrow="Quantum"
          title={
            isHybrid
              ? "Ideal marked-position queries"
              : isGrover
                ? "Grover oracle queries"
                : "FRQI comparison-stage query"
          }
          value={
            comparison.idealQuantumQueries == null
              ? "No marked item"
              : comparison.idealQuantumQueries.toLocaleString()
          }
          formula={
            isHybrid
              ? "Q* = ceil((pi/4) sqrt(N/M))"
              : isGrover
                ? "Q = ceil((pi/4) sqrt((N-m+1)/K))"
                : "Qcompare = 1 after state preparation"
          }
          description={comparison.quantumBestCaseComplexity}
          accent="cyan"
        />
        <ScalingComparisonCard
          eyebrow={isHybrid ? "Implemented Hybrid" : "Complexity summary"}
          title={isHybrid ? "YLC predicate queries" : "Classical / quantum"}
          value={
            isHybrid
              ? (comparison.fixedPointPredicateQueries?.toLocaleString() ?? "Unavailable")
              : `${comparison.classicalComplexity} / ${comparison.quantumComplexity}`
          }
          valueClassName={isHybrid ? "text-2xl" : "text-base leading-snug sm:text-lg"}
          formula={
            isHybrid
              ? "lambda_min = 1/N; QYLC = L - 1"
              : isGrover
                ? "Classical Theta(S*m), quantum O(sqrt(S/K)) queries"
                : "Classical Theta(N), FRQI comparison stage O(1)"
          }
          description={
            isHybrid
              ? "The unknown-M fixed-point schedule uses the lower bound 1/N, not the actual mutation count."
              : "The graph recomputes immediately when algorithm, N, m, or K changes."
          }
        />
      </div>

      <div className="mt-5">
        <ScalingComparisonChart data={chartData} mode={selectedMode} />
      </div>
    </section>
  );
}

function ScalingField({
  label,
  value,
  min,
  max,
  detail,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max?: number;
  detail: string;
  onChange(value: number): void;
}) {
  return (
    <label className="rounded-xl border border-white/10 bg-black/30 p-3">
      <span className="text-xs font-medium text-foreground">{label}</span>
      <Input
        type="number"
        value={value}
        min={min}
        max={max}
        step={1}
        onChange={(event) => onChange(numericInput(event.target.value))}
        className="mt-2 border-white/10 bg-black/30 font-mono"
      />
      <span className="mt-1 block text-[11px] text-muted-foreground">{detail}</span>
    </label>
  );
}
