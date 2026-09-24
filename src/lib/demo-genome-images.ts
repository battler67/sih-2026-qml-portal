import type { GenomeViewerContext } from "./genome-viewer";

export type DemoGenomeImageQuery = {
  gene?: string;
  organism?: string;
  scientificName?: string;
  taxId?: string;
  accession?: string;
};

type DemoGenomeImage = NonNullable<GenomeViewerContext["image"]> & {
  genes?: string[];
  organisms?: string[];
  taxIds?: string[];
};

const DEMO_IMAGES: DemoGenomeImage[] = [
  {
    url: "/demo/genome-viewer/brca1-gene-chromosome-17.png",
    source: "Local demo image",
    title: "Human BRCA gene chromosome locations",
    description: "BRCA1 on chromosome 17 and BRCA2 on chromosome 13.",
    pageUrl: "",
    genes: ["BRCA1"],
    organisms: ["Homo sapiens", "human"],
    taxIds: ["9606"],
  },
  {
    url: "/demo/genome-viewer/brca1-homo-sapiens-structure.png",
    source: "Local demo image",
    title: "BRCA1 structure in Homo sapiens",
    description: "A molecular structure view supplied for the local genome-viewer demo.",
    pageUrl: "",
    genes: ["BRCA1"],
    organisms: ["Homo sapiens", "human"],
    taxIds: ["9606"],
  },
  {
    url: "/demo/genome-viewer/brca1-protein-structure.png",
    source: "Local demo image",
    title: "BRCA1 protein structure",
    description: "A protein structure view supplied for the local genome-viewer demo.",
    pageUrl: "",
    genes: ["BRCA1"],
  },
  {
    url: "/demo/genome-viewer/homo-sapiens-taxon-9606.png",
    source: "Local demo image",
    title: "Homo sapiens — taxonomy ID 9606",
    description: "Human anatomical reference image for the selected NCBI taxon.",
    pageUrl: "",
    organisms: ["Homo sapiens", "human"],
    taxIds: ["9606"],
  },
  {
    url: "/demo/genome-viewer/human-silhouette-anatomy.png",
    source: "Local demo image",
    title: "Human anatomy",
    description: "Human anatomical silhouette supplied for the local genome-viewer demo.",
    pageUrl: "",
    organisms: ["Homo sapiens", "human"],
    taxIds: ["9606"],
  },
  {
    url: "/demo/genome-viewer/nbr1-homo-sapiens.png",
    source: "Local demo image",
    title: "",
    description: "",
    pageUrl: "",
    genes: ["NBR1"],
    organisms: ["Homo sapiens", "human"],
    taxIds: ["9606"],
  },
];

export function findDemoGenomeImage(query: DemoGenomeImageQuery): GenomeViewerContext["image"] {
  const gene = normalize(query.gene);
  const organisms = [query.organism, query.scientificName].map(normalize).filter(Boolean);
  const taxId = normalize(query.taxId);

  const scored = DEMO_IMAGES.map((image, index) => {
    const geneMatch = Boolean(gene && image.genes?.some((value) => normalize(value) === gene));
    const organismMatch = Boolean(
      organisms.length && image.organisms?.some((value) => organisms.includes(normalize(value))),
    );
    const taxIdMatch = Boolean(taxId && image.taxIds?.some((value) => normalize(value) === taxId));

    if (image.genes?.length && !geneMatch) return null;
    if (image.organisms?.length && !organismMatch && !taxIdMatch) return null;

    return {
      image,
      index,
      score: (geneMatch ? 100 : 0) + (organismMatch || taxIdMatch ? 30 : 0),
    };
  }).filter((entry): entry is NonNullable<typeof entry> => entry !== null);

  if (scored.length === 0) return null;
  const bestScore = Math.max(...scored.map((entry) => entry.score));
  const bestMatches = scored.filter((entry) => entry.score === bestScore);
  const selectionKey =
    query.accession || query.gene || query.scientificName || query.organism || "";
  const selected = bestMatches[stableIndex(selectionKey, bestMatches.length)]?.image;
  if (!selected) return null;

  return {
    url: selected.url,
    source: selected.source,
    title: selected.title,
    description: selected.description,
    pageUrl: selected.pageUrl,
  };
}

function normalize(value?: string) {
  return (value || "").trim().toLowerCase().replace(/[_-]+/g, " ").replace(/\s+/g, " ");
}

function stableIndex(value: string, length: number) {
  if (length <= 1) return 0;
  let hash = 0;
  for (const character of value) {
    hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  }
  return hash % length;
}
