# Familial hypercholesterolemia genomic-risk and referral pathway

Date: 2026-09-21  
Branch: `codex/fh-genomic-risk-pathway`  
Status: decisions approved; synthetic FH vertical slice implemented and under verification

Decision lock: `1A 2A 3A 4A 5A 6A` approved by the project owner on 2026-09-21. Version 1 is adult-only and synthetic-only; every completed model is catalogued, only replay-verified artifacts are runnable, tags are dataset-local, deterministic evidence/referral remains authoritative, and the first FH QML task is explicitly synthetic rule-reproduction.

## 1. Product decision

The first genomics use case will be a synthetic-data **familial hypercholesterolemia (FH) genomic-risk and referral pathway** inside a broader **Multimodal Early-Risk Research Lab**.

The top-level user journey will require the user to choose one modality:

1. EHR;
2. genomics; or
3. medical imaging.

Every modality will use the same interaction contract:

```text
Choose modality
  -> read purpose and limitations
  -> load a synthetic example or enter allowed fields
  -> inspect validation and preprocessing
  -> run all available classical and QML models
  -> compare model metrics, prediction, cost, and evidence maturity
  -> receive a research-only result and next-step/referral explanation
```

Multimodal fusion will remain visible as a later phase and will not block the three independent pathways.

## 2. Clinical and scientific boundary

This feature will not claim that FH or cardiovascular disease was detected from an arbitrary gene sequence. The defensible output is one of:

- curated pathogenic/likely-pathogenic FH evidence found in a synthetic variant record;
- an FH clinical-suspicion/referral category derived from transparent rules;
- insufficient or uncertain evidence;
- a separate research-model score; or
- input unsuitable for the pathway.

The result language will use `research signal`, `evidence match`, `FH suspicion`, and `referral suggested`. It will not use `diagnosed`, `disease detected`, `you have FH`, or treatment instructions.

The deterministic evidence/referral result is authoritative within the demonstration. QML and classical model outputs are comparative research results and must never overwrite variant evidence, downgrade a referral, or convert a VUS into a positive finding.

## 3. Evidence-supported FH pathway

### 3.1 Synthetic MVP inputs

The first release will use structured synthetic records, not uploaded personal genomes and not VCF parsing.

```json
{
  "example_id": "synthetic-fh-001",
  "synthetic": true,
  "age_years": 34,
  "sex_at_birth": "female",
  "untreated_ldl_c_mg_dl": 232,
  "treated_ldl_c_mg_dl": null,
  "lipid_lowering_treatment": false,
  "family_history_premature_ascvd": true,
  "family_history_high_ldl": true,
  "personal_history_premature_ascvd": false,
  "tendon_xanthomas": false,
  "corneal_arcus_before_45": false,
  "secondary_causes_reviewed": true,
  "variant": {
    "gene": "LDLR",
    "synthetic_variant_id": "SYNTHETIC_LDLR_001",
    "classification": "pathogenic",
    "zygosity": "heterozygous",
    "review_status": "synthetic_expert_panel_equivalent",
    "condition": "familial hypercholesterolemia"
  }
}
```

All examples will carry `synthetic: true` in the API and a permanent visual banner. Synthetic variant identifiers must not resemble real ClinVar accessions.

### 3.2 Input validation

The backend will reject or mark unavailable:

- missing synthetic marker in the public MVP;
- impossible ages or lipid measurements;
- treated LDL-C presented as untreated LDL-C;
- unsupported genes or classifications;
- a VUS presented as pathogenic;
- contradictory zygosity/inheritance examples;
- absent evidence snapshot metadata; and
- attempts to submit raw DNA, FASTA, FASTQ, BAM/CRAM, or VCF to this endpoint.

The existing sequence-search workflow remains separate.

### 3.3 Evidence categories

The synthetic evidence snapshot will use the ACMG/AMP five-tier vocabulary:

- pathogenic;
- likely pathogenic;
- variant of uncertain significance;
- likely benign; and
- benign.

Only pathogenic and likely pathogenic variants with an FH-relevant gene-condition assertion can contribute a positive genomic evidence signal. VUS, conflicting, and missing evidence remain explicitly uncertain. Benign/likely benign does not rule out FH.

The first genes are `LDLR`, `APOB`, and gain-of-function `PCSK9`. `LDLRAP1`, `APOE`, `ABCG5`, `ABCG8`, and `LIPA` belong to a later differential/phenocopy expansion and will not be silently treated as equivalent in version 1.

### 3.4 Transparent clinical-suspicion calculation

The portal may calculate a research reproduction of the Dutch Lipid Clinic Network score from synthetic inputs. Each point contribution must be visible and testable. It is a decision-support demonstration, not a diagnosis.

The rule engine will additionally flag urgent specialist review when the synthetic phenotype resembles possible homozygous FH. Exact pediatric/adult thresholds and age scope are blocked on decision 2 below.

The result object will keep these concepts separate:

```text
input quality
genomic evidence
clinical-suspicion criteria
referral pathway
research-model comparison
limitations and provenance
```

### 3.5 Referral categories

Proposed categories:

- `specialist_review_priority`: very high LDL-C/possible homozygous phenotype or other high-concern combination;
- `fh_specialist_or_genetic_counselling_referral`: P/LP FH evidence or criteria-based probable/definite suspicion;
- `routine_clinical_review`: possible phenotype without high-confidence genomic evidence;
- `uncertain_evidence_review`: VUS/conflicting evidence, with no pathogenic interpretation;
- `insufficient_information`: required phenotype/evidence fields missing; and
- `no_fh_specific_signal_in_this_demo`: no qualifying synthetic signal, explicitly not an all-clear.

The portal will not recommend a medication or dosage. It will explain that confirmatory clinical testing and qualified review are required.

## 4. Pinned synthetic evidence snapshot

Version 1 will ship a local, reviewable fixture such as:

```text
snapshot_id: synthetic-fh-evidence-v1
source_type: synthetic_educational
reference_build: not_applicable
genes: LDLR, APOB, PCSK9
created_at: 2026-09-21
record_count: bounded and test-visible
sha256: recorded in the model/evidence manifest
```

Each record will contain gene, synthetic identifier, condition, classification, review status, mode of inheritance, citations used to design the example, and a human-readable limitation. A checksum will prevent unnoticed changes.

The later real-data phase can replace the adapter with a pinned ClinVar release plus RefSeq/assembly metadata without changing the result contract.

## 5. Model integration strategy

### 5.1 What “all models in the portal” means

The model registry will contain every completed EHR and medical-imaging model with traceable saved metrics. No model is discarded because it performed poorly.

Models have two independent properties:

1. `availability`: `runnable`, `evidence_only`, `unavailable`, or `configured_not_run`;
2. `performance_tag`: `best`, `moderate`, or `experimental`.

This avoids pretending that a CSV metric row is a deployable inference artifact. Every model can appear in the portal immediately as a model card, but only a model with a compatible preprocessing bundle, serialized weights/kernel state, calibration, and verified replay can expose a `Run` action.

### 5.2 Tagging rules

Tags are dataset- and endpoint-specific. EHR, Framingham, BreastMNIST, and WDBC models are never ranked in one global leaderboard.

- `best`: highest predeclared primary metric in its track among completed runs, subject to a valid saved test evaluation;
- `moderate`: completed model with useful discrimination relative to that track but not the leader;
- `experimental`: proof-of-function, weak/unstable metrics, unfair sample comparison, incomplete repetition, configured-only result, or any QML result whose evidence does not support promotion.

Every tag also shows an evidence badge such as `single-seed smoke`, `two tiny folds`, or `three-seed teaching benchmark`. “Best” means best observed in that bounded experiment, never clinically best.

### 5.3 Initial tags from the saved metrics

#### EHR / UCI Cleveland disease-presence classification

Primary ranking metric: held-out AUPRC. All results are a single-seed smoke experiment on 46 test records and are not early prediction.

| Model | Type | AUPRC | AUROC | Balanced accuracy | Proposed tag |
| --- | --- | ---: | ---: | ---: | --- |
| RBF SVM | classical | 0.896 | 0.897 | 0.852 | best |
| Random forest | classical | 0.894 | 0.899 | 0.736 | moderate |
| Linear SVM | classical | 0.878 | 0.910 | 0.865 | moderate |
| Logistic regression | classical | 0.875 | 0.909 | 0.845 | moderate |
| Classical MLP | classical | 0.663 | 0.619 | 0.574 | experimental |
| Pauli OQSVM | quantum kernel | 0.739 | 0.775 | 0.650 | experimental |
| Preferred BCE HQMLP | hybrid QML | 0.583 | 0.621 | 0.572 | experimental |
| Paper-loss HQMLP | hybrid QML | 0.558 | 0.619 | 0.572 | experimental |

The OQSVM/HQMLP models used only 50 balanced training rows while classical models used 212. That is a material evidence limitation and keeps them experimental regardless of a single metric.

#### Medical imaging / BreastMNIST smoke classification

Primary ranking metric: held-out AUPRC, with AUROC and operating-threshold behavior shown alongside it. The test set contained 32 images, so all tags carry a `small smoke test` qualifier.

| Model | Type | AUPRC | AUROC | Balanced accuracy | Proposed tag |
| --- | --- | ---: | ---: | ---: | --- |
| MobileNetV3-Small ImageNet | classical transfer learning | 0.669 | 0.816 | 0.556 | best |
| Small CNN | classical | 0.634 | 0.725 | 0.575 | moderate |
| Logistic regression, same four pooled features | classical matched control | 0.577 | 0.657 | 0.507 | moderate |
| Reduced classical MLP | classical | 0.433 | 0.671 | 0.703 | moderate |
| ResNet-18 ImageNet | classical transfer learning | 0.370 | 0.633 | 0.534 | moderate |
| Four-qubit QCNN | QML | 0.232 | 0.348 | 0.510 | experimental |

The threshold-selected MobileNet sensitivity was unstable because the validation set had only four malignant examples. The UI must show the threshold and sensitivity/specificity rather than relying on the “best” tag alone.

#### WDBC QCNN control

| Model | Type | Mean AUPRC | Mean AUROC | Mean balanced accuracy | Proposed tag |
| --- | --- | ---: | ---: | ---: | --- |
| Logistic regression | classical matched control | 0.937 | 0.967 | 0.808 | best |
| QCNN | QML | 0.481 | 0.575 | 0.475 | experimental |

These are two tiny folds and will appear as a separate WDBC control, not as BreastMNIST evidence.

#### Framingham future-CHD teaching benchmark

All 60 completed model records remain visible. The three-seed summary is a stronger engineering benchmark than a single smoke run, but it uses educational data and overlapping repeated splits.

- `best`: full-feature RBF SVM by mean AUROC (0.760) for the practical classical reference;
- `moderate`: other completed classical controls, including full-feature logistic regression and matched PCA controls;
- `experimental`: all QKSVM, IQP-QKSVM, OQSVM, VQC, and HQMLP variants; Angle QKSVM PCA-2 is labelled the strongest observed quantum result, not the overall best model.

The full registry will ingest the saved Framingham summary rather than hard-code only the three models currently promoted for inference.

### 5.4 FH model plan

The initial FH pathway does not have clinically valid training data. Therefore version 1 will provide:

- a deterministic evidence engine;
- a transparent clinical-suspicion/referral rule engine;
- a synthetic logistic-regression baseline;
- a matched small Angle-QKSVM on the same compact synthetic features; and
- an explicit `synthetic functionality only` evidence badge.

Synthetic labels will test plumbing but cannot establish model accuracy. They must not be used to claim that QML detects FH. If labels are generated directly from the rule engine, the UI will call the experiment `rule-reproduction`, not independent prediction.

Proposed compact research features:

1. normalized untreated LDL-C feature;
2. qualifying P/LP genomic-evidence indicator/strength;
3. family-history evidence feature;
4. phenotype/personal-history feature;
5. missingness flags retained outside or within a bounded expanded representation.

The model output remains separate from the evidence/referral output.

## 6. Common API and UI contract

### 6.1 Registry endpoints

Proposed endpoints:

```text
GET  /v1/lab/modalities
GET  /v1/lab/models?modality=ehr|genomics|imaging
GET  /v1/lab/models/{model_id}
POST /v1/lab/ehr/analyze
POST /v1/lab/genomics/fh/analyze
POST /v1/lab/imaging/analyze
GET  /v1/lab/evidence-snapshots/{snapshot_id}
```

The existing service health, checksum, CORS, no-request-time-training, and truthful unavailable-state patterns will be retained.

### 6.2 Shared model card

Every model card will show:

- model and family;
- modality, dataset, endpoint, and prediction type;
- availability;
- performance tag and why it received the tag;
- AUROC, AUPRC, balanced accuracy, sensitivity, specificity, calibration/Brier when available;
- sample counts, split, seeds/folds, and evidence limitations;
- classical, quantum-kernel, variational/hybrid, or QCNN type;
- qubits, circuit executions, shots/backend, depth/two-qubit gates when measured;
- training/inference time and memory when measured;
- preprocessing and selected features;
- artifact checksums and source run; and
- `Run`, `Evidence only`, or `Unavailable` state.

### 6.3 Genomics FH screen

The FH screen will contain:

1. synthetic example chooser;
2. phenotype/family-history form;
3. synthetic variant evidence card;
4. visible input validation;
5. evidence snapshot card;
6. transparent suspicion-score breakdown;
7. referral explanation;
8. classical-versus-QML research comparison;
9. resource metrics; and
10. exportable ephemeral research report.

No user or relative will be contacted by the prototype. Cascade testing will be explained as a clinician/genetic-counselling next step only.

## 7. Engineering phases

### Phase 0 — decisions and acceptance criteria

- Resolve the six questions below.
- Freeze wording, population, and model availability policy.
- Record acceptance criteria and threat boundaries.

### Phase 1 — unified registry and all-model catalog

- Replace hard-coded selected-model presentation with a versioned registry.
- Import every completed EHR, imaging, WDBC-control, and Framingham summary record.
- Implement tag derivation with unit tests and dataset-specific primary metrics.
- Mark models runnable only after artifact/preprocessing/calibration replay verification.
- Add filters for modality, model family, availability, and tag.

### Phase 2 — multimodal shell

- Add the Multimodal Early-Risk Research Lab landing page.
- Require EHR, genomics, or imaging selection.
- Reuse the shared model card, preprocessing timeline, comparison chart, resource card, and limitation components.
- Preserve existing `/qml` routes with redirects or compatibility links.

### Phase 3 — synthetic FH evidence/referral vertical slice

- Add typed synthetic FH schema and fixtures.
- Add pinned evidence fixture with checksum.
- Implement evidence matching, VUS/conflict handling, suspicion breakdown, and referral state machine.
- Add logistic and Angle-QKSVM rule-reproduction experiment with identical compact features.
- Add API, service, component, and end-to-end tests.

### Phase 4 — runnable EHR and imaging expansion

- Promote every compatible saved EHR model artifact into the inference bundle.
- Add PyTorch-safe loading and architecture/version validation for HQMLPs.
- Promote imaging models only with reproducible preprocessing and saved weights.
- Keep evidence-only cards for models whose artifact replay cannot be verified.
- Never retrain silently in a production request.

### Phase 5 — evidence and reporting hardening

- Add report provenance, checksum, synthetic marker, tag explanation, and limitations.
- Add accessibility and responsive browser verification.
- Add secret/privacy scan and prove genomic payloads are not logged or externally dispatched.
- Record all verification in `specs`.

### Later phase — real VCF/RefSeq/ClinVar

- authenticated and consented upload;
- strict VCF/gVCF validation and resource limits;
- assembly-aware normalization;
- pinned ClinVar release and RefSeq transcript metadata;
- no external dispatch without purpose-specific consent;
- deletion, audit, encryption, incident-response, and human-review workflow;
- clinical/legal review before any real-person deployment.

## 8. Test and verification plan

Minimum automated coverage:

- schema and range validation;
- synthetic-only gate;
- evidence snapshot checksum;
- pathogenic/likely-pathogenic/VUS/conflicting/benign behavior;
- no positive inference from VUS;
- no all-clear from a negative synthetic variant;
- deterministic suspicion-score contributions;
- referral state transitions;
- dataset-local tag calculation and tie handling;
- unavailable/evidence-only model states;
- artifact checksum and prediction replay;
- identical preprocessing for matched classical/QML comparisons;
- no request-time training;
- no payload logging or external network call;
- API contract and CORS;
- keyboard/accessibility checks;
- responsive browser flow from modality selection through report.

## 9. Risks and mitigations

| Risk | Engineering response |
| --- | --- |
| Synthetic labels appear clinically accurate | Permanent synthetic badge; no clinical accuracy claims; label rule-reproduction explicitly |
| “Best” is read as medically approved | Dataset-local tag explanation and evidence-maturity badge on every occurrence |
| Every metric record is assumed runnable | Separate registry availability from performance tag |
| VUS causes alarm | Never treat VUS as positive; show uncertainty and qualified review language |
| Negative gene result becomes an all-clear | Explicitly state that a negative result does not exclude FH |
| QML overrides evidence | Deterministic evidence/referral result is separate and cannot be overwritten |
| Metric leakage or cherry-picking | Predeclare primary metric per track; ingest source metrics and preserve all models |
| Personal genomic data reaches external services | Synthetic-only gate now; later explicit consent and local-first processing |
| Pediatric and adult rules are mixed | Freeze the supported population before implementation |

## 10. Research reading log

The following sources were reviewed for this implementation decision. Papers are recorded with the specific design consequence; guidelines and curated knowledge bases are labelled as such.

1. Sturm et al., **Clinical Genetic Testing for Familial Hypercholesterolemia: JACC Scientific Expert Panel** (2018), DOI `10.1016/j.jacc.2018.05.044`. Supports `LDLR`, `APOB`, and `PCSK9` as the minimum core genes, cascade testing for first-degree relatives, and genetic counselling. [Paper](https://doi.org/10.1016/j.jacc.2018.05.044)
2. Chora et al., **ClinGen FH Variant Curation Expert Panel consensus guidelines for LDLR variant classification** (Genetics in Medicine, 2022), DOI `10.1016/j.gim.2021.09.012`. Supports LDLR-specific ACMG/AMP rules and prevents the portal from inventing pathogenicity from an in-silico model. [Paper](https://pubmed.ncbi.nlm.nih.gov/34906454/)
3. Richards et al., **Standards and guidelines for the interpretation of sequence variants** (Genetics in Medicine, 2015), DOI `10.1038/gim.2015.30`. Provides the five-tier P/LP/VUS/LB/B vocabulary. [Paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC4544753/)
4. Khera et al., **Diagnostic Yield and Clinical Utility of Sequencing Familial Hypercholesterolemia Genes in Patients With Severe Hypercholesterolemia** (JACC, 2016), DOI `10.1016/j.jacc.2016.03.520`. In the studied cohorts, an FH variant occurred in fewer than 2% of people with LDL-C at least 190 mg/dL, while mutation carriers had substantially higher CAD risk; this supports combining genotype and phenotype and avoiding LDL-only or gene-only conclusions. [Paper](https://pubmed.ncbi.nlm.nih.gov/27050191/)
5. Abul-Husn et al., **Familial Hypercholesterolemia in the eMERGE Network: Prevalence, Penetrance, Cardiovascular Risk, and Outcomes after Return of Results** (2023). Supports the actionability/referral story while showing that returning results occurs within consented systems with follow-up and qualified care. [Paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC10113961/)
6. CATCH investigators, **Genetic Cascade Screening for Familial Hypercholesterolemia: A Randomized Clinical Trial** (2026). A secure patient-mediated digital pathway increased testing uptake and new case identification; this supports explaining cascade testing while not directly contacting relatives in the prototype. [Paper](https://pubmed.ncbi.nlm.nih.gov/41973423/)
7. Akyea et al., **Detection of familial hypercholesterolaemia: external validation of the FAMCAT clinical case-finding algorithm** (2019). Supports treating criteria and ML as case-finding/referral aids and not diagnoses; external validation reported stronger discrimination for FAMCAT than several traditional criteria in that population. [Paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC6506568/)
8. **A Scoping Review of Electronic Health Records-Based Screening Algorithms for Familial Hypercholesterolemia** (JACC: Advances, 2024). Supports including classical EHR baselines and highlights incomplete utility/generalizability evidence across populations. [Paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC11733818/)
9. **Systematic identification of familial hypercholesterolaemia: an updated systematic review and meta-analysis** (Atherosclerosis, 2025). Supports EHR case-finding potential but identifies inconsistent referral outcomes and equity/evidence gaps. [Paper](https://www.atherosclerosis-journal.com/article/S0021-9150%2825%2901523-0/fulltext)
10. **Familial hypercholesterolaemia in children and adolescents: a European Atherosclerosis Society consensus statement** (European Heart Journal, 2026). Supports keeping pediatric thresholds/referral and timing distinct from the adult pathway. [Paper](https://academic.oup.com/eurheartj/article/47/26/3324/8691080)
11. NICE, **Familial hypercholesterolaemia: identification and management** (guideline CG71). Supports repeat LDL measurement, referral for DNA testing at specified criteria, specialist confirmation, and cascade testing following an identified familial variant. [Guideline](https://www.nice.org.uk/guidance/cg71/chapter/Recommendations)
12. ClinGen, **Heterozygous Familial Hypercholesterolemia Adult Actionability Summary Report** (curated evidence report). Lists definitive actionability for `LDLR`, `APOB`, and `PCSK9`; the displayed curation has an older literature-search date, so the portal must show snapshot dates. [Evidence report](https://actionability.clinicalgenome.org/ac/ui/Adult/ui/stg2SummaryRpt/AC057)
13. Sowa et al., **A systematic review of quantum machine learning for digital health** (npj Digital Medicine, 2025). Supports keeping QML comparative and experimental because the reviewed literature did not establish consistent empirical advantage. [Paper](https://www.nature.com/articles/s41746-025-01597-z)

Search-result-only items, editorials, Wikipedia pages, Reddit discussions, and unreviewed arXiv FH models were not used as implementation authority.

## 11. Approved decisions

1. **Population:** should version 1 be adults only, or adults plus a clearly separate pediatric synthetic pathway? Recommendation: adults only for the first slice.
2. **Data boundary:** confirm that the public MVP accepts only built-in or manually entered synthetic structured FH records—no real DNA, VCF, or identifiable EHR/image uploads. Recommendation: synthetic only.
3. **Meaning of all models:** should every completed model appear immediately while only verified artifacts are runnable, or must implementation wait until every model has been exported and made runnable? Recommendation: show all model cards now and progressively enable verified inference.
4. **Tags:** approve dataset-local `best`, `moderate`, and `experimental` tags based primarily on AUPRC, always paired with an evidence-maturity qualifier. Recommendation: approve; never rank models across modalities.
5. **FH output authority:** confirm that deterministic genomic evidence plus transparent referral rules are the main result and that QML/classical scores appear only in a separate research comparison. Recommendation: yes.
6. **Synthetic QML target:** is it acceptable to label the first FH logistic/QKSVM experiment `rule-reproduction` when its synthetic labels come from the transparent rule engine, until a licensed genotype-plus-phenotype cohort is available? Recommendation: yes; do not present synthetic accuracy as disease-detection evidence.

## 12. Implementation and verification log

- Created the isolated branch `codex/fh-genomic-risk-pathway`; existing QML research models and artifacts were not modified.
- Added a unified registry containing all 38 completed model records across EHR, genomics, and imaging, with independent performance-tag and runnable/evidence-only fields.
- Added a synthetic adult FH schema, four built-in examples, pinned evidence metadata, transparent suspicion/referral rules, and explicit VUS/negative-result safeguards.
- Added logistic-regression and four-qubit Angle-QKSVM artifacts trained only to reproduce the declared synthetic rule labels. Their metrics are research-pipeline checks, not clinical performance claims.
- Added the multimodal landing flow, FH genomics page, visible preprocessing, evidence snapshot, referral output, model comparison, and model registry filters.
- Backend verification: 9 service/API tests passed, including pathogenic/likely-pathogenic and VUS behavior plus the synthetic-only gate.
- Frontend verification: production build passed; targeted semantic ESLint passed. The repository-wide lint command remains noisy because it scans the pre-existing `.venv-qml` tree and enforces line endings on untouched files.
- Browser end-to-end verification passed against the local services: the modality landing page rendered all 38 records; the pathogenic example produced a 12-point transparent breakdown and specialist/genetic-counselling referral; the VUS example remained `Uncertain Significance` with zero DNA-evidence points; and the pre-existing Framingham Angle-QKSVM synthetic workflow still completed. No browser console errors or warnings were observed.
