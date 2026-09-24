import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";
import { createElement } from "react";

export const Route = createFileRoute("/qml/models/$modelId")({
  component: lazyRouteComponent(() =>
    import("@/components/QmlPages").then(({ QmlModelDetails }) => ({
      default: function ModelRoute() {
        const { modelId } = Route.useParams();
        return createElement(QmlModelDetails, { modelId });
      },
    })),
  ),
});
