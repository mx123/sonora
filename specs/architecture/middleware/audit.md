# Middleware: Audit Logging

## Metadata

- **Middleware ID:** `mw.audit`
- **Category:** optional
- **Pipeline Position:** 500
- **Implementation Ref:** `repo.backend :: entry.middleware.audit`

## Contract

### Purpose

Provides consistent audit logging for security-sensitive and business-significant operations, correlated with identity, tenant, and trace context. Runs after all mandatory middleware so that auth context, trace context, error handling, and messaging semantics are fully established.

### Preconditions

- Auth context has been established by `mw.auth` (position 100).
- Trace context has been established by `mw.trace` (position 200).
- Error middleware (`mw.error`, position 300) is in place.
- The audit starter is included via build-time dependency; when not included, this middleware does not participate in the pipeline.

### Processing

- Intercepts request/message processing to capture audit-significant events.
- Automatically records security-sensitive operations:
  - Authentication success/failure (delegated from `mw.auth` outcomes).
  - Authorization denial events.
  - Token refresh operations.
- Provides a narrow **audit port** that domain code can invoke explicitly to record domain-specific audit events.
- Correlates all audit records with:
  - `traceId` and `spanId` from the trace context.
  - `userId` and `tenantId` from the auth context.
  - Timestamp (ISO-8601).
  - Operation identifier (request path, message type, or domain-defined action).
- Applies **field filtering** for PII/secrets before persisting audit records:
  - Sensitive fields are masked or hashed according to a pluggable field filter.
  - Audit records MUST NOT contain raw passwords, tokens, or cryptographic keys.

### Postconditions

- Audit records for security-sensitive operations are persisted via the configured audit sink.
- Domain-initiated audit events (via audit port) are persisted with full correlation context.
- No domain state is mutated by the audit middleware itself.
- Audit failures do NOT block request/message processing (fail-open for availability; audit failures are logged as warnings via the trace context).

### Domain port

Domain code MAY depend on a narrow audit port (e.g., `AuditLogger`) to record business-significant events. This port:

- Accepts an event name, a map of contextual attributes, and an optional detail payload.
- Automatically enriches records with auth and trace context (domain code does not need to pass these explicitly).
- Is a no-op when the audit starter is not included (domain code compiles and runs without the audit dependency).

### Sink SPI

Audit event persistence is pluggable via the audit sink SPI:

- **Default implementation:** structured JSON log output correlated with trace context.
- **Alternative implementations:** database table, message queue, external audit service.
- The sink is selected via configuration; multiple sinks MAY be active simultaneously.

## Quality Gates

- `qg.tests.contract` — audit middleware contract tests (security event capture, correlation enrichment, PII filtering, sink delegation)
- `qg.arch.boundaries` — audit middleware resides in infrastructure/adapter layer, not in domain core

## Related

- ADR-0009: Security Starters (Auth + Audit)
- ADR-0005: Stateless JWT in Distributed Domains
- ADR-0018: Middleware Design Principles and Registry
- Backend shell app spec: `specs/architecture/backend-shell-app.md`
