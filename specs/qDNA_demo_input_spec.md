# QDNA Genomic Search Input Specification

## 1. Query Sequence

Purpose:
The query sequence is the DNA pattern to search for or compare against.

Accepted query input modes:

### A. Pasted

- Enter raw DNA bases directly.
- Allowed characters: A, C, G, T only.
- Whitespace is removed and lowercase bases are converted to uppercase.
- Minimal example:

```text
ACGT
```

- Multiline example:

```text
acgt acgt
ttaa
```

The normalized query passed to the search is `ACGTACGTTTAA`.

- Invalid example:

```text
ACNT
```

Expected behavior: validation stops at `N` because query sequences must be unambiguous ACGT DNA.

### B. Uploaded FASTA

- Enter a FASTA-formatted query sequence.
- Header line starts with `>`.
- Sequence must contain A, C, G, T only for quantum processing.
- Single-line example:

```text
>query_demo
ACGT
```

- Multiline example:

```text
>query_lacz_fragment
ATGACCATG
ATTACGGAT
```

The FASTA header is metadata; the two sequence lines are combined into one 18-base query.

- Invalid ambiguity example:

```text
>query_with_unknown_base
ACGTNACGT
```

Expected behavior: the upload is rejected for use as a query. Replace `N` with a verified base or select a known ACGT-only region; do not silently delete it.

### C. NCBI Accession

- Enter an NCBI nucleotide accession to use as the query source.
- The backend fetches the sequence from NCBI.
- The fetched sequence must be DNA.
- Unsupported ambiguity bases such as N, R, Y are detected and not silently removed.
- Example genomic nucleotide accession:

```text
U00096.3
```

- Example of an unsuitable query accession:

```text
XM_085829552.1
```

Expected behavior: the fetched `XM_` record is identified as mRNA and rejected rather than treated as genomic DNA.

- Example decision sequence:

```text
1. Enter accession: U00096.3
2. Fetch the record.
3. Confirm molecule type: DNA.
4. Select an ACGT-only region no longer than Maximum Query Length.
5. Estimate before running the simulator.
```

### Query Input Selection Examples

| Goal | Recommended mode | Example |
| --- | --- | --- |
| Fastest offline demonstration | Pasted | `ACGT` |
| Preserve a named local sample | Uploaded FASTA | `>sample_01` followed by `ACGTACGT` |
| Reuse a public nucleotide record | NCBI accession | `U00096.3` |
| Test validation behavior | Pasted | `ACNT` should be rejected |

## 2. Search Database / Reference Genomic Data

Purpose:
This is the target/reference genomic data where the query sequence is searched.

Accepted database modes:

### A. Taxonomy ID Assemblies

- Used to retrieve genome assemblies by NCBI taxonomy ID.
- Example organism:

```text
Escherichia coli
```

- Example taxonomy ID:

```text
562
```

- Additional examples:

```text
Homo sapiens — 9606
Mus musculus — 10090
Oryza sativa — 4530
```

Use the numeric taxonomy ID to avoid ambiguity between organisms with similar common names.

### B. Organism Assemblies

- Used to retrieve genome assemblies by organism name.
- Examples:

```text
Escherichia coli
Homo sapiens
Oryza sativa
```

For a demo, combine an organism name with `Maximum records: 1` so that retrieval and preprocessing stay bounded.

### C. Exact Genomic Nucleotide Accessions

- Used when you already know exact genomic nucleotide accession IDs.
- Examples:

```text
U00096.3
FJ404781.1
JF300162.1
```

Multiple accessions can be entered when the UI accepts an accession list, but a single accession is safest for live demonstrations.

### D. Exact GCA/GCF Assembly Accessions

- Used when you already know assembly accession IDs.
- Examples:

```text
GCF_000005845.2
GCA_000005845.2
```

- RefSeq and GenBank example pair:

```text
RefSeq assembly: GCF_000005845.2
GenBank assembly: GCA_000005845.2
Organism: Escherichia coli str. K-12 substr. MG1655
```

Use the complete versioned accession when it is known. `GCF_` selects RefSeq and `GCA_` selects GenBank.

### E. Uploaded Genomic FASTA

- Used when the target/reference genome is supplied manually as FASTA.
- One-record example:

```text
>reference_demo
ACGTACGTACGT
```

- Multi-record example:

```text
>contig_1
TTTTACGTAAAA
>contig_2
GGGGACGTCCCC
```

- Ambiguous-target example:

```text
>reference_with_gap
ACGTNNNNACGT
```

Expected behavior: the target may be accepted as IUPAC DNA, but windows containing `N` are skipped. ACGT-only windows remain eligible for quantum processing.

### F. RefSeq Reference or Representative Assemblies

- Use `RefSeq reference assemblies` when a curated reference genome is preferred.
- Use `RefSeq representative assemblies` when a representative genome is acceptable.
- Example:

```text
Organism: Escherichia coli
Scope: RefSeq reference assemblies
Maximum records: 1
```

### G. GenBank GCA or RefSeq GCF Assemblies

- Use `GenBank GCA assemblies` to search GenBank assemblies.
- Use `RefSeq GCF assemblies` to search RefSeq assemblies.
- Examples:

```text
Organism: Escherichia coli
Scope: GenBank GCA assemblies
```

```text
Organism: Escherichia coli
Scope: RefSeq GCF assemblies
```

### H. Pasted Genomic DNA

- Use this local target mode for the smallest possible demo without creating a FASTA header.
- Example:

```text
Query: ACGT
Target: TTTTACGTAAAA
```

Expected forward-strand exact match: the query starts at one-based target position 5.

### Database Mode Selection Examples

| Situation | Database mode | Example value |
| --- | --- | --- |
| No network access | Uploaded genomic FASTA | `>demo` / `ACGTACGT` |
| Known chromosome or nucleotide record | Exact genomic nucleotide accessions | `U00096.3` |
| Known assembly | Exact GCA/GCF accessions | `GCF_000005845.2` |
| Known organism but not accession | Organism assemblies | `Escherichia coli` |
| Known taxonomic identifier | Taxonomy ID assemblies | `562` |

## 3. Search Configuration

### Shots

- Number of simulator measurements.
- Demo-safe values:

```text
16, 64, 128
```

- Larger values increase runtime.
- Example choices:

```text
16 shots: fastest smoke test
64 shots: repeatable presentation demo
128 shots: slightly smoother probability/count charts
```

- Example workload comparison: two accepted windows at 64 shots produce an estimated 128 simulator measurements.

### Maximum Query Length

- Maximum accepted query length.
- Demo-safe value:

```text
32
```

- Examples:

```text
Query ACGT (length 4) with maximum 32: accepted
Query ACGTACGT (length 8) with maximum 4: rejected
```

For Grover demos, prefer a 4-base query even though the input limit can be higher, because circuit cost grows rapidly.

### Maximum Records

- Number of genomic records to retrieve/process.
- Demo-safe value:

```text
1
```

- Examples:

```text
1: process only the first bounded record
2: compare two retrieved records, with higher retrieval and simulation cost
```

### Maximum Windows

- Number of target windows processed by the quantum simulator.
- Demo-safe values:

```text
1 or 2
```

- Example with query `ACGT` and target `ACGTACGT`:

```text
Maximum windows 1: process the first eligible window only
Maximum windows 2: process the first two eligible windows only
```

This setting is a compute cap, not the total number of possible sliding windows in the target.

### Window Stride

- Sliding window step size.
- Demo-safe value:

```text
1
```

- Example for a four-base query on target `ACGTACGT`:

```text
Stride 1 starts: 1, 2, 3, 4, 5
Stride 2 starts: 1, 3, 5
```

Coordinates in results are one-based; internal sequence indexes may be zero-based.

### Strand

- Forward strand: searches only forward DNA.
- Both strands: searches forward and reverse-complement strands.
- Demo-safe value:

```text
Forward strand
```

- Forward-only example:

```text
Query: AGTC
Target: TTTTAGTCAAAA
Result: forward hit
```

- Reverse-complement example:

```text
Query: AGTC
Reverse complement: GACT
Target: TTTTGACTAAAA
Forward strand: no exact query hit
Both strands: reverse-complement hit
```

### Complete Configuration Profiles

| Profile | Shots | Max records | Max windows | Stride | Strand |
| --- | ---: | ---: | ---: | ---: | --- |
| Smoke test | 16 | 1 | 1 | 1 | Forward |
| Presentation demo | 64 | 1 | 2 | 1 | Forward |
| Strand demonstration | 64 | 1 | 4 | 1 | Both |
| Small FRQI comparison | 128 | 1 | 4 | 2 | Forward |

## 4. Algorithm Selection

### FRQI Similarity

- Compares query and target windows using FRQI-style quantum similarity.
- Faster for demos.
- Example:

```text
Query:  ACGT
Window: ACGA
```

The window can receive a nonzero FRQI similarity score even though it is not an exact match. Treat this as an angle-overlap ranking score, not BLAST percent identity.

- Best-use example: rank a few four-base windows when approximate similarity is more useful than exact-hit detection.

### Grover Search

- Performs exact-pattern Grover/QGSA search.
- More expensive than FRQI.
- Demo-safe only with small windows, low shots and few records.
- Exact-match example:

```text
Query:  ACGT
Target: TTACGTAA
```

Expected behavior: the exact `ACGT` occurrence is amplified and returned as a quantum hit.

- No-match example:

```text
Query:  ACGT
Target: TTACGAAA
```

Expected behavior: no exact `ACGT` hit. The current Grover oracle does not allow mismatches.

### Hybrid Search

- Visible as a research option only.
- Not executable in this build.
- Example:

```text
Algorithm: Hybrid Search
Action: Run Search
Expected: execution remains disabled; select FRQI or Grover
```

### Algorithm Choice Examples

| Goal | Choose | Example |
| --- | --- | --- |
| Rank near matches | FRQI Similarity | Compare `ACGT` with `ACGA` |
| Find an exact short motif | Grover Search | Find `ACGT` in `TTACGTAA` |
| Discuss future research UI | Hybrid Search | Display only; do not run |

## 5. Recommended Demo Inputs

### Fast Local Grover Demo

Query Sequence:

```text
pasted
ACGT
```

Search Database:

```text
Uploaded genomic FASTA
```

Reference FASTA:

```text
>demo_reference
ACGTACGT
```

Algorithm:

```text
Grover Search
```

Configuration:

```text
Shots: 16
Maximum records: 1
Maximum windows: 2
Window stride: 1
Strand: Forward strand
```

Expected:

- Estimate completes.
- Run Search completes.
- Results show quantum hits.

### Fast NCBI Taxonomy Demo

Query Sequence:

```text
pasted
ACGT
```

Search Database:

```text
Taxonomy ID assemblies
```

Organism:

```text
Escherichia coli
```

Taxonomy ID:

```text
562
```

Algorithm:

```text
FRQI Similarity or Grover Search
```

Configuration:

```text
Shots: 16
Maximum records: 1
Maximum windows: 1 or 2
Window stride: 1
Strand: Forward strand
```

Expected:

- NCBI retrieves bounded genomic records.
- Quantum processing runs only on limited ACGT windows.
- Full GenBank is not loaded into a quantum circuit.

### Fast Local FRQI Similarity Demo

Query Sequence:

```text
pasted
ACGT
```

Search Database and reference:

```text
Uploaded genomic FASTA
>frqi_reference
ACGAACGT
```

Algorithm and configuration:

```text
Algorithm: FRQI Similarity
Shots: 64
Maximum records: 1
Maximum windows: 2
Window stride: 4
Strand: Forward strand
```

Expected:

- Two non-overlapping windows, `ACGA` and `ACGT`, are compared.
- The exact window should rank above the one-base variant.
- The score is reported as FRQI similarity, not percent identity.

### Reverse-Complement Grover Demo

Query Sequence:

```text
pasted
AGTC
```

Search Database and target:

```text
Pasted genomic DNA
GACT
```

Algorithm and configuration:

```text
Algorithm: Grover Search
Shots: 64
Maximum records: 1
Maximum windows: 2
Window stride: 1
Strand: Both strands
```

Expected:

- The reverse complement `GACT` is eligible for matching.
- Re-running with `Forward strand` illustrates the difference between strand modes.

### Exact Nucleotide Accession Demo

Query Sequence:

```text
pasted
ACGT
```

Search Database:

```text
Exact genomic nucleotide accessions
FJ404781.1
```

Configuration:

```text
Algorithm: FRQI Similarity
Shots: 16
Maximum records: 1
Maximum windows: 1
Window stride: 1
Strand: Forward strand
```

Expected:

- Only the named genomic nucleotide record is fetched.
- Retrieval still depends on NCBI availability and configured credentials.
- The simulator processes only the configured bounded window count.

## Recommended Hackathon Demo Order

Use the Fast Local Grover Demo first. It is the most reliable demo because it avoids live NCBI latency and keeps the quantum simulator workload small.

Example presentation order:

```text
1. Fast Local Grover Demo — prove the end-to-end path.
2. Fast Local FRQI Similarity Demo — contrast ranking with exact matching.
3. Reverse-Complement Grover Demo — explain strand handling.
4. Fast NCBI Taxonomy Demo — show live retrieval only after local demos succeed.
```

## 6. NCBI Search Page Recommended Inputs

Page:

```text
http://localhost:8080/ncbi/search
```

Use these values when the goal is to find records that can safely hand off to the quantum sequence analysis page.

### BRCA1 / Mus caroli Search

Recommended input values:

```text
Gene: BRCA1
Organism filter: Mus caroli
Source: RefSeq + GenBank
Min length: 10000
Max length: 250000
```

Finding:

- Do not use `GenBank only` for the default BRCA1/Mus caroli workflow. It can return zero records after genomic filtering, or it can steer users toward transcript records in older cached results.
- The record `XM_085829552.1` is an mRNA record. It is useful for viewing NCBI metadata, but it is not valid for quantum sequence analysis in this project because the analysis endpoint rejects RNA records.
- The frontend should show `Genomic DNA required` for RNA/protein/transcript records instead of opening `/quantum-search?analysisAccession=...`.

### If BRCA1 / Mus caroli Returns Zero Records

Use this broader fallback:

```text
Gene: BRCA1
Organism filter: Mus caroli
Source: RefSeq + GenBank
Min length: 1000
Max length: 1000000
```

If that still returns zero records, remove only the organism filter:

```text
Gene: BRCA1
Organism filter:
Source: RefSeq + GenBank
Min length: 10000
Max length: 1000000
```

Reason:

- Genomic DNA records are often much longer than mRNA records.
- A narrow upper bound like `10000` can select short transcript-like records or eliminate valid genomic records.
- Empty organism filters are useful for discovery, but organism-specific filters are better once a valid DNA accession is known.

### Reliable Demo Search

Use this when a live NCBI demo needs to return quickly:

```text
Gene: lacZ
Organism filter: Escherichia coli
Source: RefSeq + GenBank
Min length: 1000
Max length: 10000
```

Finding:

- This search returned DNA records from the local API during validation.
- Some returned lacZ records are CDS/gene-region records rather than full genomic assemblies, so prefer the `View Record` button first and use `Sequence Analysis` only when the page marks the record as DNA-analysis ready.

### Broader Human BRCA1 Discovery Example

Use this for discovery when the organism-specific search is too restrictive:

```text
Gene: BRCA1
Organism filter: Homo sapiens
Source: RefSeq + GenBank
Min length: 10000
Max length: 1000000
```

Example review sequence:

```text
1. Run the search.
2. Open View Record.
3. Confirm Molecule is DNA.
4. Confirm the record is genomic rather than mRNA/protein.
5. Use Sequence Analysis only when the result card enables it.
```

### Small lacZ Search Variants

Exact-organism variant:

```text
Gene: lacZ
Organism filter: Escherichia coli str. K-12 substr. MG1655
Source: RefSeq + GenBank
Min length: 1000
Max length: 10000
```

Broader fallback:

```text
Gene: lacZ
Organism filter: Escherichia coli
Source: RefSeq + GenBank
Min length: 500
Max length: 20000
```

### Search Result Interpretation Examples

| Result | Recommended action |
| --- | --- |
| `Molecule: DNA` and `Sequence Analysis` enabled | Open the analysis handoff |
| `XM_085829552.1`, mRNA | View metadata only; do not analyze as genomic DNA |
| Zero records with a narrow length range | Increase `Max length`, then reduce `Min length` if needed |
| Many records from an empty organism filter | Add the scientific organism name to narrow the result set |
| Live request is slow | Return to the local FASTA demo rather than increasing quantum limits |

## 7. Genomic/DNA Verification Finding

Finding:

- The backend quantum-analysis endpoint is not hardcoded. It fetches the selected NCBI record details, reads the GenBank/FASTA sequence, checks the molecule type, rejects RNA/protein records, and rejects sequences containing `U`.
- The NCBI search result card previously used an overly strict frontend heuristic that required the word `genomic` and rejected titles containing `CDS`. That was incorrect because valid DNA records can have CDS annotations. The frontend readiness rule should accept `Molecule: dna` records and block RNA/protein/transcript records.
- The strongest verification is the `/api/ncbi/entrez/records/{accession}/analysis` endpoint. If that endpoint returns `moleculeType: DNA`, the record is acceptable for sequence-analysis handoff.

Verified records that returned `moleculeType: DNA` from the local analysis endpoint:

| Organism | Gene shown by API | Accession | Length |
| --- | --- | --- | --- |
| Homo sapiens | NBR1 | DQ478408.1 | 150,505 bp |
| Oryza sativa f. spontanea | LOC_Os09g26830 | MN542935.1 | 194,610 bp |
| Oryza brachyantha | LOC_Os09g26830 | MN542930.1 | 193,568 bp |
| Escherichia coli | lacZ' | FJ404781.1 | 4,082 bp |
| Escherichia coli str. K-12 substr. MG1655 | lacZ | JF300162.1 | 5,579 bp |

Recommended search inputs for these examples:

```text
Gene: BRCA1
Organism filter:
Source: RefSeq + GenBank
Min length: 10000
Max length: 1000000
```

or for a smaller live demo:

```text
Gene: lacZ
Organism filter: Escherichia coli
Source: RefSeq + GenBank
Min length: 1000
Max length: 10000
```

### Verification Examples

Accepted handoff example:

```text
Accession: FJ404781.1
Analysis endpoint: /api/ncbi/entrez/records/FJ404781.1/analysis
Required response property: moleculeType = DNA
Frontend action: Sequence Analysis
```

Rejected handoff example:

```text
Accession: XM_085829552.1
Record type: mRNA
Frontend action: Genomic DNA required
```

Ambiguous-sequence example:

```text
Fetched region: ACGTNNACGT
Molecule type: DNA
Outcome: DNA identity can be valid, but windows containing N are excluded from quantum processing
```

Uracil example:

```text
Fetched sequence: ACGU
Outcome: reject as non-DNA input because U is present
```

### Verification Decision Table

| Molecule/sequence evidence | Quantum handoff |
| --- | --- |
| `moleculeType: DNA`, ACGT-only selected region | Allow |
| DNA record with some IUPAC ambiguity | Allow the record, skip ambiguous windows |
| mRNA/transcript or sequence containing `U` | Block |
| Protein record | Block |
| Title contains `CDS`, but endpoint confirms DNA | Allow; `CDS` alone is not a rejection reason |

## 8. Genome Data Viewer / Taxonomy Tree Feature

Reference:

```text
https://www.ncbi.nlm.nih.gov/gdv?org=apodemus-sylvaticus&group=muroidea
```

Implementation finding:

- NCBI API keys are already integrated through backend environment variables: `NCBI_API_KEY`, `NCBI_TOOL_NAME`, and `NCBI_DEVELOPER_EMAIL`.
- The frontend must not expose the NCBI API key.
- Taxonomy tree data is generated dynamically from NCBI Taxonomy records through the backend.
- Organism images are fetched opportunistically from free Wikimedia/Wikipedia image metadata. If no image is found, the UI shows a no-image state instead of using a hardcoded or copyrighted image.

Implemented behavior:

- `/ncbi/search` includes a right-side Genome Data Viewer panel beside search results.
- Each result with a taxonomy ID can preview its taxonomy tree in that right-side panel.
- `/ncbi/record/:accession` includes a Genome Data Viewer panel beside the record sections.
- The selected organism is highlighted in the broader lineage tree.
- Record and search pages link to:
  - the NCBI organism details route, `/ncbi/organism/:taxId`
  - the corresponding NCBI Genome Data Viewer URL
  - the Wikimedia/Wikipedia image source when an image exists

API endpoint:

```text
GET /api/ncbi/organisms/{tax_id}/genome-viewer
```

Runtime fallback:

- The frontend first calls `/api/ncbi/organisms/{tax_id}/genome-viewer`.
- If the running backend has not been restarted yet and returns 404 for that new endpoint, the frontend falls back to the existing `/api/ncbi/organisms/{tax_id}` endpoint and builds the lineage tree client-side.
- In fallback mode, the frontend performs the free Wikimedia/Wikipedia image lookup directly from the browser.

Response purpose:

- selected organism identity
- broader lineage tree nodes
- highlighted selected organism node
- optional organism image metadata
- NCBI Taxonomy and Genome Data Viewer links

Example requests:

```text
Escherichia coli: GET /api/ncbi/organisms/562/genome-viewer
Homo sapiens: GET /api/ncbi/organisms/9606/genome-viewer
Mus musculus: GET /api/ncbi/organisms/10090/genome-viewer
```

Illustrative response shape:

```json
{
  "taxId": "9606",
  "scientificName": "Homo sapiens",
  "rank": "species",
  "treeNodes": [
    {
      "taxId": "9605",
      "scientificName": "Homo",
      "rank": "genus",
      "isSelected": false
    },
    {
      "taxId": "9606",
      "scientificName": "Homo sapiens",
      "rank": "species",
      "isSelected": true
    }
  ],
  "image": null,
  "links": {
    "taxonomy": "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=9606",
    "genomeDataViewer": "https://www.ncbi.nlm.nih.gov/gdv?org=homo-sapiens"
  }
}
```

The real lineage normally contains more nodes, and `image` may contain Wikimedia metadata instead of `null`.

Example UI flows:

```text
Search result -> Preview Tree -> right-side lineage panel
Search result -> View Organism -> /ncbi/organism/562
Record detail -> Genome Data Viewer -> external NCBI GDV page
```

Example no-image behavior:

```text
Wikimedia lookup returns no usable image
Result: taxonomy tree and links still render; the panel shows a no-image state
```

Design note:

- `Images/flowchart.png` is used as the visual reference for the tree direction and highlighted selected organism concept.
- The implemented tree is dynamic and data-driven, not a static copy of the reference image.

## 9. NCBI Search Result Action Button Layout and Preview Selection

Finding:

- The screenshot `Images/make_vertical_buttons.png` showed the four card actions laid out horizontally, which squeezed the result metadata and made the card hard to scan.
- The search result card action controls should be vertical per card:
  - Preview Tree
  - View Record
  - View Organism
  - Sequence Analysis or Genomic DNA required

Preview tree bug:

- The previous selected-state logic used only `taxId`.
- Multiple search results can share the same organism taxonomy ID, for example several `Homo sapiens` records.
- Because of that, selecting one preview tree highlighted every later card with the same `taxId`.

Fix:

- The tree panel still loads by `taxId`, because taxonomy trees are organism-level data.
- The highlighted `Preview Tree` button is now keyed by selected accession, so only the clicked card appears selected.

### Card Layout Example

```text
FJ404781.1
Escherichia coli | lacZ' | 4,082 bp | DNA

[Preview Tree]
[View Record]
[View Organism]
[Sequence Analysis]
```

Non-DNA example:

```text
XM_085829552.1
Mus caroli | BRCA1 | mRNA

[Preview Tree]
[View Record]
[View Organism]
[Genomic DNA required]
```

### Preview Selection Examples

Two accessions with the same taxonomy ID:

```text
Card A: accession DQ478408.1, taxId 9606
Card B: accession another_human_record, taxId 9606
User clicks Preview Tree on Card B
Expected: both cards refer to the same organism tree, but only Card B's button is highlighted
```

Two accessions with different taxonomy IDs:

```text
Card A: FJ404781.1, taxId 562
Card B: DQ478408.1, taxId 9606
User clicks Card A, then Card B
Expected: the panel changes from Escherichia coli to Homo sapiens and only Card B remains highlighted
```

Missing-taxonomy example:

```text
Record has no taxId
Expected: Preview Tree and View Organism are omitted; View Record remains available
```
