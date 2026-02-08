# Workspace Registry (Multi-repo)

This document defines the central, SSOT-adjacent way to discover and integrate related repositories.

Normative language: **MUST**, **MUST NOT**, **SHOULD**, **MAY** are used as in RFC 2119.

## 1) Purpose

A workspace registry is used to:

- list related repositories (URLs + revisions),
- define minimum expectations for each repository (e.g., root `repo.yaml`),
- support CI/local-dev orchestration without assuming monorepo.

## 2) Registry location

- The registry file **MUST** live under `specs/`.
- Baseline location: `specs/registry/workspace-registry.yaml`.

## 3) Repository requirements

Each listed repository:

- **MUST** have a root `repo.yaml` (see `specs/rules/repo-index.md`).
- **MUST** declare `qualityGates[]` it participates in.

## 4) Tooling integration

- The registry MAY point to a per-repo gate mapping file (tool-specific), but that mapping is not part of `repo.yaml`.
- Tool-specific mapping files MUST remain replaceable; gate IDs remain stable.

Recommended field:
- `repos[].gateMappingPath`: repository-relative path to a tool-specific mapping file.

## 5) Change policy

- Adding/removing repositories **SHOULD** be reviewable and auditable.
- If the registry becomes security-sensitive (e.g., private URLs), it MUST avoid secrets and tokens.
