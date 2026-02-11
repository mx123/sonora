# Middleware: Trace Propagation

## Metadata

- **Middleware ID:** `mw.trace`
- **Category:** mandatory
- **Pipeline Position:** 200
- **Implementation Ref:** `repo.backend :: entry.middleware.trace`

## Contract

### Purpose

Ensures end-to-end correlation/trace propagation across HTTP requests, outbound calls, messaging, and logs. Runs after auth so that trace context can include authenticated identity information when appropriate.

### Preconditions

- Auth context has been established by `mw.auth` (position 100).
- Inbound request/message is available.

### Processing

- Extracts or generates a **correlation ID** (trace ID, span ID) from inbound request/message headers.
- Propagates trace context to:
  - all outbound HTTP calls,
  - all outbound messages,
  - structured log entries.
- Enriches trace context with request metadata (e.g., service name, operation).

### Postconditions

- Trace context (correlation ID, span ID) is available to all downstream middleware and domain handlers.
- All outbound interactions carry propagated trace headers.
- No domain state is mutated.

### Domain port

Domain code SHOULD NOT depend on trace middleware directly. Trace propagation is transparent — it operates on infrastructure-level context (headers, MDC/thread-local). If domain code needs to access correlation IDs explicitly (e.g., for idempotency keys), a narrow port MAY be provided.

## Quality Gates

- `qg.tests.contract` — trace propagation contract tests (inbound → outbound correlation, header presence, log enrichment)
- `qg.arch.boundaries` — trace middleware resides in infrastructure/adapter layer

## Related

- ADR-0010: Observability Starters (Trace + Errors)
- Backend shell app spec §5.3: Trace propagation contract
