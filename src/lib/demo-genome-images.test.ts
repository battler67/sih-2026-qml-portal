import { describe, expect, test } from "bun:test";
import { findDemoGenomeImage } from "./demo-genome-images";

describe("demo genome image lookup", () => {
  test("uses a BRCA1 demo image for a BRCA1 search", () => {
    const image = findDemoGenomeImage({
      gene: "BRCA1",
      organism: "Mus caroli",
      accession: "NC_012345.1",
    });

    expect(image?.url).toBe("/demo/genome-viewer/brca1-protein-structure.png");
    expect(image?.source).toBe("Local demo image");
  });

  test("uses human-specific images for Homo sapiens records", () => {
    const image = findDemoGenomeImage({
      gene: "BRCA1",
      scientificName: "Homo sapiens",
      taxId: "9606",
      accession: "NM_007294.4",
    });

    expect([
      "/demo/genome-viewer/brca1-gene-chromosome-17.png",
      "/demo/genome-viewer/brca1-homo-sapiens-structure.png",
    ]).toContain(image?.url);
  });

  test("matches the L78833.1 BRCA1 record page to a supplied image", () => {
    const image = findDemoGenomeImage({
      gene: "BRCA1",
      organism: "Homo sapiens",
      scientificName: "Homo sapiens",
      taxId: "9606",
      accession: "L78833.1",
    });

    expect([
      "/demo/genome-viewer/brca1-gene-chromosome-17.png",
      "/demo/genome-viewer/brca1-homo-sapiens-structure.png",
    ]).toContain(image?.url);
  });

  test("uses the supplied NBR1 image for the NBR1 record returned by the BRCA1 demo", () => {
    const image = findDemoGenomeImage({
      gene: "NBR1",
      scientificName: "Homo sapiens",
      taxId: "9606",
      accession: "DQ190457.1",
    });

    expect(image?.url).toBe("/demo/genome-viewer/nbr1-homo-sapiens.png");
    expect(image?.title).toBe("");
    expect(image?.description).toBe("");
  });

  test("matches taxonomy images without a supported gene", () => {
    const image = findDemoGenomeImage({
      gene: "TP53",
      scientificName: "Homo sapiens",
      taxId: "9606",
      accession: "NC_000017.11",
    });

    expect([
      "/demo/genome-viewer/homo-sapiens-taxon-9606.png",
      "/demo/genome-viewer/human-silhouette-anatomy.png",
    ]).toContain(image?.url);
  });

  test("returns null so the remote image remains the fallback", () => {
    expect(
      findDemoGenomeImage({
        gene: "Trp53",
        scientificName: "Mus musculus",
        taxId: "10090",
      }),
    ).toBeNull();
  });
});
