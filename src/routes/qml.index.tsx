import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/qml/")({
  component: lazyRouteComponent(() => import("@/components/QmlPages"), "QmlLanding"),
});
