# Error Registry (Codes, Types, i18n Keys)

This document defines conventions and a lightweight registry for standardized errors across the project.
It supports ADR-0007.

## Goals

- Make error handling consistent across domains and channels
- Ensure error codes and i18n keys are stable and discoverable
- Enable safe evolution (backward compatibility) without guessing semantics

## Canonical fields (summary)

For the canonical error model, see ADR-0007.

Registry responsibilities:

- `code`: stable machine-readable identifier
- `type`: stable problem type identifier (URI)
- `i18n.key`: stable translation key for user-facing copy

## Naming conventions

### Error code (`code`)

`code` MUST be stable and namespaced.

Recommended format:

- `<DOMAIN>.<CATEGORY>.<NAME>`

Examples:

- `AUTH.CREDENTIALS.INVALID`
- `TENANT.ACCESS.FORBIDDEN`

Rules:

- Codes MUST NOT be reused for different meanings.
- Renaming a code is a breaking change and requires a migration plan.
- Prefer creating a new code and deprecating the old one.

### Problem type (`type`)

`type` MUST be a stable URI.

Recommended patterns:

- `https://https://errors.CHANGE_ME.example.com/<domain>/<category>/<name>`
- `urn:problem:<domain>:<category>:<name>`

Rules:

- `type` MUST be stable.
- `type` SHOULD be unique per `code`.

### i18n key (`i18n.key`)

`i18n.key` MUST be stable, UI-friendly, and namespaced.

Recommended pattern:

- `<domain>.<area>.<name>`

Examples:

- `auth.login.invalid_credentials`
- `tenant.access.forbidden`

Rules:

- i18n keys MUST NOT encode variable data; use `i18n.params` for parameters.
- If a key changes, UIs may lose localization; treat key renames as breaking.

## Minimal mapping: HTTP status ↔ category

This table defines the baseline mapping for HTTP APIs.

- 400: `VALIDATION` / malformed input
- 401: `AUTH` / unauthenticated
- 403: `ACCESS` / authenticated but forbidden
- 404: `NOT_FOUND`
- 409: `CONFLICT`
- 422: `VALIDATION` / semantic validation (optional; project decision)
- 429: `RATE_LIMITED`
- 502/503/504: `UPSTREAM` / dependency failure
- 500: `INTERNAL`

Rules:

- Domain services SHOULD prefer the most specific category.
- Avoid 500 for business-rule rejections; use 400/409/422 with stable `code`.

## Common baseline (recommended)

This baseline is intended to keep cross-domain behavior predictable.
Domains MAY define additional codes and types, but SHOULD align with these defaults.

| Scenario | HTTP `status` | `code` | `type` (pattern) | `i18n.key` |
|---|---:|---|---|---|
| Malformed request / generic validation failure | 400 | `COMMON.VALIDATION.FAILED` | `https://https://errors.CHANGE_ME.example.com/common/validation/failed` | `common.validation.failed` |
| Unauthenticated | 401 | `AUTH.UNAUTHORIZED` | `https://https://errors.CHANGE_ME.example.com/auth/unauthorized` | `auth.unauthorized` |
| Forbidden | 403 | `AUTH.FORBIDDEN` | `https://https://errors.CHANGE_ME.example.com/auth/forbidden` | `auth.forbidden` |
| Resource not found | 404 | `COMMON.NOT_FOUND` | `https://https://errors.CHANGE_ME.example.com/common/not-found` | `common.not_found` |
| Conflict (business/state) | 409 | `COMMON.CONFLICT` | `https://https://errors.CHANGE_ME.example.com/common/conflict` | `common.conflict` |
| Rate limited | 429 | `COMMON.RATE_LIMITED` | `https://https://errors.CHANGE_ME.example.com/common/rate-limited` | `common.rate_limited` |
| Upstream unavailable / dependency timeout | 503 | `COMMON.UPSTREAM.UNAVAILABLE` | `https://https://errors.CHANGE_ME.example.com/common/upstream/unavailable` | `common.upstream.unavailable` |
| Unhandled internal error | 500 | `COMMON.INTERNAL.ERROR` | `https://https://errors.CHANGE_ME.example.com/common/internal/error` | `common.internal.error` |

Notes:

- `type` values above use the short form `https://https://errors.CHANGE_ME.example.com` as the project's error base URI.
- For field-level validation errors, use `COMMON.VALIDATION.FAILED` at the top-level plus per-field `errors[]` entries.


## Minimal mapping: messaging failures

Messaging is not HTTP; still, we align to ADR-0007 canonical semantics.

### When to emit a failure event

- Command-style workflows SHOULD emit a domain event like `CommandRejected` containing the canonical Problem object.
- Background processing SHOULD emit `ProcessingFailed` when the failure is meaningful to consumers.

### Suggested mapping

- Validation / business rejection: `status` = 400/409/422 equivalent
- Unauthorized/forbidden (if applicable in async context): `status` = 401/403 equivalent
- Dependency failures: `status` = 503 equivalent
- Unknown/unhandled: `status` = 500 equivalent

Rules:

- Always include `traceId`, `errorId`, and stable `code`.
- Always include `i18n.key` + `i18n.params` (even if no UI consumes it today).
- Do not treat broker-level DLQ metadata as a replacement for domain-level error semantics.

## Versioning and backward compatibility (messaging)

Error objects evolve over time; messaging consumers are often loosely coupled.

Recommended rules:

- Treat the Problem object as a versioned schema.
- Prefer **additive** changes only (adding new optional fields/extensions).
- Do not rename/remove existing fields in a minor evolution.
- If a breaking change is unavoidable:
  - introduce a new event type/version (e.g., `ProcessingFailed.v2`), or
  - use an explicit `schemaVersion` field in the message envelope and support multiple versions during migration.

Minimum envelope recommendations:

- Include `schemaVersion` (string) at the message envelope level.
- Include `traceId` and `errorId` at the envelope level and inside the Problem object (duplication is acceptable for interoperability).


## Registry process (lightweight)

- Each domain owns its own `code` and `i18n.key` namespace.
- The project maintains a shared index (this doc) and expects new codes/keys to be documented here.
- New codes/keys SHOULD be introduced together with:
  - examples in ADR/specs
  - telemetry conventions (e.g., dashboards by `code`)

## Initial baseline (seed)

This section is intentionally small; expand as domains are implemented.

- `AUTH.CREDENTIALS.INVALID` → `auth.login.invalid_credentials` → type `https://https://errors.CHANGE_ME.example.com/auth/credentials/invalid`
- `COMMON.VALIDATION.FAILED` → `common.validation.failed` → type `https://https://errors.CHANGE_ME.example.com/common/validation/failed`
- `COMMON.UPSTREAM.UNAVAILABLE` → `common.upstream.unavailable` → type `https://https://errors.CHANGE_ME.example.com/common/upstream/unavailable`

Add as domains appear:

- `COMMON.NOT_FOUND` → `common.not_found` → type `https://https://errors.CHANGE_ME.example.com/common/not-found`
- `COMMON.CONFLICT` → `common.conflict` → type `https://https://errors.CHANGE_ME.example.com/common/conflict`
- `COMMON.INTERNAL.ERROR` → `common.internal.error` → type `https://https://errors.CHANGE_ME.example.com/common/internal/error`
