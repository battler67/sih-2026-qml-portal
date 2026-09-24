import type { ReactNode } from "react";

type ScalingComparisonCardProps = {
  eyebrow: string;
  title: string;
  value: ReactNode;
  formula: string;
  description: string;
  accent?: "emerald" | "cyan" | "amber";
  valueClassName?: string;
};

const accentClasses = {
  emerald: "border-emerald/20 bg-emerald/5 text-emerald",
  cyan: "border-cyan-glow/20 bg-cyan-glow/5 text-cyan-glow",
  amber: "border-amber-400/20 bg-amber-400/5 text-amber-300",
} as const;

export function ScalingComparisonCard({
  eyebrow,
  title,
  value,
  formula,
  description,
  accent = "emerald",
  valueClassName = "text-2xl",
}: ScalingComparisonCardProps) {
  return (
    <article className={`rounded-xl border p-4 ${accentClasses[accent]}`}>
      <div className="text-[10px] uppercase tracking-[0.2em] opacity-80">{eyebrow}</div>
      <h3 className="mt-1 text-sm font-medium text-foreground">{title}</h3>
      <div className={`mt-3 break-words font-display font-semibold ${valueClassName}`}>{value}</div>
      <div className="mt-2 rounded-md bg-black/20 px-2 py-1 font-mono text-[11px]">{formula}</div>
      <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{description}</p>
    </article>
  );
}
