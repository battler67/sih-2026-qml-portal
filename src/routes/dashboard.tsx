import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — QDNA" },
      {
        name: "description",
        content: "Quantum DNA alignment workspace with FRQI encoding and Grover search.",
      },
    ],
  }),
  component: lazyRouteComponent(() => import("@/components/Dashboard"), "Dashboard"),
});
