# ADR-0010: Observability Starters (Trace + Errors)

- Status: Proposed
- Date: 2026-01-26

## Context

ADR-0008 requires mandatory starters for traceability and error handling to ensure consistent behavior across any shell-backend composition.

This ADR groups:

- **Trace starter**: correlation/trace propagation across REST + messaging + logs.
- **Errors starter**: RFC 9457 problem responses for REST and a canonical Problem model for failures.

This ADR must remain compatible with:

- ADR-0007 (RFC 9457 Error Handling with i18n)
- ADR-0008 (Shell Backend Middleware Composition via Build-Time Domain Inclusion)

Backbone technologies must remain tech-agnostic. However, we will define a reference mapping to OpenTelemetry concepts to enable a default implementation.

## Decision

TBD (follow-up ADR).

### Core Principles (optional)

- Correlation and error identifiers are end-to-end and consistent.
- Error payloads must not leak secrets/PII; diagnostics live in correlated logs.
- Tech-agnostic abstractions with an OpenTelemetry mapping for default implementations.

## Consequences

### Positive

- 

### Negative
- 

## Alternatives Considered (optional)

1. **Ad-hoc per-domain logging and error responses**
   - Rejected: breaks cross-domain troubleshooting and frontend consistency.

2. **OpenTelemetry-only, no abstraction**
   - Rejected: conflicts with tech-agnostic requirement.

## Decision Drivers (optional)

- Frontend needs consistent error model and trace correlation.
- Operability and incident response depend on cross-service traceability.
- Replaceability and co-existence of implementations.
