import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/qml/imaging")({
  component: lazyRouteComponent(() => import("@/components/QcnnImaging"), "QcnnImaging"),
});
