# Middleware: Auth Context

## Metadata

- **Middleware ID:** `mw.auth`
- **Category:** mandatory
- **Pipeline Position:** 100
- **Implementation Ref:** `repo.backend :: entry.middleware.auth`

## Contract

### Purpose

Establishes request identity and tenant context as the first stage of the middleware pipeline. All downstream middleware and domain handlers can rely on auth context being resolved.

### Preconditions

- Inbound HTTP request or message is available.
- JWT validation keys/configuration are present at startup (fail-fast if missing).

### Processing

- Validates the authentication token (e.g., JWT) from the inbound request/message.
- Extracts identity, tenant, and role/permission claims.
- Populates a narrow **auth context abstraction** accessible to downstream stages and domain code.
- On authentication failure: short-circuits the pipeline with an appropriate error response (delegates to `mw.error` format).

### Postconditions

- Auth context is available to all subsequent pipeline stages and domain handlers via a narrow port/interface.
- No domain state is mutated.

### Domain port

Domain code MAY depend on a narrow auth context port (e.g., `CurrentIdentity`, `TenantContext`) to access the authenticated user/tenant. This port is part of the domain's inbound port contract.

## Quality Gates

- `qg.tests.contract` — auth middleware contract tests (valid token, expired token, missing token, tenant extraction)
- `qg.arch.boundaries` — auth middleware resides in infrastructure/adapter layer, not in domain core

## Related

- ADR-0005: Stateless JWT in Distributed Domains
- ADR-0009: Security Starters (Auth + Audit)
- Backend shell app spec §5.1: Auth context contract
