# ADR-0008: Shell Backend Middleware Composition via Build-Time Domain Inclusion

- Status: Proposed
- Date: 2026-01-26

## Context

This project is designed to evolve from a **modular monolith** into a **partially / fully distributed system** while preserving the ability to run multiple domains together and to extract a domain into an independent service later.

Earlier decisions established domain boundary principles:

- Each domain is a potential service.
- Domains separate API contracts, domain core, application orchestration, and infrastructure wiring.
- Domain core and application logic are framework-free.
- Domains do not depend on each other directly; interaction happens only through `api`.
- Persistence is a domain boundary.

We also have global cross-cutting decisions that must hold regardless of which domains are composed into a given runtime:

- Stateless JWT model across distributed domains (ADR-0005).
- Standardized error model based on RFC 9457 with i18n extensions (ADR-0007).

We need a backend “shell” application that can host **any composition of domains** and provide a stable REST interface to frontend middleware (where frontend composition provides a seamless experience). The backend shell must also provide consistent cross-cutting behavior (auth, errors, traceability, inter-domain messaging) without polluting domain code or re-implementing these concerns per app.

Important constraints:

- Documentation under `docs/` is governed by `docs/constitution.md` (English, ADR format and immutability rules).
- Specs are SSOT and derived artifacts are not authoritative (`specs/constitution.md`).
- Changes must remain controllable as the system grows: architectural rules must be phrased in a way that can be verified by tests (modern test pyramid), architecture tests, and mutation testing (detailed governance in a follow-up ADR).

## Decision

We will implement backend composition as a **Shell Backend** pattern that composes domains using **build-time inclusion** and an explicit **domain container registration** contract.

### Core Principles

- **Build-time composition is the primary mechanism.** A domain is “included” if its infrastructure module is present on the application classpath. Runtime toggles may exist, but are explicitly secondary.
- **Framework code is confined to infrastructure wiring.** Domain and application layers remain framework-free.
- **Backbone technologies are tech-agnostic.** Each starter provides a stable abstraction with pluggable implementations selected by configuration.
- **REST-only external interface (for now).** The shell backend exposes REST APIs only. This does not prevent future adoption of other protocols via new ADRs.
- **Compliance is testable.** Every rule below must be expressible as something that can be verified (tests and/or architecture rules).

### Composition Contract

- The runtime composition lives in the backend Shell App for a Service.
- Each domain provides an explicit domain container registration entrypoint in its integration layer.
- A shell backend application includes a domain by adding a build-time dependency on the domain container package/module (directly or via a domain starter artifact).

### Minimal Included / Excluded Semantics

- **Excluded domain (build-time):** If a domain is not on the classpath, it MUST NOT contribute any REST endpoints, message consumers, scheduled jobs, or persistence/caching components.
- **Included domain (build-time):** If a domain is on the classpath, it MAY contribute endpoints and runtime behavior, but MUST comply with the mandatory starter contracts defined below.

### Mandatory Starters (Required)

Any production backend service that exposes REST APIs and/or consumes/publishes messages MUST include the following narrow starters:

1. **Auth starter**
   - Enforces local JWT validation.
   - Provides the necessary tenant/request context to downstream concerns.

2. **Errors starter**
   - Enforces RFC 9457 problem responses for REST APIs.
   - Provides a canonical Problem model that can also be used for messaging failures.

3. **Trace starter**
   - Enforces correlation/trace propagation across inbound REST requests, outbound calls, messaging, and logs.

4. **Messaging starter**
   - Provides tech-agnostic messaging integration.
   - Enforces idempotent handler semantics and trace propagation when enabled.

Notes:

- The detailed guarantees, configuration model, and mappings (including OpenTelemetry mapping for observability) are specified in follow-up ADRs.
- All backbone technologies remain replaceable and may co-exist (e.g., different messaging backends in different environments) as long as the starter abstractions remain stable.

### Optional Starters

A shell backend MAY additionally include the following starters depending on domain/business needs:

- **Audit starter (optional but important):** integrates audit logging (e.g., via Inspektr). Defined in a follow-up ADR.
- **Persistence starter:** provides persistence integration for stateful domains. Defined in a follow-up ADR.
- **Cache starter:** provides caching integration.
  - **Two-level caching model:**
    - Domain-level caches are provided via the domain/cache starter and remain domain-scoped.
    - Cross-domain caches are allowed only at the shell application level (explicit and intentional).

### Controlled Evolution (Verifiability)

- The rules in this ADR MUST be implementable in a way that can be verified by:
  - layered testing aligned to a modern test pyramid,
  - architecture tests that enforce dependency and layering rules,
  - mutation testing for critical logic.

The detailed testing governance and CI enforcement approach is defined in a dedicated follow-up ADR.

### Spec Impact (Transformation Targets)

This ADR is expected to transform into spec updates in these areas (see `specs/constitution.md` mapping table):

- `specs/architecture/` (composition topology and constraints)
- `specs/adapters/` (REST adapter conventions)
- `specs/messaging/` (inter-domain messaging rules)
- `specs/rules/` (machine-checkable rules for layering and starter compliance)

## Consequences

### Positive

- Enables partial domain compositions (including BFF-like shells) using build-time dependencies.
- Keeps domain core portable and extractable (preserves ADR-0004 intent).
- Establishes consistent, reusable cross-cutting behavior via narrow, replaceable starters.
- Provides a clear evolution path: more protocols/backends can be added via follow-up ADRs.
- Makes governance enforceable by phrasing rules in testable terms.

### Negative

- Requires disciplined module boundaries and consistent packaging of domain autoconfiguration.
- Increases the number of shared starter modules to design and maintain.
- Tech-agnostic abstraction layers may limit access to some backend-specific features.
- Without dedicated compliance checks, drift is possible; follow-up ADRs must define verification.

## Alternatives Considered

1. **Runtime toggles as the primary composition mechanism**
   - Rejected: hides missing dependencies until runtime, makes compositions less reviewable and less testable.

2. **Framework-specific module systems for module boundaries**
   - Rejected: conflicts with portability/extraction goals.

3. **Per-application bespoke wiring without shared starters**
   - Rejected: leads to inconsistent cross-cutting behavior and duplication across apps.

## Decision Drivers

- Evolution from modular monolith to distributed system.
- Need for partial domain compositions (shell/BFF as an instance, not a separate architecture).
- Portability and extractability of domains.
- Consistent cross-cutting behavior (auth, errors, trace, messaging).
- Controlled evolution via verifiable governance.

## Related Decisions

- ADR-0016: Multi-repo baseline and tool-neutral quality gates
- ADR-0005: Stateless JWT in Distributed Domains
- ADR-0007: RFC 9457 Error Handling with i18n
