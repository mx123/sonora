# Backend Shell App (Middleware + Domain Containers)

Status: Adopted (via ADR-0016)

This document specifies the **authoritative, normative** backend Shell App contract.

The goal is to define a **language- and toolchain-agnostic** composition model:
- stable architectural boundaries (domain core remains portable),
- stable cross-cutting behavior (middleware contracts),
- predictable domain inclusion semantics (domain containers).

## 1) Terms

- **Service**: a deployable unit.
- **Shell App (backend)**: the host application for a Service that composes domain containers and enforces cross-cutting behavior.
- **Domain core**: domain + application logic that is framework-agnostic.
- **Domain container**: the domain’s integration layer for a Service (routes/handlers/consumers/wiring).
- **Middleware**: cross-cutting request/message processing stages (auth, errors, tracing, messaging semantics).

## 2) Composition intent

- A Shell App MUST be able to host any composition of domains.
- A domain MUST be extractable into its own Service without changing its domain core.
- The primary composition mechanism is **build-time inclusion** (dependency inclusion). Runtime toggles MAY exist but are secondary.

## 3) Domain inclusion semantics

- **Included domain (build-time)**: its domain container is present in the Shell App’s build/dependency graph.
- **Excluded domain (build-time)**: it MUST contribute none of the following at runtime:
  - HTTP routes/endpoints
  - message consumers/subscriptions
  - scheduled jobs
  - persistence/caching components

## 4) Domain container contract

A domain container, when included, MAY contribute:
- HTTP routing/handlers for its API
- messaging consumers and publishers (through the messaging contract)
- persistence wiring for its adapters
- cache wiring for domain-scoped caches

A domain container MUST:
- keep the **domain core** framework-free (no framework annotations/imports in domain core)
- expose integration via explicit registration (no hidden side effects)
- obey dependency direction rules defined by `qg.arch.boundaries`

## 5) Mandatory middleware contracts (minimum)

A production backend Shell App that exposes HTTP and/or messaging MUST enforce, at minimum:

1. **Auth context**
   - request identity/tenant context is established early
   - downstream code can access auth context via a narrow abstraction

2. **Error model (RFC 9457 / Problem Details)**
   - HTTP errors MUST be represented via the canonical problem model
   - domain containers MUST NOT invent their own error payload formats

3. **Trace propagation**
   - inbound → outbound correlation MUST be preserved across HTTP and messaging

4. **Messaging semantics**
   - handler idempotency expectations are explicit
   - trace propagation for message handling is enforced

## 6) Boundary rules (hard constraints)

- Domain cores MUST NOT depend on framework, persistence drivers, messaging drivers, or web frameworks.
- Cross-domain interaction MUST be via stable contracts only (not direct coupling).
- Shared code MUST remain bounded and MUST NOT become a dumping ground for business logic.

## 7) Reference implementations (non-normative)

Implementations MAY vary by language, framework, and deployment platform.

This specification intentionally does **not** name specific technologies.
Any concrete stack choices MUST be treated as reference implementations and MUST NOT change the normative meaning of this spec.

## 8) Related governance

- Quality gates: `qg.arch.boundaries`, `qg.tests.contract`

References:
- ADR-0018 (middleware design principles and registry): `docs/adr/ADR-0018-middleware-design-principles-registry.md`
- ADR-0017 (domain composition and registration): `docs/adr/ADR-0017-domain-composition-and-registration.md`
- ADR-0016 (baseline reset): `docs/adr/ADR-0016-multi-repo-registry-quality-gates.md`
- ADR-0008 (shell backend rationale): `docs/adr/ADR-0008-shell-backend-middleware-composition.md`
- Middleware registry: `specs/architecture/middleware/`
- Domain registry: `specs/architecture/domain/`
- Quality gates catalog: `specs/rules/quality-gates.md`
