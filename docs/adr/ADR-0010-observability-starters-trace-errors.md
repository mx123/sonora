# ADR-0010: Observability Starters (Trace + Errors)

- Status: Accepted
- Date: 2026-02-11

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

We adopt a **two-module observability starter model** with mandatory trace and error starters, each providing a tech-agnostic abstraction layer with pluggable implementations.

### 1) Trace Starter

The trace starter provides **end-to-end correlation and trace propagation** across all communication channels (HTTP, messaging, logs).

#### Abstraction layer

The trace starter defines a **tech-agnostic tracing API** consisting of:

- **TraceContext port**: provides `traceId`, `spanId`, `parentSpanId` to any downstream consumer (middleware, domain code, adapters).
- **SpanFactory port**: allows infrastructure code to create child spans for outbound calls. Domain code SHOULD NOT create spans directly — trace propagation is transparent.
- **CorrelationId accessor**: a simplified accessor for `traceId` usable from domain code when explicit correlation is needed (e.g., idempotency keys).

#### Provider SPI

- The starter defines a **TracingProvider SPI** that implementations must satisfy.
- **Default implementation**: OpenTelemetry SDK mapping.
  - `traceId` → W3C Trace Context `traceparent`
  - `spanId` → OpenTelemetry span ID
  - HTTP propagation → W3C `traceparent` + `tracestate` headers
  - Messaging propagation → message header injection
  - Log enrichment → MDC/structured log context injection
- Alternative providers MAY be substituted (e.g., AWS X-Ray, Datadog) by implementing the SPI.

#### Propagation guarantees

- All outbound HTTP calls MUST carry trace headers.
- All outbound messages MUST carry trace headers in message metadata.
- All structured log entries MUST include `traceId` at minimum.
- Trace context is established after auth context (pipeline position 200).

### 2) Errors Starter

The errors starter provides a **canonical error model** based on RFC 9457 Problem Details, applicable to both HTTP responses and messaging failures.

#### Abstraction layer

- **ProblemFactory port**: constructs Problem Detail objects from domain exceptions, applying error code mapping, i18n resolution, and trace correlation.
- **ExceptionMapper SPI**: maps domain/application exceptions to Problem Details (type URI, status code, error code, i18n key).
- **ProblemSerializer**: serializes Problem objects for HTTP responses (JSON) and messaging failure events (canonical envelope).

#### Error mapping conventions

Per ADR-0007 and the error registry (`specs/rules/error-registry.md`):

- Domain exceptions SHOULD declare their mapping via metadata (annotations, exception hierarchy, or explicit mapper registration).
- Unmapped exceptions default to `500 / COMMON.INTERNAL.ERROR` with no internal details exposed.
- All error responses include `traceId` from the trace context for observability correlation.
- i18n resolution (when configured) uses the `i18n.key` from the error registry and user locale.

#### Provider SPI

- **Default implementation**: direct RFC 9457 JSON serialization with trace context injection from the trace starter.
- Alternative serialization formats MAY be supported via SPI (e.g., protobuf for internal messaging).

### 3) Starter packaging model

Both starters follow the packaging contract defined in ADR-0009 §3:

- Single build-time dependency with auto-activation.
- Public contract via narrow ports.
- Default implementation auto-configured.
- Implementation in infrastructure/adapter layer (ADR-0014).
- SPIs for technology pluggability.

### 4) OpenTelemetry reference mapping

This mapping is **informative** (not normative) — it guides the default implementation:

| Abstraction | OpenTelemetry concept |
|------------|----------------------|
| `TraceContext.traceId` | W3C Trace Context `trace-id` |
| `TraceContext.spanId` | OTel Span ID |
| `SpanFactory.createSpan()` | `Tracer.spanBuilder()` |
| HTTP propagation | W3C `traceparent` header via OTel HTTP instrumentation |
| Messaging propagation | OTel messaging semantic conventions (header injection) |
| Log enrichment | OTel Log Bridge API / MDC injection |
| ProblemFactory trace injection | Reads `TraceContext.traceId` for error response correlation |

### Spec impact (transformation targets)

- `specs/architecture/middleware/trace.md` — already exists; no changes required
- `specs/architecture/middleware/error.md` — already exists; no changes required

## Consequences

### Positive

- End-to-end traceability across HTTP, messaging, and logs without domain code awareness.
- Consistent error model across all channels (REST + messaging) based on a single canonical Problem specification.
- Technology pluggability via SPIs — OpenTelemetry is the default but not the only option.
- Error-to-trace correlation enables fast incident response.

### Negative

- Two SPIs (tracing, error mapping) require design and ongoing maintenance.
- OpenTelemetry default implementation carries its own dependency footprint.
- Transparent trace propagation relies on infrastructure correctness — misconfigured outbound clients can break the trace chain.

## Alternatives Considered

1. **Ad-hoc per-domain logging and error responses**
   - Rejected: breaks cross-domain troubleshooting and frontend consistency.

2. **OpenTelemetry-only, no abstraction**
   - Rejected: conflicts with tech-agnostic requirement; locks all domains to OTel SDK.

3. **Combined single observability starter**
   - Rejected: trace and error concerns have different lifecycle and dependency profiles; separate starters allow independent evolution.

## Decision Drivers

- Frontend needs consistent error model and trace correlation.
- Operability and incident response depend on cross-service traceability.
- Replaceability and co-existence of implementations.
