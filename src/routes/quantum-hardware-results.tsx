import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";
import { createElement } from "react";

export const Route = createFileRoute("/quantum-hardware-results")({
  validateSearch: (search: Record<string, unknown>) => ({
    jobId: typeof search.jobId === "string" ? search.jobId : "",
  }),
  head: () => ({
    meta: [
      { title: "Real Quantum Hardware Results - QDNA" },
      {
        name: "description",
        content: "Raw real-hardware quantum circuit results with resource-aware backend selection.",
      },
    ],
  }),
  component: lazyRouteComponent(() =>
    import("@/components/QuantumHardwareResults").then(({ QuantumHardwareResultsPage }) => ({
      default: function HardwareResultsRoute() {
        const { jobId } = Route.useSearch();
        return createElement(QuantumHardwareResultsPage, { jobId });
      },
    })),
  ),
});
