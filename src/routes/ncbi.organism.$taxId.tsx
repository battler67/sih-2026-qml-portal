import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";
import { createElement } from "react";

export const Route = createFileRoute("/ncbi/organism/$taxId")({
  head: () => ({
    meta: [
      { title: "NCBI Organism - QDNA" },
      {
        name: "description",
        content: "NCBI taxonomy details for organisms found in quantum and BLAST DNA search results.",
      },
    ],
  }),
  component: lazyRouteComponent(() =>
    import("@/components/NcbiOrganismDetails").then(({ NcbiOrganismDetails }) => ({
      default: function OrganismRoute() {
        const { taxId } = Route.useParams();
        return createElement(NcbiOrganismDetails, { taxId });
      },
    })),
  ),
});
