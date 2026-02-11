# Architecture Specs

Authoritative architecture specifications live here.

Guidelines:
- Treat specs as the source of truth; code is derived.
- Prefer additive changes via deltas under `specs/deltas/`.
- Keep deployment-dependent infrastructure choices out of core; describe ports/contracts instead.

Key specs:
- Federated UI composition: `specs/architecture/federated-ui-composition.md`
- Backend shell app contract: `specs/architecture/backend-shell-app.md`
- Frontend shells contract: `specs/architecture/frontend-shells.md`
- Domain registry (backend domains): `specs/architecture/domain/` (index: `domains.yaml`)

Registry and integration:
- Workspace registry (multi-repo): `specs/registry/workspace-registry.yaml`
- Repository index contract (`repo.yaml`): `specs/rules/repo-index.md`
- Quality gates catalog (`qg.*`): `specs/rules/quality-gates.md`
