# Changelog

## Unreleased

- docs: add docs folder for project documentation and document the Azure DevOps pipeline location
- docs: add architecture and configuration guides under docs/
- docs: document Phase 2/3 behavior in README (input validation notes, `--summary-json`, CI coverage gate)
- ci: enforce coverage gate at 75% in CI workflow
- cli: add machine-readable summary output via `--summary-json` for `sync` and `run`

## 0.1.0-alpha.1

- Initial public scaffold for `openreview`
- Added Azure DevOps client for PR threads/comments
- Added MVP sync planner for create/update/close/reopen actions
- Added `openreview sync` CLI command
- Added basic tests and CI workflow
