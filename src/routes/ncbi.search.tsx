import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/ncbi/search")({
  head: () => ({
    meta: [
      { title: "NCBI Gene Search - QDNA" },
      {
        name: "description",
        content: "NCBI Entrez gene search results for nucleotide records and quantum analysis handoff.",
      },
    ],
  }),
  component: lazyRouteComponent(() => import("@/components/NcbiSearchResults"), "NcbiSearchResults"),
});
