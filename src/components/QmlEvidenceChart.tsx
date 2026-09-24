import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Row = { model: string; AUROC?: number; AUPRC?: number; "Balanced accuracy"?: number };

export default function QmlEvidenceChart({ data }: { data: Row[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} layout="vertical" margin={{ left: 35, right: 10 }}>
        <CartesianGrid stroke="rgba(255,255,255,.07)" horizontal={false} />
        <XAxis type="number" domain={[0, 1]} tick={{ fill: "#a7b8b0", fontSize: 11 }} />
        <YAxis
          type="category"
          dataKey="model"
          width={140}
          tick={{ fill: "#a7b8b0", fontSize: 11 }}
        />
        <Tooltip
          contentStyle={{ background: "#102019", border: "1px solid #285342", borderRadius: 12 }}
        />
        <Bar dataKey="AUROC" fill="#10B981" radius={[0, 4, 4, 0]} />
        <Bar dataKey="AUPRC" fill="#38bdf8" radius={[0, 4, 4, 0]} />
        <Bar dataKey="Balanced accuracy" fill="#84cc16" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
