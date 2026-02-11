# ADR-0009: Security Starters (Auth + Audit)

- Status: Accepted
- Date: 2026-02-11

## Context

ADR-0008 defines the shell backend composition model and requires narrow, replaceable starters for cross-cutting concerns.

Security concerns must be consistent across any composition of domains and across both monolith and extracted services.

This ADR groups:

- **Auth starter**: stateless JWT validation, tenant context, authorization integration.
- **Audit starter**: optional but important auditing, correlated to identity/tenant/trace context.

This ADR must remain compatible with:

- ADR-0005 (Stateless JWT in Distributed Domains)
- ADR-0008 (Shell Backend Middleware Composition via Build-Time Domain Inclusion)

## Decision

We adopt a **two-module security starter model** with mandatory auth and optional audit, both packaged as narrow, replaceable starter modules following the pipeline model defined in ADR-0018.

### 1) Auth Starter

The auth starter provides **local, stateless JWT validation** and populates a narrow auth context abstraction for downstream consumers.

#### Starter abstraction contract

The auth starter MUST expose a **narrow port** (e.g., `CurrentIdentity`, `TenantContext`) that domain code and other middleware can depend on without coupling to JWT mechanics or framework specifics.

The abstraction contract:

- `CurrentIdentity`: provides `userId`, `tenantId`, `roles[]`, `scopes[]`, `authLevel`, `sessionId`.
- `TenantContext`: provides `tenantId` with cross-tenant isolation guarantee.
- Both ports are **read-only** and populated once per request/message by the auth middleware (pipeline position 100).

#### Pluggable implementations

- The starter defines a **provider SPI** (Service Provider Interface) for token validation.
- Default implementation: JWKS-based JWT validation (RS256/ES256) with cached public keys.
- Alternative implementations MAY be swapped via configuration (e.g., opaque token introspection for legacy integration).
- All implementations MUST satisfy the same auth context contract.

#### Claim governance

Per ADR-0005:

- `tenant_id` is mandatory; cross-tenant access is forbidden by default.
- Domain-specific business data MUST NOT appear in JWT claims.
- Domains do not call the Auth Domain synchronously during request handling.

### 2) Audit Starter

The audit starter is **optional** (per ADR-0008) and provides consistent audit logging correlated with identity, tenant, and trace context.

#### Opt-in model

- The audit starter is included via build-time dependency (same mechanism as domain inclusion).
- When included, it participates in the middleware pipeline at position 500 (after all mandatory middleware).
- When excluded, no audit side-effects occur and no audit-related code is loaded.

#### Audit event contract

The audit starter MUST provide:

- A narrow **audit port** that domain code can invoke to record audit-significant events.
- Pre-built audit capture for security-sensitive operations (authentication, authorization failures, token refresh).
- Correlation with trace context (`traceId`, `spanId`) and auth context (`userId`, `tenantId`).

#### PII and secrets policy

- Audit records MUST NOT contain secrets (passwords, tokens, keys).
- Audit records MUST NOT contain raw PII unless explicitly configured and documented per-field.
- Sensitive fields SHOULD be masked or hashed.
- The audit starter MUST provide a pluggable **field filter** mechanism for PII handling.

#### Pluggable storage

- The audit starter defines a **sink SPI** for audit event persistence.
- Default implementation: structured log output (JSON) correlated with trace context.
- Alternative implementations: database, message queue, external audit service.
- The sink is selected via configuration.

### 3) Starter packaging model

Both starters follow a consistent packaging contract:

- Each starter is a **single build-time dependency** that activates automatically when on the classpath.
- Each starter exposes its public contract via **narrow ports** (interfaces in the domain/application layer).
- Each starter provides at least one **default implementation** that is auto-configured.
- Starter implementation details reside in the **infrastructure/adapter layer** (per ADR-0014).
- Starters MUST NOT depend on each other's internal implementation; they communicate only via the pipeline context (auth context, trace context, etc.).

### Spec impact (transformation targets)

- `specs/architecture/middleware/auth.md` — already exists; no changes required
- `specs/architecture/middleware/audit.md` — **new**: audit middleware contract (this ADR creates it)
- `specs/architecture/middleware/README.md` — update audit entry from *(follow-up)* to `audit.md`

## Consequences

### Positive

- Consistent security posture across any domain composition without per-app re-implementation.
- Audit is opt-in — domains that don't need audit don't carry the dependency.
- Narrow ports keep domain code decoupled from security infrastructure details.
- SPI-based pluggability enables technology replacement without changing domain or middleware contracts.
- PII filter mechanism prevents accidental data exposure in audit logs.

### Negative

- Maintaining two SPIs (token validation, audit sink) adds design and testing overhead.
- The auth context port is a ubiquitous dependency — changes to its shape require coordinated migration.
- Audit opt-in model requires discipline: security-sensitive domains SHOULD enable audit but are not forced to.

## Alternatives Considered

1. **No shared security starter**
   - Rejected: inconsistent security posture across composed apps.

2. **Centralized auth calls per request**
   - Rejected: violates stateless distributed-domain constraints.

3. **Mandatory audit for all domains**
   - Rejected: unnecessary overhead for domains with no audit requirements; opt-in is sufficient when combined with security review guidance.

## Decision Drivers

- Consistent security posture across any domain composition.
- Local JWT validation requirements (ADR-0005).
- Ability to add audit without forcing it on every domain.
- Technology replaceability via SPI abstraction.
