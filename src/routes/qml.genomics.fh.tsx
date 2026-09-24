import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/qml/genomics/fh")({
  component: lazyRouteComponent(() => import("@/components/FhPathway"), "FhPathway"),
});
