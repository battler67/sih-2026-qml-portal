import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";
import { createElement } from "react";

export const Route = createFileRoute("/qml/analyze")({
  validateSearch: (search: Record<string, unknown>): { modelId?: string } =>
    typeof search.modelId === "string" ? { modelId: search.modelId } : {},
  component: lazyRouteComponent(() =>
    import("@/components/QmlPages").then(({ QmlAnalyze }) => ({
      default: function QmlAnalyzeRoute() {
        const { modelId } = Route.useSearch();
        return createElement(QmlAnalyze, { initialModelId: modelId });
      },
    })),
  ),
});
