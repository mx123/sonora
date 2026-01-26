# ADR-0009: Security Starters (Auth + Audit)

- Status: Proposed
- Date: 2026-01-26

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

TBD (follow-up ADR).

### Core Principles (optional)

- Auth is stateless and validated locally (no synchronous auth dependency during request handling).
- Audit is opt-in and must not leak secrets/PII.
- Security behavior is provided via narrow, replaceable starter modules.

## Consequences

### Positive

- 

### Negative

- 

## Alternatives Considered (optional)

1. **No shared security starter**
   - Rejected: inconsistent security posture across composed apps.

2. **Centralized auth calls per request**
   - Rejected: violates stateless distributed-domain constraints.

## Decision Drivers (optional)

- Consistent security posture across any domain composition.
- Local JWT validation requirements.
- Ability to add audit without forcing it on every domain.
