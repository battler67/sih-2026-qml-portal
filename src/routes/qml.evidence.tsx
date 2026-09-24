import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/qml/evidence")({
  component: lazyRouteComponent(() => import("@/components/QmlPages"), "QmlEvidence"),
});
