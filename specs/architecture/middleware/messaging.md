# Middleware: Messaging Semantics

## Metadata

- **Middleware ID:** `mw.messaging`
- **Category:** mandatory
- **Pipeline Position:** 400
- **Implementation Ref:** `repo.backend :: entry.middleware.messaging`

## Contract

### Purpose

Provides tech-agnostic messaging integration for the messaging processing path. Enforces idempotent handler semantics and ensures trace propagation within message handling. This middleware applies **only on the messaging path** (not HTTP requests).

### Preconditions

- Auth context and trace context have been established by upstream middleware.
- Error middleware is in place to catch messaging handler failures.
- Inbound message is available.

### Processing

- Extracts message metadata (message ID, correlation ID, headers).
- Enforces **idempotency semantics**: ensures that redelivered messages are handled safely (at-least-once → effectively-once via idempotency checks).
- Propagates trace context from message headers to the handler execution context.
- Delegates to the domain message handler.
- On handler failure: allows `mw.error` (position 300) to handle the exception via the pipeline.

### Postconditions

- Message handlers execute with full auth, trace, and error context.
- Duplicate message deliveries are handled idempotently.
- Trace correlation is maintained from message producer to consumer.
- No domain state is mutated by the messaging middleware itself (idempotency checks are infrastructure-level).

### Domain port

Domain message handlers declare their idempotency expectations explicitly (e.g., via handler metadata or contract annotations). The messaging middleware provides the idempotency enforcement mechanism; the domain declares the semantic requirement.

## Quality Gates

- `qg.tests.contract` — messaging middleware contract tests (idempotent redelivery, trace propagation, handler delegation)
- `qg.arch.boundaries` — messaging middleware resides in infrastructure/adapter layer

## Related

- ADR-0011: Messaging Starter (Inter-domain Communication)
- ADR-0008: Shell Backend Middleware Composition (§ Mandatory Starters — Messaging)
- Backend shell app spec §5.4: Messaging semantics contract
