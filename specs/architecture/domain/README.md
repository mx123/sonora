# Domain Registry (Backend Domains)

This folder contains the **architecture-level registry** of backend domains that can participate in a Backend Shell App.

- Registered domains are indexed in `domains.yaml`.
- Each registered domain MUST have a dedicated file `DOM-####.yaml` with its detailed metadata.

This registry is **not** a requirements model; it is a discoverability and integration contract.

Related:
- Backend shell contract: `specs/architecture/backend-shell-app.md`
- Workspace registry (multi-repo): `specs/registry/workspace-registry.yaml`
- Per-repo index contract: `repo.yaml` + `specs/rules/repo-index.md`
