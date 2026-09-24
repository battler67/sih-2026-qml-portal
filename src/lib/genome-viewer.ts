export type GenomeViewerContext = {
  taxId: string;
  scientificName: string;
  commonName: string;
  rank: string;
  division: string;
  parentTaxId?: string;
  lineage: string;
  treeNodes: Array<{ taxId: string; scientificName: string; rank: string; isSelected: boolean }>;
  image: {
    url: string;
    source: string;
    title: string;
    description: string;
    pageUrl: string;
  } | null;
  links: {
    taxonomy: string;
    genomeDataViewer: string;
  };
};

type OrganismDetails = {
  taxId: string;
  scientificName: string;
  commonName: string;
  rank: string;
  division: string;
  lineage: string;
  lineageTaxa: Array<{ taxId: string; scientificName: string; rank: string }>;
  ncbiUrl: string;
};

export async function fetchGenomeViewerContext(
  apiBase: string,
  taxId: string,
): Promise<GenomeViewerContext> {
  const viewerResponse = await fetch(
    `${apiBase}/api/ncbi/organisms/${encodeURIComponent(taxId)}/genome-viewer`,
  );
  if (viewerResponse.ok) {
    return viewerResponse.json();
  }

  const detailsResponse = await fetch(`${apiBase}/api/ncbi/organisms/${encodeURIComponent(taxId)}`);
  const detailsBody = await detailsResponse
    .json()
    .catch(() => ({ detail: detailsResponse.statusText }));
  if (!detailsResponse.ok) {
    throw new Error(String(detailsBody.detail || detailsResponse.statusText));
  }

  const details = detailsBody as OrganismDetails;
  const scientificName = details.scientificName || "Selected organism";
  return {
    taxId: details.taxId,
    scientificName,
    commonName: details.commonName || "",
    rank: details.rank || "",
    division: details.division || "",
    lineage: details.lineage || "",
    treeNodes: [
      ...details.lineageTaxa
        .filter((node) => node.taxId && node.scientificName)
        .map((node) => ({
          taxId: node.taxId,
          scientificName: node.scientificName,
          rank: node.rank || "no rank",
          isSelected: false,
        })),
      {
        taxId: details.taxId,
        scientificName,
        rank: details.rank || "species",
        isSelected: true,
      },
    ],
    image: await fetchWikimediaImage(scientificName),
    links: {
      taxonomy: details.ncbiUrl,
      genomeDataViewer: gdvUrl(scientificName),
    },
  };
}

async function fetchWikimediaImage(scientificName: string): Promise<GenomeViewerContext["image"]> {
  if (!scientificName.trim()) return null;
  const params = new URLSearchParams({
    action: "query",
    generator: "search",
    gsrsearch: scientificName,
    gsrlimit: "1",
    prop: "pageimages|description|info",
    piprop: "thumbnail|original",
    pithumbsize: "700",
    inprop: "url",
    format: "json",
    origin: "*",
  });

  try {
    const response = await fetch(`https://en.wikipedia.org/w/api.php?${params.toString()}`);
    if (!response.ok) return null;
    const data = await response.json();
    const pages = data?.query?.pages;
    if (!pages || typeof pages !== "object") return null;
    const page = Object.values(pages)[0] as {
      title?: string;
      description?: string;
      fullurl?: string;
      thumbnail?: { source?: string };
      original?: { source?: string };
    };
    const url = page.thumbnail?.source || page.original?.source || "";
    if (!url) return null;
    return {
      url,
      source: "Wikimedia/Wikipedia",
      title: page.title || scientificName,
      description: page.description || "",
      pageUrl: page.fullurl || "",
    };
  } catch {
    return null;
  }
}

function gdvUrl(scientificName: string) {
  const slug = scientificName.trim().toLowerCase().replace(/\s+/g, "-");
  return slug
    ? `https://www.ncbi.nlm.nih.gov/gdv?org=${encodeURIComponent(slug)}`
    : "https://www.ncbi.nlm.nih.gov/gdv";
}
