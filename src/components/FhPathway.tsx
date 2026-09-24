import { useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  Activity,
  ArrowRight,
  Atom,
  CheckCircle2,
  CircleAlert,
  Dna,
  FileClock,
  FlaskConical,
  GitBranch,
  Loader2,
  ShieldCheck,
  Stethoscope,
} from "lucide-react";
import { Notice, Shell, button, panel, subtleButton } from "@/components/QmlPages";
import { qmlApi, type FhRecord, type FhResult, type FhSchema } from "@/lib/qml-api";

const checkboxFields: { name: keyof FhRecord; label: string; detail: string }[] = [
  {
    name: "familyHistoryPrematureAscvd",
    label: "Premature ASCVD in family",
    detail: "Synthetic first-degree family-history signal.",
  },
  {
    name: "familyHistoryHighLdl",
    label: "High LDL-C in family",
    detail: "Synthetic first-degree high-cholesterol history.",
  },
  {
    name: "personalHistoryPrematureAscvd",
    label: "Personal premature ASCVD",
    detail: "Synthetic personal clinical-history signal.",
  },
  {
    name: "tendonXanthomas",
    label: "Tendon xanthomas",
    detail: "Synthetic physical-examination finding.",
  },
  {
    name: "cornealArcusBefore45",
    label: "Corneal arcus before 45",
    detail: "Synthetic physical-examination finding.",
  },
  {
    name: "secondaryCausesReviewed",
    label: "Secondary causes reviewed",
    detail: "Required context for interpreting high LDL-C.",
  },
];

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function metric(value?: number) {
  return value == null ? "—" : value.toFixed(3);
}

export function FhPathway() {
  const [schema, setSchema] = useState<FhSchema | null>(null);
  const [record, setRecord] = useState<FhRecord | null>(null);
  const [result, setResult] = useState<FhResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    qmlApi
      .fhSchema()
      .then((next) => {
        if (!active) return;
        setSchema(next);
        setRecord(next.examples[0].record);
      })
      .catch((reason) => active && setError(reason.message));
    return () => {
      active = false;
    };
  }, []);

  const selectedVariant = useMemo(
    () => schema?.variantOptions.find((item) => item.id === record?.variantId),
    [record?.variantId, schema?.variantOptions],
  );

  function update<K extends keyof FhRecord>(name: K, value: FhRecord[K]) {
    setRecord((current) => (current ? { ...current, [name]: value } : current));
    setResult(null);
    setError("");
  }

  async function analyze() {
    if (!record) return;
    setBusy(true);
    setError("");
    try {
      setResult(await qmlApi.fhAnalyze(record));
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell
      eyebrow="Genomics · synthetic FH pathway"
      title="Trace evidence to an FH referral signal."
    >
      <div className="mb-6 grid gap-3 md:grid-cols-4">
        {[
          ["01", "Synthetic record", Dna],
          ["02", "Evidence snapshot", FileClock],
          ["03", "Referral rules", GitBranch],
          ["04", "Model comparison", Atom],
        ].map(([step, label, Icon]) => (
          <div
            key={String(step)}
            className="rounded-xl border border-white/10 bg-white/[0.035] p-4"
          >
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{step}</span>
              <Icon size={16} className="text-emerald" />
            </div>
            <div className="mt-2 text-sm font-medium">{label as string}</div>
          </div>
        ))}
      </div>

      <Notice>
        This adults-only workflow accepts synthetic structured records. It does not accept DNA, VCF,
        identifiable EHR data or personal medical images.
      </Notice>

      {!schema || !record ? (
        <p className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 size={16} className="animate-spin" /> Loading the pinned synthetic evidence…
        </p>
      ) : (
        <div className="mt-6 grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
          <section className={panel} aria-labelledby="fh-input-title">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald">
                  Input and preprocessing
                </p>
                <h2 id="fh-input-title" className="mt-2 font-display text-2xl font-semibold">
                  Synthetic FH record
                </h2>
              </div>
              <span className="rounded-full border border-cyan-glow/25 bg-cyan-glow/10 px-3 py-1 text-xs text-cyan-glow">
                Synthetic only
              </span>
            </div>

            <div className="mt-5 flex flex-wrap gap-2">
              {schema.examples.map((example) => (
                <button
                  key={example.id}
                  type="button"
                  className={subtleButton}
                  onClick={() => {
                    setRecord(example.record);
                    setResult(null);
                    setError("");
                  }}
                >
                  <FlaskConical size={15} /> {example.label}
                </button>
              ))}
            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <label className="text-sm">
                <span className="font-medium">Age</span>
                <input
                  type="number"
                  min={18}
                  max={100}
                  value={record.ageYears}
                  onChange={(event) => update("ageYears", Number(event.target.value))}
                  className="mt-2 w-full rounded-xl border border-white/15 bg-background/70 px-3 py-2.5"
                />
              </label>
              <label className="text-sm">
                <span className="font-medium">Untreated LDL-C</span>
                <div className="relative mt-2">
                  <input
                    type="number"
                    min={40}
                    max={700}
                    value={record.untreatedLdlCMgDl}
                    onChange={(event) => update("untreatedLdlCMgDl", Number(event.target.value))}
                    className="w-full rounded-xl border border-white/15 bg-background/70 px-3 py-2.5 pr-20"
                  />
                  <span className="absolute right-3 top-3 text-xs text-muted-foreground">
                    mg/dL
                  </span>
                </div>
              </label>
              <label className="text-sm">
                <span className="font-medium">Sex at birth</span>
                <select
                  value={record.sexAtBirth}
                  onChange={(event) =>
                    update("sexAtBirth", event.target.value as FhRecord["sexAtBirth"])
                  }
                  className="theme-select mt-2 w-full rounded-xl border border-white/15 px-3 py-2.5"
                >
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                  <option value="not_specified">Not specified</option>
                </select>
              </label>
              <label className="text-sm">
                <span className="font-medium">Synthetic variant evidence</span>
                <select
                  value={record.variantId}
                  onChange={(event) => update("variantId", event.target.value)}
                  className="theme-select mt-2 w-full rounded-xl border border-white/15 px-3 py-2.5"
                >
                  {schema.variantOptions.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {checkboxFields.map((field) => (
                <label
                  key={field.name}
                  className="flex cursor-pointer gap-3 rounded-xl border border-white/10 bg-white/[0.025] p-3"
                >
                  <input
                    type="checkbox"
                    checked={Boolean(record[field.name])}
                    onChange={(event) => update(field.name, event.target.checked as never)}
                    className="mt-1 h-4 w-4 accent-emerald"
                  />
                  <span>
                    <span className="block text-sm font-medium">{field.label}</span>
                    <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                      {field.detail}
                    </span>
                  </span>
                </label>
              ))}
            </div>

            <div className="mt-6 rounded-xl border border-emerald/20 bg-emerald/5 p-4 text-sm">
              <div className="flex items-center gap-2 font-medium text-emerald">
                <ShieldCheck size={17} /> Visible preprocessing
              </div>
              <p className="mt-2 leading-6 text-muted-foreground">
                LDL-C is validated as an untreated synthetic measurement. Evidence strength, family
                history and phenotype are converted into four auditable features. The same four
                features feed the logistic and Angle-QKSVM models.
              </p>
            </div>

            {error && (
              <div className="mt-5">
                <Notice error>{error}</Notice>
              </div>
            )}
            <button
              type="button"
              className={`${button} mt-6`}
              disabled={busy}
              onClick={() => void analyze()}
            >
              {busy ? <Loader2 size={16} className="animate-spin" /> : <Activity size={16} />}
              Analyze synthetic record
            </button>
          </section>

          <aside className="space-y-5">
            <section className={panel}>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald">
                    Pinned evidence
                  </p>
                  <h2 className="mt-2 font-display text-xl font-semibold">
                    {selectedVariant?.gene} · {humanize(selectedVariant?.classification || "")}
                  </h2>
                </div>
                <FileClock className="text-cyan-glow" />
              </div>
              <dl className="mt-5 space-y-3 text-sm">
                <div className="flex justify-between gap-4 border-b border-white/5 pb-2">
                  <dt className="text-muted-foreground">Snapshot</dt>
                  <dd className="font-mono text-xs">{schema.snapshotId}</dd>
                </div>
                <div className="flex justify-between gap-4 border-b border-white/5 pb-2">
                  <dt className="text-muted-foreground">Variant ID</dt>
                  <dd className="font-mono text-xs">{record.variantId}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">Source</dt>
                  <dd>Synthetic educational fixture</dd>
                </div>
              </dl>
            </section>

            {!result ? (
              <section className={`${panel} border-dashed`}>
                <GitBranch className="text-emerald" />
                <h2 className="mt-4 font-display text-xl font-semibold">
                  Referral result appears here
                </h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  The evidence result, visible score breakdown, referral state and matched model
                  comparison remain separate so a model cannot overwrite curated evidence.
                </p>
              </section>
            ) : (
              <>
                <section className={panel} aria-live="polite">
                  <div className="flex items-start gap-3">
                    {result.evidence.isQualifyingPositive ? (
                      <CheckCircle2 className="mt-1 shrink-0 text-emerald" />
                    ) : (
                      <CircleAlert className="mt-1 shrink-0 text-amber-300" />
                    )}
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                        Evidence result
                      </p>
                      <h2 className="mt-2 font-display text-xl font-semibold">
                        {humanize(result.evidence.classification)}
                      </h2>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        {result.evidence.interpretation}
                      </p>
                    </div>
                  </div>
                </section>

                <section className={panel}>
                  <div className="flex items-center gap-2 text-emerald">
                    <Stethoscope size={19} />
                    <span className="text-xs font-semibold uppercase tracking-[0.16em]">
                      Referral pathway
                    </span>
                  </div>
                  <h2 className="mt-3 font-display text-xl font-semibold">
                    {humanize(result.referral.category)}
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {result.referral.message}
                  </p>
                  <div className="mt-4 rounded-xl bg-white/5 p-4">
                    <div className="flex items-end justify-between">
                      <span className="text-sm text-muted-foreground">Educational DLCN score</span>
                      <span className="font-display text-3xl text-emerald">
                        {result.clinicalSuspicion.score}
                      </span>
                    </div>
                    <div className="mt-3 space-y-2 text-xs">
                      {Object.entries(result.clinicalSuspicion.breakdown).map(([name, value]) => (
                        <div key={name} className="flex justify-between gap-3">
                          <span className="text-muted-foreground">{humanize(name)}</span>
                          <span>{value} points</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>

                <section className={panel}>
                  <div className="flex items-center justify-between gap-3">
                    <h2 className="font-display text-xl font-semibold">
                      Research model comparison
                    </h2>
                    <Atom className="text-cyan-glow" />
                  </div>
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">
                    These probabilities reproduce synthetic rules. They are not independent evidence
                    of FH.
                  </p>
                  <div className="mt-4 space-y-3">
                    {result.researchModels.map((model) => (
                      <article
                        key={model.id}
                        className="rounded-xl border border-white/10 bg-white/[0.025] p-4"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <div className="text-sm font-medium">{model.name}</div>
                            <div className="mt-1 text-xs text-muted-foreground">
                              {model.type.replaceAll("_", " ")} · experimental
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-display text-2xl">
                              {(model.probability * 100).toFixed(1)}%
                            </div>
                            <div className="text-xs text-muted-foreground">
                              rule-reproduction score
                            </div>
                          </div>
                        </div>
                        <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                          <div className="rounded-lg bg-white/5 p-2">
                            <span className="text-muted-foreground">AUPRC</span>
                            <strong className="mt-1 block">{metric(model.metrics.auprc)}</strong>
                          </div>
                          <div className="rounded-lg bg-white/5 p-2">
                            <span className="text-muted-foreground">AUROC</span>
                            <strong className="mt-1 block">{metric(model.metrics.auroc)}</strong>
                          </div>
                          <div className="rounded-lg bg-white/5 p-2">
                            <span className="text-muted-foreground">Qubits</span>
                            <strong className="mt-1 block">
                              {String(model.resources.qubits ?? "N/A")}
                            </strong>
                          </div>
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
              </>
            )}
          </aside>
        </div>
      )}

      <div className="mt-6 flex flex-wrap gap-3">
        <Link to="/qml" className={subtleButton}>
          Back to modality selection
        </Link>
        <Link to="/qml/evidence" className={subtleButton}>
          Open all model evidence <ArrowRight size={15} />
        </Link>
      </div>
    </Shell>
  );
}
