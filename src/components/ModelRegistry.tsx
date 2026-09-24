import { useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Atom, Cpu, Image as ImageIcon, Loader2, Play, ShieldQuestion } from "lucide-react";
import { qmlApi, type QmlModel } from "@/lib/qml-api";

const tagStyles: Record<QmlModel["performanceTag"], string> = {
  best: "border-emerald/35 bg-emerald/10 text-emerald",
  moderate: "border-cyan-glow/30 bg-cyan-glow/10 text-cyan-glow",
  experimental: "border-amber-300/30 bg-amber-300/10 text-amber-200",
};

function format(value?: number) {
  return value == null ? "—" : value.toFixed(3);
}

const availabilityLabels: Record<QmlModel["availability"], string> = {
  runnable: "Runnable",
  evidence_only: "Evidence only",
  configured_not_run: "Configured, not run",
  unavailable: "Unavailable",
};

function ModelIcon({ model }: { model: QmlModel }) {
  if (model.modality === "imaging") return <ImageIcon size={17} />;
  if (["quantum_kernel", "hybrid_qml", "qcnn"].includes(model.family)) return <Atom size={17} />;
  return <Cpu size={17} />;
}

export function ModelRegistry({ compact = false }: { compact?: boolean }) {
  const [models, setModels] = useState<QmlModel[]>([]);
  const [modality, setModality] = useState<"all" | QmlModel["modality"]>("all");
  const [tag, setTag] = useState<"all" | QmlModel["performanceTag"]>("all");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    qmlApi
      .labModels()
      .then((result) => active && setModels(result.models))
      .catch((reason) => active && setError(reason.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  const visible = useMemo(
    () =>
      models.filter(
        (model) =>
          (modality === "all" || model.modality === modality) &&
          (tag === "all" || model.performanceTag === tag),
      ),
    [models, modality, tag],
  );

  if (loading) {
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 size={16} className="animate-spin" /> Loading model registry…
      </p>
    );
  }
  if (error) {
    return (
      <p role="alert" className="text-sm text-red-200">
        {error}
      </p>
    );
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2" aria-label="Filter models by modality">
          {(["all", "ehr", "genomics", "imaging"] as const).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setModality(value)}
              className={`rounded-full border px-3 py-1.5 text-sm transition ${modality === value ? "border-emerald/50 bg-emerald/10 text-emerald" : "border-white/10 text-muted-foreground hover:bg-white/5"}`}
            >
              {value === "all"
                ? "All modalities"
                : value === "ehr"
                  ? "EHR"
                  : value[0].toUpperCase() + value.slice(1)}
            </button>
          ))}
        </div>
        <select
          value={tag}
          onChange={(event) => setTag(event.target.value as typeof tag)}
          className="theme-select rounded-xl border border-white/15 px-3 py-2 text-sm"
          aria-label="Filter models by performance tag"
        >
          <option value="all">All performance tags</option>
          <option value="best">Best observed</option>
          <option value="moderate">Moderate</option>
          <option value="experimental">Experimental</option>
        </select>
      </div>

      <p className="mt-3 text-xs text-muted-foreground">
        Showing {visible.length} of {models.length} completed model records. Tags apply only inside
        each dataset and endpoint.
      </p>

      <div className={`mt-4 grid gap-3 ${compact ? "lg:grid-cols-2" : "xl:grid-cols-2"}`}>
        {visible.map((model) => (
          <article
            key={model.id}
            className="rounded-2xl border border-white/10 bg-card/60 p-5 shadow-lg shadow-black/10"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex min-w-0 items-start gap-3">
                <span className="mt-0.5 rounded-lg bg-white/5 p-2 text-emerald">
                  <ModelIcon model={model} />
                </span>
                <div className="min-w-0">
                  <p className="text-xs uppercase tracking-[0.13em] text-muted-foreground">
                    {model.modality} · {model.workflow}
                  </p>
                  <h3 className="mt-1 font-display text-lg font-semibold">{model.name}</h3>
                </div>
              </div>
              <div className="flex flex-wrap justify-end gap-2">
                <span
                  className={`rounded-full border px-2.5 py-1 text-xs ${tagStyles[model.performanceTag]}`}
                >
                  {model.performanceTag === "best" ? "Best observed" : model.performanceTag}
                </span>
                <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-muted-foreground">
                  {availabilityLabels[model.availability]}
                </span>
              </div>
            </div>

            <p className="mt-3 text-sm text-muted-foreground">{model.endpoint}</p>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
              <div className="rounded-lg bg-white/5 p-2">
                <span className="text-muted-foreground">AUPRC</span>
                <strong className="mt-1 block">{format(model.metric.auprc)}</strong>
              </div>
              <div className="rounded-lg bg-white/5 p-2">
                <span className="text-muted-foreground">AUROC</span>
                <strong className="mt-1 block">{format(model.metric.auroc)}</strong>
              </div>
              <div className="rounded-lg bg-white/5 p-2">
                <span className="text-muted-foreground">Balanced acc.</span>
                <strong className="mt-1 block">{format(model.metric.balanced_accuracy)}</strong>
              </div>
            </div>
            <p className="mt-3 text-xs leading-5 text-muted-foreground">
              <ShieldQuestion size={13} className="mr-1 inline" /> {model.evidenceMaturity}
            </p>
            <div className="mt-4 flex flex-wrap gap-3 text-sm">
              {model.availability === "runnable" && model.modality === "ehr" && (
                <Link
                  to="/qml/analyze"
                  search={{ modelId: model.id }}
                  className="inline-flex items-center gap-1 text-emerald hover:underline"
                >
                  <Play size={13} /> Run
                </Link>
              )}
              {model.availability === "runnable" && model.modality === "genomics" && (
                <Link
                  to="/qml/genomics/fh"
                  className="inline-flex items-center gap-1 text-emerald hover:underline"
                >
                  <Play size={13} /> Run FH pathway
                </Link>
              )}
              {model.availability === "runnable" && model.modality === "imaging" && (
                <Link
                  to="/qml/imaging"
                  className="inline-flex items-center gap-1 text-emerald hover:underline"
                >
                  <Play size={13} /> Run QCNN
                </Link>
              )}
              <Link
                to="/qml/models/$modelId"
                params={{ modelId: model.id }}
                className="text-muted-foreground hover:text-foreground"
              >
                Evidence and provenance
              </Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
