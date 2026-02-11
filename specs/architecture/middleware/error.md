# Middleware: Error Model (RFC 9457)

## Metadata

- **Middleware ID:** `mw.error`
- **Category:** mandatory
- **Pipeline Position:** 300
- **Implementation Ref:** `repo.backend :: entry.middleware.error`

## Contract

### Purpose

Catches exceptions from all subsequent pipeline stages and domain handlers and translates them into standardized RFC 9457 Problem Details responses. Acts as the last-resort error boundary in the pipeline.

### Preconditions

- Auth context and trace context have been established by upstream middleware.
- Inbound request/message is available.

### Processing

- Wraps execution of all downstream stages (position > 300) and the domain handler.
- On unhandled exception:
  - Maps the exception to an RFC 9457 Problem Details representation.
  - Preserves trace correlation ID in the error response.
  - Applies i18n error message resolution when configured (per ADR-0007).
  - Ensures no stack traces or internal details leak to the client.
- On successful execution: passes the response through unchanged.

### Postconditions

- All HTTP error responses conform to the RFC 9457 Problem Details format.
- Messaging failures produce a canonical Problem model for dead-letter/retry handling.
- No domain state is mutated by the error middleware itself.
- Error responses include trace correlation IDs for observability.

### Domain port

Domain code MUST NOT invent custom error payload formats. Domain exceptions SHOULD be translatable to Problem Details via a mapping convention (e.g., exception type → problem type URI, HTTP status code).

## Quality Gates

- `qg.tests.contract` — error middleware contract tests (exception → Problem Details mapping, correlation ID preservation, no internal detail leakage)
- `qg.arch.boundaries` — error middleware resides in infrastructure/adapter layer

## Related

- ADR-0007: RFC 9457 Error Handling with i18n
- ADR-0010: Observability Starters (Trace + Errors)
- Backend shell app spec §5.2: Error model contract
