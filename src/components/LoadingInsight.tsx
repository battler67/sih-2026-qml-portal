import { useEffect, useState } from "react";
import { ChevronRight, Dna, Sparkles } from "lucide-react";
import { LOADING_FACTS } from "@/lib/loading-facts";

export function LoadingInsight({ title }: { title: string }) {
  const [factIndex, setFactIndex] = useState(() => stableIndex(title));

  useEffect(() => {
    setFactIndex(Math.floor(Math.random() * LOADING_FACTS.length));
  }, [title]);

  function showAnotherFact() {
    setFactIndex((current) => {
      let next = current;
      while (next === current) next = Math.floor(Math.random() * LOADING_FACTS.length);
      return next;
    });
  }

  return (
    <section
      className="glass relative overflow-hidden rounded-2xl border border-emerald/30 p-6 shadow-lg shadow-emerald/5"
      aria-label={`${title}: science fact`}
    >
      <div className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-emerald/15 blur-3xl" />
      <div className="relative flex items-start gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-emerald/25 bg-emerald/10 text-emerald">
          <Dna className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-emerald">
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            While the science loads
          </div>
          <p className="mt-3 min-h-12 text-sm leading-6 text-foreground/85" aria-live="polite">
            {LOADING_FACTS[factIndex]}
          </p>
        </div>
        <button
          type="button"
          onClick={showAnotherFact}
          className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-emerald transition hover:border-emerald/40 hover:bg-emerald/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald"
          aria-label="Show another quantum or DNA fact"
          title="Show another fact"
        >
          <ChevronRight className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>
    </section>
  );
}

function stableIndex(value: string) {
  return (
    Array.from(value).reduce((total, character) => total + character.charCodeAt(0), 0) %
    LOADING_FACTS.length
  );
}
