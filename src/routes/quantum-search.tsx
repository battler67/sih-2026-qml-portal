import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/quantum-search")({
  head: () => ({
    meta: [
      { title: "Genomic Quantum Search - QDNA" },
      {
        name: "description",
        content: "NCBI genomic nucleotide retrieval with FRQI or Grover quantum similarity search.",
      },
    ],
  }),
  component: lazyRouteComponent(() => import("@/components/QuantumSearch"), "QuantumSearch"),
});
