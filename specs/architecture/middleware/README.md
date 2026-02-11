# Middleware Registry (Backend Shell App)

This folder contains the **architecture-level registry** of middleware that participate in the Backend Shell App request/message processing pipeline.

Each registered middleware has a dedicated spec file describing its contract, ordering position, and implementation reference.

This registry is **not** a requirements model; it is a discoverability and integration contract.

## Pipeline Ordering

| Position | ID             | Category  | Spec File        | Entry-point ID             |
|----------|----------------|-----------|------------------|----------------------------|
| 100      | `mw.auth`      | mandatory | `auth.md`        | `entry.middleware.auth`      |
| 200      | `mw.trace`     | mandatory | `trace.md`       | `entry.middleware.trace`     |
| 300      | `mw.error`     | mandatory | `error.md`       | `entry.middleware.error`     |
| 400      | `mw.messaging` | mandatory | `messaging.md`   | `entry.middleware.messaging` |
| 500      | `mw.audit`     | optional  | `audit.md`       | `entry.middleware.audit`     |
| 600      | `mw.cache`     | optional  | `cache.md`       | `entry.middleware.cache`     |

Position gaps (100-step increments) allow future insertions without renumbering.

## Related

- ADR-0018 (middleware design principles and registry): `docs/adr/ADR-0018-middleware-design-principles-registry.md`
- ADR-0008 (shell backend composition): `docs/adr/ADR-0008-shell-backend-middleware-composition.md`
- Backend shell app spec: `specs/architecture/backend-shell-app.md`
- Domain registry: `specs/architecture/domain/`
- Per-repo index contract: `specs/rules/repo-index.md`
- Workspace registry: `specs/registry/workspace-registry.yaml`
