# Full-Stack GitHub Monorepo

## Target

- Private repository: `battler67/quantum-helix-lab`
- Local assembly directory: `quantum-helix-lab-full`
- Preserve the remote repository's existing `main` history.

## Included source

- Active frontend from `Rit_Grover_project/quantum-helix-lab`
- `quantum_search_api`
- `qgsa_grover`
- `frqi_dna`
- `quantum_dna`
- `docs`, `specs`, representative required artifacts, and environment templates

## Exclusions

- Real credentials and personal configuration
- `.env`, nested `.git`, `node_modules`, build outputs, caches, logs, temporary files
- Duplicate frontend copies
- Bulk generated PNG/QASM/result directories unless required by tests or examples
- Local-only executables and unrelated papers/presentations

## Reproducibility

- Root README with Windows setup and two-terminal startup commands
- Safe placeholder-only `.env.example`
- Root `.gitignore`
- Pinned dependency lockfiles already used by the frontend
- Backend dependencies and scoped test commands

## Verification before push

- Secret-pattern audit: passed; templates contain placeholders only.
- Clean setup script: passed with a new `.venv` and frontend dependency install.
- Backend API suite: 47 passed.
- FRQI suite: 19 passed.
- QGSA suite: 19 passed.
- `quantum_dna` suite: 34 passed.
- Changed frontend source ESLint: passed.
- Frontend production build: passed.
- Git status/diff review and repository size check: passed; 192 files staged,
  no file exceeds 5 MB, and `git diff --cached --check` is clean.
- Fresh-clone-oriented startup path review: passed.

## Publishing

- Commit only the assembled monorepo contents.
- Push without rewriting remote history.
- Verify the remote branch and commit after push.
