# ADR-0011: Messaging Starter for Inter-Domain Communication

- Status: Proposed
- Date: 2026-01-26

## Context

ADR-0008 requires a mandatory messaging starter to enable inter-domain communication with consistent guarantees.

Messaging is a backbone concern that must remain tech-agnostic (broker/vendor replaceable). Implementations are selected via configuration.

Key concerns that must be addressed:

- Contract governance and versioning strategy for messages.
- Trace/correlation propagation over messaging.
- Idempotency and retry/redelivery semantics.
- Failure signaling using a canonical Problem model aligned with REST errors.

This ADR must remain compatible with:

- ADR-0007 (RFC 9457 Error Handling with i18n)
- ADR-0008 (Shell Backend Middleware Composition via Build-Time Domain Inclusion)

## Decision

TBD (follow-up ADR).

### Core Principles (optional)

- Tech-agnostic messaging abstractions; implementations are pluggable.
- Handlers are idempotent and safe under retries.
- Failures can be represented as canonical Problem objects.

## Consequences

### Positive

- 

### Negative

- 

## Alternatives Considered (optional)

1. **Synchronous HTTP between domains**
   - Rejected: increases coupling and reduces resilience.

2. **Broker-specific code in domain/application layers**
   - Rejected: violates portability and layer boundaries.

## Decision Drivers (optional)

- Distributed evolution requires reliable inter-domain communication.
- Observability and error handling must remain consistent.
- Replaceability of messaging backends.
