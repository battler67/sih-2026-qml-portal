# Grover adapter import debug

## Problem

`quantum_search_api/services/quantum/grover_adapter.py` modified `sys.path` at
module import time and then imported `qgsa_grover.qgsa`. The import worked at
runtime from this checkout, but IDE/static analysis could not reliably resolve
the dynamically added source directory.

## Change

- Removed the module-level `sys.path` mutation.
- Imported QGSA through its explicit monorepo source-package path:
  `qgsa_grover.src.qgsa_grover.qgsa`.

## Verification

- `python -m py_compile quantum_search_api/services/quantum/grover_adapter.py`
  passed.
- A minimal 16-shot `GroverSearchEngine.run("A", "A", ...)` completed and
  returned 16 total counts.
- `python -m pytest quantum_search_api/tests -q --disable-warnings` passed:
  33 tests passed with one warning.
