# QML and genomics branch consolidation

Date: 2026-09-22

Target branch: `codex/fh-genomic-risk-pathway`

## Objective

Preserve the current synthetic FH genomics vertical slice, consolidate the
completed QCNN, SIH end-to-end, real-hardware, and unbounded Hybrid work into
the genomics branch, verify the combined application, and remove only local
feature branches that are proven ancestors of the final target.

## Observed topology

- `codex/qcnn-portal-integration` is already an ancestor of
  `codex/sih139-end-to-end-pipelines`.
- `codex/sih139-end-to-end-pipelines` is already an ancestor of
  `codex/qml-real-hardware-execution`.
- `feature/unbounded-hybrid-hardware-testing` contains two unique commits and
  must be merged explicitly.
- `codex/fh-genomic-risk-pathway` currently points at `main`; its FH work is a
  local uncommitted vertical slice and must be checkpointed before merging.

## Execution plan

1. Commit the current FH implementation and this plan on the genomics branch.
2. Merge `feature/unbounded-hybrid-hardware-testing` into
   `codex/qml-real-hardware-execution` and verify the merge.
3. Merge the consolidated real-hardware branch into
   `codex/fh-genomic-risk-pathway`, resolving overlaps without weakening the
   synthetic-only, evidence-first genomics boundaries.
4. Run the production frontend build and the available backend test suites.
5. Confirm all four source branches are ancestors of the genomics branch.
6. Detach any secondary worktree that still has a source branch checked out,
   then delete the four fully merged local source branches.
7. Leave `qml-portal-consolidation` checked out on
   `codex/fh-genomic-risk-pathway` for continued improvement.

## Safety constraints

- Do not push or rewrite published history.
- Preserve unrelated dirty files in the historical
  `feature/qml-portal-integration` worktree.
- Do not delete a branch unless ancestry verification succeeds.
- Keep real genomic uploads disabled; the FH pathway remains synthetic-only.

## Verification log

- Checkpointed the synthetic FH vertical slice as `a39ecfa`.
- Confirmed QCNN is an ancestor of SIH and SIH is an ancestor of the
  real-hardware branch.
- Merged the two unique unbounded-Hybrid commits into the real-hardware line;
  consolidated source commit: `85cb62e`.
- Resolved the combined portal conflicts by retaining the 38-model registry,
  synthetic FH evidence/referral API, runnable BreastMNIST QCNN API, and
  hardware preview/submission routes.
- Promoted the verified QCNN registry entry to `runnable` while retaining all
  other non-replayable imaging records as `evidence_only`.
- `bun run build`: passed, including `/qml/genomics/fh` and `/qml/imaging`.
- QML inference backend: 20 tests passed.
- Unbounded-Hybrid quantum-search scope: 36 tests passed with two dependency
  deprecation warnings.
- Branch ancestry and deletion are completed after the merge commit.

## Post-merge portal integration repair (2026-09-23)

Plan: reproduce the rendered-page timeout separately from static asset serving and
backend health; split eager route component imports so the first SSR request only
loads its own page; reconcile QCNN imaging navigation and model availability tags
without dropping evidence-only experiments; then verify build, tests, both APIs,
and browser-to-API flows. Record observed results here and in the existing
implementation status/user guide. Do not create new Markdown files.
