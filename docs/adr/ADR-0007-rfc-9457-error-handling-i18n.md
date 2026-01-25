# ADR-0007: Standardized Error Handling (RFC 9457) with i18n/l10n

- Status: Accepted
- Date: 2026-01-25

## Context

We operate a multi-domain system that evolves from a modular monolith to distributed services.
Domains are independently developed and deployed, and UIs are composed via a Shell (ADR-0006).
Authentication is stateless JWT-based across domains (ADR-0005).

Today, error handling is underspecified. This creates the following risks:

- Inconsistent API error shapes across domains and channels (HTTP vs messaging vs UI)
- Poor user experience due to non-localizable errors or hard-coded strings
- Operational inefficiency due to missing correlation identifiers and unstable error codes
- Security risk due to accidental leakage of internal details/PII in error payloads

We need a single, cross-project standard for error responses and error semantics that:

- Is interoperable and well-known for HTTP APIs
- Supports localization (translations) and the ability to update UI copy without deployment
- Works across the Shell + Domain UI federation model
- Extends to non-HTTP channels (messaging) without inventing unrelated conventions

## Decision

We standardize error handling across the project using RFC 9457 Problem Details for HTTP APIs,
and an aligned "Problem" envelope for non-HTTP channels.

Localization strategy is hybrid:

- Error payloads MUST always carry translation keys and parameters.
- Error payloads MAY include English fallback text (safe for display), but fallback text MUST NOT be the only usable UX string.

### Core Principles

1. **Single canonical semantics** across domains and channels.
2. **Stable machine-readable codes** for routing, analytics, and support.
3. **Localizable UX**: declare intent as `i18n.key + i18n.params`.
4. **Security by default**: do not leak sensitive details in responses.
5. **Traceability**: every error is correlated and supportable.

### HTTP APIs: RFC 9457 Problem Details

All HTTP APIs MUST return errors as `application/problem+json` using RFC 9457 fields:

- `type` (URI): stable problem type identifier
- `title` (string): short human summary (optional but recommended)
- `status` (number): HTTP status code
- `detail` (string): optional human-readable detail (fallback)
- `instance` (URI/string): a stable identifier for this occurrence (e.g., `/errors/{errorId}`)

#### Standard extensions (required)

All error responses MUST include the following extensions:

- `code` (string): stable internal error code
- `traceId` (string): correlation identifier for logs/traces
- `errorId` (string): unique identifier for this occurrence (support ticket handle)
- `i18n` (object): localization intent
  - `key` (string): translation key
  - `params` (object): interpolation parameters

Recommended optional extensions:

- `domain` (string)
- `service` (string)
- `timestamp` (string, ISO-8601)

#### Error code format

`code` MUST be stable and namespaced. Recommended format:

- `<DOMAIN>.<CATEGORY>.<NAME>` (e.g., `AUTH.CREDENTIALS.INVALID`)

`i18n.key` SHOULD be stable, namespaced, and UI-friendly (e.g., `auth.login.invalid_credentials`).

The conventions and the lightweight registry for `code` / `type` / `i18n.key` are maintained under:

- `specs/rules/error-registry.md`

#### Fallback text rules

- `title` and/or `detail` MAY contain English fallback text safe for end users.
- `title`/`detail` MUST NOT contain secrets, PII, tokens, stack traces, SQL, or internal hostnames.
- Debug details belong in logs, correlated via `traceId` and `errorId`.

### Validation errors

For request validation, the Problem Details payload MUST include an `errors` array extension:

- `errors[]` entries SHOULD include:
  - `path` (string): JSON Pointer or field path
  - `code` (string): field-level error code
  - `i18n.key` + `i18n.params`

### Authentication and authorization errors

- `401` errors MUST use a dedicated `type` (e.g., `https://errors.example.com/auth/unauthorized`) and a stable `code`.
- `403` errors MUST use a dedicated `type` (e.g., `https://errors.example.com/auth/forbidden`) and a stable `code`.

### Non-HTTP channels (Messaging)

RFC 9457 is an HTTP specification. For messaging, we adopt an aligned "Problem" object:

- The Problem object MUST use the same core fields as RFC 9457 (`type`, `title`, `status`, `detail`, `instance`) plus the required extensions (`code`, `traceId`, `errorId`, `i18n`).
- Transport-level failures (broker NACK/DLQ) SHOULD be supplemented by emitting a domain-level failure event when applicable.

Recommended patterns:

- Command-style workflows SHOULD return a domain event such as `CommandRejected` with the Problem object.
- Background processing failures SHOULD emit `ProcessingFailed` with the Problem object and correlation identifiers.

### UI (Web + Mobile) within Federated Composition

To preserve ADR-0006 boundaries:

- Domain UIs MUST NOT embed hard-coded cross-domain error copy.
- The Shell MUST provide a shared i18n facade for resolving `i18n.key + i18n.params`.
- Domain UIs MUST render user-facing errors by resolving translation keys via the facade.
- If the translation key is missing, UIs MAY display the fallback (`title`/`detail`) while also capturing telemetry for missing keys.

This is aligned with the requirement that localization updates are possible without deployment (see NFR-0014).

### Adapter error mapping

Adapters MUST map upstream errors into the canonical format:

- Preserve upstream diagnostics in logs only (correlated via `traceId`/`errorId`).
- Normalize to stable internal `code` and `i18n.key`.

### Rollout plan and feasibility (planning)

Phase 0 (Contract first):
- Define canonical problem types and `code` registry.
- Provide reference examples and a thin library/module per platform.

Phase 1 (HTTP):
- Implement standard exception-to-problem mapping in the API edge (Gateway/BFF) and one pilot domain.

Phase 2 (UI):
- Shell implements the i18n facade + error presentation patterns.
- Domain UIs integrate via the facade (no direct translation coupling between domains).

Phase 3 (Messaging):
- Define failure events + DLQ handling conventions.
- Migrate command workflows to use `CommandRejected` style responses.

Complexity estimate:
- HTTP APIs: Medium
- Gateway/BFF normalization: Medium
- UI (Shell + Domain UI): Medium to Large
- Messaging: Large
- Adapters: Medium

## Consequences

### Positive

- Consistent error semantics across the system
- Better UX via localization-ready errors
- Improved supportability via stable codes and correlation identifiers
- Reduced risk of leaking sensitive internal details

### Negative

- Requires governance for `code` and `i18n.key` registries
- Messaging alignment requires additional conventions and may require rework of existing workflows
- Migration requires temporary backward compatibility and dual-shape tolerance

## Alternatives Considered

1. **Server-only localization (return already-localized strings)**
   - Rejected: conflicts with the requirement that localization updates must be possible without deployment.

2. **Client-only errors (no fallback text, keys only)**
   - Rejected: non-UI consumers and developer experience benefit from safe fallback text.

3. **RFC 7807 only**
   - Rejected: we explicitly standardize on RFC 9457.

## Decision Drivers

- Cross-domain consistency and interoperability
- Federated UI composition constraints (ADR-0006)
- Stateless distributed auth model (ADR-0005)
- Localization agility requirement (NFR-0014)
- Operational excellence (traceability, support, observability)
