# ADR-0011: Messaging Starter for Inter-Domain Communication

- Status: Accepted
- Date: 2026-02-11

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

We adopt a **tech-agnostic messaging starter** with explicit contract governance, envelope conventions, and failure semantics.

### 1) Messaging Starter Abstraction

The messaging starter provides a **technology-independent messaging API** for publishing and consuming domain events and commands across domain boundaries.

#### Abstraction layer

- **MessagePublisher port**: publishes messages to a logical channel. Domain code depends on this port, never on broker-specific APIs.
- **MessageHandler contract**: domain message handlers implement a narrow handler interface. The messaging middleware (pipeline position 400) enforces idempotency and trace propagation around handler execution.
- **ChannelResolver SPI**: maps logical channel names to physical broker destinations. Default: convention-based mapping (e.g., `domain.event-name` → broker topic/queue).

#### Provider SPI

- The starter defines a **MessagingProvider SPI** for broker integration.
- Default implementation: to be selected per deployment (e.g., Kafka, RabbitMQ, NATS). The SPI contract is defined; the default provider is a deployment decision, not an architecture decision.
- All providers MUST satisfy:
  - At-least-once delivery guarantee.
  - Message header injection for trace propagation (per ADR-0010).
  - Dead-letter routing for unprocessable messages.

### 2) Message Envelope Convention

All messages MUST conform to a standard envelope structure:

```yaml
envelope:
  messageId: <UUID>            # Unique message identifier (idempotency key)
  type: <domain.EventName>     # Fully qualified message type (channel + event/command name)
  schemaVersion: <semver>      # Schema version for this message type (e.g., "1.0.0")
  timestamp: <ISO-8601>        # Publication timestamp
  source: <domain-id>          # Publishing domain identifier
  traceId: <trace-id>          # Correlation ID from trace context
  tenantId: <tenant-id>        # Tenant context from auth context
  payload: <...>               # Message-type-specific payload (governed by schema)
```

Rules:

- `messageId` is mandatory and MUST be unique per logical message emission.
- `schemaVersion` is mandatory and follows semantic versioning.
- `traceId` and `tenantId` are injected automatically by the messaging middleware from the pipeline context.
- `payload` structure is defined per message type in the message schema registry (`specs/messaging/`).

### 3) Contract Governance and Versioning

Message schemas are **governed contracts** and follow explicit evolution rules.

#### Schema location

- Message schemas are defined in `specs/messaging/` as YAML files, one per message type.
- Each schema file defines: message type, schema version, payload fields (name, type, required/optional), and backward compatibility notes.

#### Versioning strategy

- Messages use **semantic versioning** for schema evolution:
  - **Patch** (1.0.x): documentation-only changes, no field changes.
  - **Minor** (1.x.0): additive changes only — new optional fields. Consumers MUST ignore unknown fields.
  - **Major** (x.0.0): breaking changes — field removal, type change, semantic change.
- **Backward compatibility rules**:
  - Minor versions MUST be backward compatible: existing consumers continue working without changes.
  - Major versions require a migration plan: dual-publish during transition, explicit deprecation timeline.
  - New required fields are a **breaking change** (major version).

#### Consumer contract

- Consumers MUST tolerate unknown fields (forward compatibility).
- Consumers MUST validate messages against the declared schema version.
- Consumers MUST NOT depend on field ordering.

### 4) Idempotency Semantics

Per the messaging middleware contract (ADR-0018, pipeline position 400):

- Message handlers MUST be **idempotent** — redelivered messages produce the same outcome.
- The messaging starter provides an **idempotency enforcement mechanism** (e.g., message ID deduplication store).
- Domain handlers declare their idempotency expectations via handler metadata.
- The deduplication store is a **pluggable SPI** (in-memory, database, distributed cache).

### 5) Dead-Letter Handling

- Messages that cannot be processed after the configured retry policy MUST be routed to a **dead-letter channel**.
- Dead-letter messages MUST retain the original envelope (including `messageId`, `traceId`, `tenantId`).
- Dead-letter messages MUST include failure metadata:
  - `failureReason`: canonical Problem object (per ADR-0007 / error registry).
  - `failureTimestamp`: ISO-8601 timestamp.
  - `retryCount`: number of processing attempts.
- Dead-letter monitoring is an operational concern; the starter provides the routing mechanism, not the monitoring UI.

### 6) Channel Naming Convention

Logical channel names follow a consistent pattern:

- Domain events: `<domain>.<aggregate>.<event-name>` (e.g., `auth.user.registered`, `inventory.item.reserved`)
- Domain commands: `<domain>.<aggregate>.<command-name>` (e.g., `cart.order.checkout`)

Rules:

- Channel names are **lowercase kebab/dot-separated**.
- Channel names MUST be stable; renaming a channel is a breaking change.
- Physical broker topic/queue names are derived from logical names by the ChannelResolver SPI.

### Spec impact (transformation targets)

- `specs/architecture/middleware/messaging.md` — already exists; no changes required
- `specs/messaging/` — **new content needed**: message schema files per message type (Level 2+ work)
- `specs/rules/error-registry.md` — messaging failure patterns already defined; no changes required

## Consequences

### Positive

- Tech-agnostic messaging enables broker replacement without domain code changes.
- Explicit envelope convention ensures consistent tracing, tenant isolation, and schema governance across all messages.
- Semantic versioning with backward compatibility rules prevents breaking consumers during evolution.
- Idempotency enforcement at the infrastructure level reduces domain handler complexity.
- Dead-letter handling provides a clear failure recovery path.

### Negative

- Envelope overhead per message (metadata fields).
- Schema governance requires discipline: every message type needs a spec file.
- Idempotency deduplication store is an additional infrastructure dependency.
- Dual-publish during major version transitions increases operational complexity.

## Alternatives Considered

1. **Synchronous HTTP between domains**
   - Rejected: increases coupling and reduces resilience.

2. **Broker-specific code in domain/application layers**
   - Rejected: violates portability and layer boundaries.

3. **Schema-less messaging (untyped payloads)**
   - Rejected: prevents contract governance and makes consumer evolution unpredictable.

## Decision Drivers

- Distributed evolution requires reliable inter-domain communication.
- Observability and error handling must remain consistent.
- Replaceability of messaging backends.
- Contract governance prevents integration surprises at deployment time.
