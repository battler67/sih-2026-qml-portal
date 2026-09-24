import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ScalingChartPoint, ScalingMode } from "@/lib/scaling-formulas";

export function ScalingComparisonChart({
  data,
  mode,
}: {
  data: ScalingChartPoint[];
  mode: ScalingMode;
}) {
  return (
    <div className="h-80 rounded-xl border border-white/10 bg-black/30 p-4">
      <div className="text-xs uppercase tracking-widest text-emerald">Query-complexity model</div>
      <div className="mt-3 h-60">
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 28, left: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              dataKey="length"
              tick={{ fill: "#94a3b8", fontSize: 10 }}
              label={{
                value: mode === "grover" ? "Reference length N" : "Equal sequence length N",
                position: "insideBottom",
                offset: -18,
                fill: "#94a3b8",
                fontSize: 10,
              }}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fill: "#94a3b8", fontSize: 10 }}
              label={{
                value: "Modeled count",
                angle: -90,
                position: "insideLeft",
                fill: "#94a3b8",
                fontSize: 10,
              }}
            />
            <Tooltip
              contentStyle={{
                background: "#0b1a15",
                border: "1px solid rgba(16,185,129,0.3)",
                borderRadius: 12,
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 10 }} />
            <Line
              type="monotone"
              dataKey="classical"
              name="Classical operations"
              stroke="#fbbf24"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="quantum"
              name="Ideal quantum queries"
              stroke="#22d3ee"
              strokeWidth={2}
              connectNulls={false}
            />
            {mode === "hybrid" && (
              <Line
                type="monotone"
                dataKey="fixedPoint"
                name="Implemented YLC predicate queries"
                stroke="#10B981"
                strokeWidth={2}
                dot={false}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
