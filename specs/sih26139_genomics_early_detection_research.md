# SIH26139 genomics and early-detection research

Date: 2026-09-21  
Status: research and feasibility only; no implementation is authorized by this document

## Executive conclusion

Genomics can materially strengthen the SIH26139 platform, but the product must not claim that an arbitrary uploaded DNA sequence can detect an early disease.

The scientifically defensible split is:

1. **Inherited DNA (germline)** can identify some pathogenic variants, carrier states, and inherited predispositions. It usually estimates susceptibility, not whether disease is present now or when it will occur.
2. **Disease-state molecular signals** such as tumor-derived cell-free DNA, somatic variants, methylation, fragmentation, RNA expression, proteins, imaging, and longitudinal clinical measurements can sometimes contribute to early detection. These require a validated specimen, assay, cohort, and intended use; they cannot be reconstructed from a consumer's ordinary germline FASTA.
3. **Common-disease risk** is normally multifactorial. Polygenic scores are probabilistic and population-sensitive, and should be combined with age, family history, clinical biomarkers, environment, and calibrated cohort evidence.
4. **QML is an experimental modelling layer, not clinical validation.** A 2025 systematic review found no consistent empirical QML benefit in digital health and found that only 16 studies used realistic hardware/noisy conditions after rigor screening. The SIH platform should compare QML and strong classical baselines honestly, not promise quantum superiority.

The recommended product concept is therefore a **two-lane Genomic Early-Risk Research Lab**:

- **Lane A — Genomic evidence and referral support:** deterministic variant normalization and evidence lookup, with explicit confidence, provenance, limitations, and clinician/genetic-counsellor review.
- **Lane B — SIH benchmark laboratory:** deidentified cohort-level genomic or multi-omic features used to train and compare classical and quantum models under leakage-safe evaluation. This lane is research-only and does not analyze a real user's genome as a medical diagnosis.

This is more credible, safer, and technically stronger than a single black-box "disease detected from DNA" screen.

## What SIH26139 actually requires

The official SIH page describes a hybrid quantum-classical platform for early disease detection using biomedical data including genomics, imaging, and EHRs. It asks for:

- data ingestion;
- classical preprocessing and feature engineering;
- quantum-enhanced models such as QSVM, QNN, or VQC;
- training and inference workflows;
- explainability;
- accuracy, sensitivity, specificity, efficiency, and generalization comparisons with classical baselines;
- simulator and near-term hardware compatibility; and
- documentation.

It does **not** require that the platform diagnose disease from a personal genome alone, and no mandatory public dataset is named on the official page. This gives the team room to select a defensible endpoint and dataset.

Source: [official SIH26139 entry](https://sih.gov.in/sih2026PS).

## What the existing portal already provides

The active `qml-portal-consolidation` application already has a strong integration base:

- React/TanStack portal and FastAPI genomic backend;
- NCBI Entrez, Datasets, nucleotide/accession, taxonomy, and BLAST-oriented services;
- pasted DNA and FASTA text ingestion, normalized to A/C/G/T;
- bounded genomic windowing, reverse complements, partial NCBI retrieval, and provenance;
- FRQI similarity, Grover exact matching, hybrid fixed-point search, noise experiments, and confirmation-gated hardware execution;
- a separate Python 3.12 QML inference service with checksummed bundles and no model training at request time;
- Framingham and Cleveland research pages, model evidence, calibrated outputs, explicit unavailable states, and ephemeral reports;
- classical comparators and honest evidence that the selected Framingham logistic model outperformed the matched quantum kernel model.

Important current gaps:

- the "uploaded FASTA" control is a text input, not a clinical genome-upload pipeline;
- its 100,000-base A/C/G/T limit and sequence-search semantics cannot represent a whole human genome, genotype confidence, zygosity, structural variants, coverage, genome build, or sample quality;
- NCBI nucleotide search is not the same as ClinVar-based human variant interpretation;
- the QML service explicitly has no DNA adapter;
- current Framingham and Cleveland models use tabular clinical features, not genomics;
- the portal has no authentication or durable consent/audit/deletion workflow suitable for identifiable human genomic data.

Therefore the existing FASTA workflow must remain a genomic search/research tool. It must not be relabelled as a clinical DNA-risk analyser.

## Can early disease be detected from only a gene sequence?

### Sometimes a genetic condition can be diagnosed or an inherited risk can be identified

For some monogenic disorders, a well-established pathogenic genotype plus the right clinical context can be diagnostic. For other conditions, a germline variant can indicate elevated lifetime risk or a carrier state. CDC describes genetic testing as capable of diagnosing some genetic conditions or informing risk; FDA emphasizes that a positive predisposition result does not mean a person will develop the condition, and a negative panel does not eliminate risk.

Sources: [CDC genetic testing overview](https://www.cdc.gov/genomics-and-health/counseling-testing/genetic-testing.html), [FDA direct-to-consumer test limitations](https://www.fda.gov/medical-devices/in-vitro-diagnostics/direct-consumer-tests).

### Usually not for common diseases

Cancer, coronary disease, diabetes, Alzheimer's disease, and most other common disorders reflect many variants plus age, exposures, behaviour, physiology, and chance. A static germline sequence does not show whether disease has begun. Polygenic scores remain probabilities, have population-transfer and ancestry limitations, and are not routinely used as stand-alone clinical tests.

Sources: [NHGRI polygenic risk scores](https://www.genome.gov/es/node/45316), [PGS Catalog ancestry documentation](https://www.pgscatalog.org/docs/ancestry/), [PRS reporting standards](https://www.nature.com/articles/s41586-021-03243-6).

### Genuine molecular early detection needs the right specimen and assay

Cancer illustrates the difference. A validated blood-based assay may look for somatic tumor mutations, methylation, and fragmentation patterns in plasma cell-free DNA. That is not equivalent to uploading a germline FASTA. FDA's approved Shield colorectal screening test uses a controlled blood collection and laboratory process, is limited to an intended population, produces false positives and false negatives, and does not replace colonoscopy.

Source: [FDA Shield approval summary](https://www.fda.gov/medical-devices/recently-approved-devices/shield-p230009).

### "Early" must be defined by time

A cross-sectional cancer-versus-control dataset supports **disease-state classification**, not early prediction. An endpoint is truly predictive only when features are measured before a defined future event, with a stated landmark, horizon, censoring rules, and leakage-safe subject split. Repeated visits from the same person must not cross folds. Case/control collections obtained after diagnosis cannot be marketed as pre-symptomatic detection.

## Input types: what they do and do not support

| Input | Realistic use | Not justified |
| --- | --- | --- |
| Reference or user FASTA | sequence search, motif/mutation-position demonstration, organism/reference comparison | human disease-risk prediction without variant calling and clinical context |
| FASTQ | raw-read QC and variant-calling pipeline when assay metadata and sufficient coverage exist | direct browser inference or trustworthy risk from unvalidated reads |
| BAM/CRAM | aligned-read QC, coverage, variant calling, somatic/germline workflows | interpretation without reference build, sample provenance, and validated pipeline |
| VCF/gVCF | normalized variants, genotype/zygosity, ClinVar matching, research PRS | treating every listed variant as causal or clinically actionable |
| SNP-array export | limited genotype/PRS demonstration when platform, strand, build, and missingness are handled | assuming untested variants are negative |
| RNA-seq/expression matrix | cohort-level disease-state or prognosis research with careful batch control | inherited-risk interpretation or early detection from a single unvalidated sample |
| Plasma cfDNA assay output | research on somatic/methylation/fragmentation signals with assay-specific evidence | deriving tumor signal from ordinary saliva/germline DNA |

For a first personal-genomics prototype, **VCF is the correct abstraction**, not raw A/C/G/T text. The canonical VCF specification is maintained by the HTS specifications project. Variant identifiers should also preserve genome build and normalized representation; GA4GH VRS is designed for consistent exchange.

Sources: [HTS format specifications](https://samtools.github.io/hts-specs/), [GA4GH VRS](https://vrs.ga4gh.org/en/1.2/).

## Evidence and annotation architecture

### ClinVar is useful but is not an automatic diagnosis engine

ClinVar reports assertions submitted by external organizations; it does not independently compute clinical conclusions. The portal must expose:

- condition-specific assertion, not only a global variant label;
- germline versus somatic classification;
- review status/stars;
- submitter count and conflicts;
- last evaluated/release date;
- reference assembly and allele normalization;
- evidence links and citations;
- `VUS` as uncertain, never harmful or benign by default.

Higher-confidence categories include expert-panel and practice-guideline review. Conflicting submissions must remain visible. ClinVar publishes comprehensive weekly XML and summary downloads plus GRCh37/GRCh38 VCF subsets; a pinned release is preferable for reproducibility, while live lookup can show whether the snapshot is stale.

Sources: [what ClinVar is](https://www.ncbi.nlm.nih.gov/clinvar/intro/), [ClinVar review status](https://www.ncbi.nlm.nih.gov/clinvar/docs/review_status/), [ClinVar data access and release cycle](https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/).

### Interpretation requires a five-tier vocabulary and evidence review

The ACMG/AMP framework classifies Mendelian sequence variants as pathogenic, likely pathogenic, uncertain significance, likely benign, or benign using multiple evidence types. A prototype may display existing curated classifications; it should not invent a new clinical classification merely from in-silico scores.

Source: [ACMG/AMP sequence variant interpretation consensus](https://pmc.ncbi.nlm.nih.gov/articles/PMC4544753/).

### NCBI expansion opportunities

The current NCBI layer can be extended without pretending all NCBI data are clinical evidence:

- ClinVar lookup and pinned release metadata;
- dbSNP identifiers only as identifiers/frequency links, not pathogenicity;
- MedGen/condition identifiers and gene-condition context;
- RefSeq transcripts and reference assemblies;
- Variation Services/SPDI-based normalization where appropriate;
- PubMed evidence links;
- explicit separation between reference sequence search and human variant evidence.

For polygenic research, use the PGS Catalog for published scoring files/metadata and the NHGRI-EBI GWAS Catalog for association discovery. A GWAS association is not itself a clinically valid predictor, and a PGS must preserve genome build, effect allele, weight, training/evaluation ancestry, intended phenotype, and licensing.

Sources: [PGS Catalog](https://www.pgscatalog.org/), [PGS scoring files](https://www.pgscatalog.org/downloads/), [GWAS Catalog API](https://www.ebi.ac.uk/gwas/rest/api/v2/docs).

## Candidate feature portfolio

### Tier 1 — realistic and recommended for the first implementation plan

1. **Input-purpose gate**
   - Ask whether the user has a reference sequence, VCF, SNP-array export, or a synthetic demo.
   - Explain what each input can support before accepting data.
   - Keep real personal genomes disabled until consent, authentication, deletion, audit, and security controls exist.

2. **Synthetic/deidentified VCF evidence explorer**
   - GRCh37/GRCh38 declaration, contig/allele checks, normalization, duplicate handling, genotype and quality display.
   - Strict size, decompression, line-count, and time limits.
   - Demo fixtures only at first; no raw identifiable genomes committed or logged.

3. **ClinVar evidence cards**
   - Variant-condition classification, stars/review status, conflicts, last update, citations, and `VUS` handling.
   - Clear wording: "curated evidence match," not "disease detected."

4. **Actionability-oriented hereditary risk pathway**
   - Begin with a narrow condition family rather than "all diseases."
   - Familial hypercholesterolemia is the strongest first story because LDLR/APOB/PCSK9 evidence can be combined with LDL cholesterol, age, and family history, and ClinGen lists definitive actionability.
   - Hereditary breast/ovarian cancer and Lynch syndrome are strong alternatives for evidence/referral demonstrations, but they indicate predisposition, not active early cancer.

   Sources: [ClinGen familial hypercholesterolemia actionability](https://actionability.clinicalgenome.org/ac/ui/Adult/ui/stg2SummaryRpt/AC057), [CDC Tier 1 genomic applications](https://archive.cdc.gov/www_cdc_gov/genomics/implementation/toolkit/tier1.htm).

5. **Multimodal research feature builder**
   - Derive a compact, auditable vector such as pathogenic/likely-pathogenic burden, pathway burden, selected validated score, age, biomarker, family history, and missingness indicators.
   - Never encode a raw whole genome directly into a few qubits and call compression an advantage.
   - Each feature must link back to source, transformation, cohort, and timestamp.

6. **Fair classical-versus-QML benchmark**
   - Same participants, folds, preprocessing, feature count, and tuning budget.
   - Fold-local imputation/scaling/feature selection; subject/family/group splits where applicable.
   - Logistic regression, calibrated linear/RBF SVM, and gradient boosting as serious baselines.
   - QKSVM and a small VQC/QNN only on the compact vector.
   - Nested/repeated validation, locked test set, calibration, confidence intervals, and negative results.
   - Report AUROC, AUPRC, sensitivity, specificity, balanced accuracy, calibration/Brier score, decision-curve utility, runtime, circuit executions, shots, depth, and qubits.

7. **Evidence-first result report**
   - Separate `input quality`, `variant evidence`, `research-model output`, and `recommended review`.
   - Avoid a single red/green diagnosis badge.
   - Make unavailable and inconclusive results explicit.
   - Offer a structured FHIR Genomics Reporting export only after the internal schema is stable.

   Source: [HL7 FHIR Genomics Reporting IG](https://hl7.org/fhir/uv/genomics-reporting/).

### Tier 2 — valuable research demonstrations, not personal clinical features

1. **Ancestry-aware PRS sandbox**
   - One preselected, versioned score with published validation and a compatible genotype source.
   - Show variant coverage, missingness, ancestry of development/evaluation cohorts, percentile reference population, and uncertainty.
   - Label as education/research; do not make treatment recommendations.

2. **Longitudinal risk fusion**
   - Combine a static genomic component with changing EHR/biomarker measurements.
   - This is much closer to "early" prediction than sequence alone.
   - Requires a cohort with pre-event timestamps and defensible censoring.

3. **High-dimensional expression/methylation benchmark**
   - Useful for demonstrating classical feature selection followed by small QML models.
   - Must be labelled disease-state classification unless samples truly precede onset.
   - Batch, site, platform, and subject leakage are central risks.

4. **cfDNA educational pathway**
   - Explain somatic mutation, methylation, and fragmentomic signals using a published/deidentified benchmark.
   - No live personal result without a validated assay and clinical-laboratory partnership.

### Tier 3 — do not ship or claim

- "Upload any DNA and detect cancer/heart disease/Alzheimer's early."
- Disease diagnosis from the portal's current 100 kb FASTA text area.
- A pathogenicity conclusion generated by an LLM.
- Treating ClinVar `VUS`, one-star, or conflicting records as actionable positives.
- Sending a personal genome to NCBI BLAST, an AI report provider, analytics, or a cloud QPU without explicit purpose-bound consent.
- A raw-base FRQI/Grover match presented as disease detection.
- Quantum advantage, clinical superiority, or improved sensitivity/specificity based on one split, a tiny smoke dataset, an ideal simulator, or post-hoc model selection.
- Training and testing on different visits, relatives, sites, or batches from the same underlying subject/group.

## Disease/use-case ranking

| Candidate | Scientific fit | Data feasibility | Portal/SIH fit | Recommendation |
| --- | --- | --- | --- | --- |
| Familial hypercholesterolemia risk/referral | strong inherited-risk and prevention story; combine genes with LDL/family history | moderate; evidence demo easy, predictive cohort harder | excellent multimodal and explainable pathway | first choice |
| Hereditary breast/ovarian cancer or Lynch evidence | strong curated predisposition evidence | synthetic VCF demo feasible; clinical validation out of scope | strong NCBI/ClinVar showcase | second choice or second demo |
| Common coronary disease PRS + clinical factors | relevant to existing Framingham work | individual-level genomic/outcome cohort access is difficult; ancestry calibration essential | excellent long-term fusion story | research roadmap, not immediate claim |
| Alzheimer's genomics/PRS | compelling but limited actionability and major population/generalization issues | suitable cohorts often controlled-access | weaker first personal-genome feature | defer |
| Tumor/normal RNA-seq or methylation classification | high-dimensional and QML-friendly | public matrices exist | good benchmark story | research track; label disease-state classification |
| Plasma cfDNA colorectal screening | genuine early-detection modality | needs assay-specific data and wet-lab provenance | high impact but high risk | educational benchmark only |

## Recommended differentiator for SIH

Most competing prototypes can upload a CSV, run a VQC, and display accuracy. The existing portal can offer a much stronger story:

> From biological source and evidence to a bounded hybrid model, with every transformation, limitation, classical comparator, and quantum resource accounted for.

The differentiating demo should show:

1. a synthetic VCF plus clinical/family-history fields;
2. reference-build and quality validation;
3. a ClinVar evidence timeline with review status and conflicts;
4. deterministic feature derivation;
5. identical-fold classical and QML predictions;
6. calibration and uncertainty rather than only accuracy;
7. an explainability view that distinguishes curated variant evidence from model attribution;
8. simulator/noisy/hardware resource cards with no quantum-advantage claim;
9. a consent/deletion simulation and zero external dispatch of the genome; and
10. a report that says inherited predisposition, research classification, or insufficient evidence—not diagnosis.

## QML research requirements

The platform should treat the official objective to "improve" performance as a hypothesis to test, not a result to guarantee. A rigorous experiment needs:

- a predeclared endpoint and analysis plan;
- enough positive events for stable sensitivity and AUPRC estimates;
- train/validation/test separation before feature selection;
- subject/family/site-aware grouping;
- missingness and batch-shift analysis;
- identical reduced features for matched comparisons plus separately labelled full-feature classical references;
- tuned classical baselines;
- repeated seeds/folds and confidence intervals;
- locked threshold selection on training/validation only;
- probability calibration and subgroup performance;
- simulator, finite-shot/noisy, and optional small hardware runs reported separately;
- end-to-end timing including classical preprocessing and encoding;
- model-card and data-card provenance; and
- an explicit result of "no advantage demonstrated" when that is what the evidence shows.

This is consistent with the systematic review finding that QML health evidence currently shows no consistent empirical benefit and that encoding/scaling/noise are often inadequately tested.

Source: [systematic review of QML for digital health](https://www.nature.com/articles/s41746-025-01597-z).

## Privacy, ethics, and product safeguards

Human genomic data is unusually identifying and implicates biological relatives. ICMR notes that an individual's genome remains a unique identity even after attempted anonymization and calls for additional confidentiality safeguards. The final Indian DPDP Rules were notified in November 2025 with a phased compliance timeline; the product will need a current legal review before processing real users' genomes.

Sources: [ICMR 2017 ethical guidelines](https://www.icmr.gov.in/icmrobject/custom_data/pdf/resource-guidelines/ICMR_Ethical_Guidelines_2017.pdf), [MeitY DPDP Rules 2025](https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa?pageTitle=Digital-Personal-Data-Protection-Rules-2025), [GA4GH privacy and security policy](https://www.ga4gh.org/product/data-privacy-and-security-policy/).

Before real personal uploads, require at minimum:

- authenticated users and role-based access;
- specific, informed, revocable consent by purpose;
- separate consent for storage, research reuse, external annotation, and model improvement;
- local-first processing where possible;
- encryption in transit and at rest with managed keys;
- short retention by default and verifiable deletion;
- no request-body, sequence, genotype, or result logging;
- audit events that do not contain genomic payloads;
- no third-party analytics on genomic pages;
- no upload for minors in the hackathon prototype;
- no raw genome sent to LLM, NCBI, or QPU by default;
- incident-response and breach procedures;
- family/secondary/incidental-finding policy;
- genetic-counselling/clinician escalation for potentially serious findings; and
- a synthetic-data demo mode that is the public default.

## Architecture direction for the later implementation plan

No implementation is proposed yet, but the clean boundary is:

```text
User input gate
  -> synthetic VCF / approved cohort feature matrix
  -> validation + genome-build/allele normalization
  -> pinned evidence snapshot (ClinVar/RefSeq) + provenance
  -> deterministic compact feature vector
  -> classical baseline service
  -> bounded QML research service
  -> calibration, comparison, explainability, resource accounting
  -> evidence-first report and optional FHIR export
```

Keep this separate from the existing NCBI sequence-search and Grover/FRQI workflows. Reuse their UI, provenance, job state, bounded execution, and truthful failure patterns, but do not reuse raw sequence matching as the disease model.

## Questions the implementation plan must resolve

1. Is the first disease target familial hypercholesterolemia, hereditary cancer predisposition, or a cohort-level expression benchmark?
2. Will the public MVP accept only synthetic/demo VCFs, or is there authority and infrastructure for real personal genomic data?
3. What exact dataset provides a temporally valid early endpoint, and what are its consent, license, ancestry, phenotype, and redistribution constraints?
4. Is the primary claim inherited-risk evidence, disease-state classification, or future-event prediction?
5. Which evidence release will be pinned, and how will reanalysis/version drift be shown?
6. Which classical models and identical-feature comparisons are mandatory?
7. What minimum sample/event count and repeated validation will be required before a model appears in the portal?
8. Which outputs require a human reviewer, genetic counsellor, or clinician?
9. What data leaves the backend, if any?
10. What is the explicit deletion, audit, and incident-response contract?

## Go/no-go recommendation

**Go** for a genomics integration if it is framed as evidence-backed inherited risk plus a separate cohort-level QML benchmark.

**No-go** for a feature claiming broad early disease detection from a user's raw gene sequence. That claim is not supported by the current portal, the current models, or the biology, and it would create serious privacy and medical-safety risk.

The strongest first planning target is a synthetic/deidentified **familial hypercholesterolemia genomic-risk and referral pathway**, paired with a rigorously benchmarked multimodal research classifier. It gives the team a preventive-health story, combines genetics with real clinical context, makes NCBI/ClinVar integration meaningful, and preserves honest QML evaluation.
