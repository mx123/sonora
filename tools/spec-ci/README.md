# spec-ci

Minimal local validation for `specs/`.

## Install

From repo root:

- `python3 -m pip install -r tools/spec-ci/requirements.txt`

## Run

- `python3 tools/spec-ci/validate.py`

## Generate derived artifacts (local)

- Structurizr (Mermaid diagrams): `python3 tools/spec-ci/generate_structurizr.py`

## What it enforces (baseline)

- JSON Schema validation for BV/CAP/BR/NFR, deltas, trace-links
- `id` must match filename for per-item specs
- Coverage via `specs/requirements/trace-links.yaml`:
  - every `CAP-*` realizes at least one `BV-*`
  - every `BR-*` is satisfied by at least one `CAP-*`
- Implemented capability hard gate:
  - `CAP.status == implemented` requires non-empty domain trace lists
  - links must resolve to anchors in `specs/domain/*.md` (e.g. `<a id="CMD-0001"></a>`)

- Domain registry (if present):
  - `specs/architecture/domain/domains.yaml` must list valid `DOM-####` ids
  - each listed domain must have a matching `specs/architecture/domain/DOM-####.yaml`
  - each `DOM-####.yaml` present must be listed in `domains.yaml` (no orphan domain files)
  - `repoId` must exist in `specs/registry/workspace-registry.yaml`
  - `entrypoints.core` and `entrypoints.container` must be `entry.*` IDs
