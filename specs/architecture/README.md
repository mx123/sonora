# Architecture Specs

Authoritative architecture specifications live here.

Guidelines:
- Treat specs as the source of truth; code is derived.
- Prefer additive changes via deltas under `specs/deltas/`.
- Keep deployment-dependent infrastructure choices out of core; describe ports/contracts instead.
