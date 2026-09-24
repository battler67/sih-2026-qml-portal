import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";
import { createElement } from "react";

export const Route = createFileRoute("/quantum-search-results")({
  validateSearch: (search: Record<string, unknown>) => ({
    jobId: typeof search.jobId === "string" ? search.jobId : "",
  }),
  head: () => ({
    meta: [
      { title: "Quantum Search Results - QDNA" },
      {
        name: "description",
        content:
          "Quantum genomic search results, validation, downloads, and scientific boundaries.",
      },
    ],
  }),
  component: lazyRouteComponent(() =>
    import("@/components/QuantumSearch").then(({ QuantumSearchResultsPage }) => ({
      default: function ResultsRoute() {
        const { jobId } = Route.useSearch();
        return createElement(QuantumSearchResultsPage, { jobId });
      },
    })),
  ),
});
