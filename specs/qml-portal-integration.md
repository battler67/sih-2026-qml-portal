# QML portal integration task record

- Branch: `feature/qml-model-consolidation`, isolated worktree from portal `main` at `7b33ed3`.
- Scope: all local research artifacts inventoried; selected verified Framingham quantum and matched classical bundles plus UCI classical demo promoted; QML pages, service, report and documentation added.
- Preserved: original portal feature branch and uncommitted user changes; independent `qml-research/` checkout and its branch history. Research branches are retained because their experiments and provenance are useful.
- Selection: Framingham seed 11 was predeclared; no test-seed maximization. Matched logistic remains the recommended model. Existing research-only/duplicate artifacts remain in the inventory instead of the serving bundle.
- Verification: source and promoted SHA-256 recorded in manifest; saved held-out prediction replay had zero QKSVM/logistic score difference for five inspected rows and probability differences at floating precision. QML unit/API tests, existing portal suites, build, lint and browser smoke results are recorded in the completion report.
- Deployment: separate Python 3.12 inference service, exact CORS allowlist, no persistence or external clinical-data dispatch.
