import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";
import { createElement } from "react";

export const Route = createFileRoute("/ncbi/record/$accession")({
  head: () => ({
    meta: [
      { title: "NCBI Record - QDNA" },
      {
        name: "description",
        content: "Complete NCBI nucleotide record details with selective download and sequence analysis.",
      },
    ],
  }),
  component: lazyRouteComponent(() =>
    import("@/components/NcbiRecordDetails").then(({ NcbiRecordDetails }) => ({
      default: function RecordRoute() {
        const { accession } = Route.useParams();
        return createElement(NcbiRecordDetails, { accession });
      },
    })),
  ),
});
