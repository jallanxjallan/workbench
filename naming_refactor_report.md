# Naming Refactor Report

Date: 2026-02-13
Scope: `/home/jeremy/Workbench` + `/home/jeremy/Autoscribe`

## Before / After

- Legacy canonical typo chain existed in runtime/docs/config generation.
- Canonical identifier is now enforced as:
  - `AUTOSCRIBE_PROJECT_MNEMONIC`
  - `autoscribe_project_mnemonic`
  - `require_project_mnemonic`

## Applied Refactors

1. Canonical env var and function rename
   - `src/asc/core/project_context.py`
   - `src/asc/cli/_shared.py`
   - `lib/py/create_project.py`
2. Reference updates in docs
   - `docs/asc-select.md`
   - `cmd/asc-select/README.md`
3. Added regression coverage
   - `src/asc/tests/test_project_context.py`
4. Added naming policy docs
   - `NAMING_CONVENTIONS.md` in both repos
5. Added policy enforcement hooks/CI
   - `scripts/check_naming_conventions.py` in both repos
   - `.pre-commit-config.yaml` in both repos
   - `.github/workflows/naming-policy.yml` in both repos
6. Generated inventory + automated rename plans
   - `identifier_inventory.json`
   - `rename_plan.json`

## Inventory Metrics

- Combined inventory (Workbench artifact): 3,641 identifiers
- Combined rename plan (Workbench artifact): 231 entries
- AutoScribe inventory: 2,106 identifiers
- AutoScribe rename plan: 190 entries

## Files Touched (This Work Order)

Workbench:
- `.gitignore`
- `lib/py/create_project.py`
- `NAMING_CONVENTIONS.md`
- `identifier_inventory.json`
- `rename_plan.json`
- `scripts/check_naming_conventions.py`
- `tools/naming/generate_identifier_inventory.py`
- `.pre-commit-config.yaml`
- `.github/workflows/naming-policy.yml`

AutoScribe:
- `src/asc/core/project_context.py`
- `src/asc/cli/_shared.py`
- `src/asc/tests/test_project_context.py`
- `docs/asc-select.md`
- `cmd/asc-select/README.md`
- `NAMING_CONVENTIONS.md`
- `identifier_inventory.json`
- `rename_plan.json`
- `scripts/check_naming_conventions.py`
- `.pre-commit-config.yaml`
- `.github/workflows/naming-policy.yml`

## Validation Results

- Naming policy checks:
  - `python3 /home/jeremy/Workbench/scripts/check_naming_conventions.py` -> pass
  - `python3 /home/jeremy/Autoscribe/scripts/check_naming_conventions.py` -> pass
- Workbench scaffold validation:
  - `create_project.py` smoke run in `/tmp` -> pass
  - `.env.local` emits `AUTOSCRIBE_PROJECT_MNEMONIC` only
- AutoScribe tests:
  - `pytest src/asc/tests -q` -> `8 passed`, `0 failed`

## Linter Execution Status

Requested linters were invoked in this environment and not available on PATH:
- `flake8` -> command not found
- `pylint` -> command not found
- `eslint` -> command not found

## Failure Rate

- Regression suite failure rate: `0 / 8 = 0%`
- Naming check failure rate: `0 / 2 = 0%`

## Manual Review Points

- `rename_plan.json` entries are machine-generated candidates and include ambiguous/non-safe renames that should be reviewed before bulk application.
- Inventory artifacts intentionally retain historical identifiers in test and policy-check contexts to verify deprecation behavior.
