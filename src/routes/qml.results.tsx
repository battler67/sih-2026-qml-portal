import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/qml/results")({
  component: lazyRouteComponent(() => import("@/components/QmlPages"), "QmlResults"),
});
