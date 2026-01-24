# ADR-0001: Spec-Driven Development (SDD) + Dedicated LLM Stream

- Status: Proposed
- Date: 2026-01-24

## Context
We are building a greenfield product that must evolve from a **fully functional monolith** into a **highly distributed system**, while keeping the ability to run as a monolith (with limited throughput) at any point in time.

Key constraints:
- Frontend: Web (TypeScript + Vite + React), Mobile (Flutter)
- Backend: Java 21+, Spring Boot, Ports & Adapters (Hexagonal)
- Infrastructure (DB/messaging/object storage) is deployment-dependent and not part of the core project; the project contains only adapters and integration contracts.

We also adopt a Spec-Driven Development approach supported by EventStorming concepts as a minimal alphabet of domain behavior:
- Command: entry point to behavior (not API)
- Event: a fact the system guarantees
- Aggregate: boundary of invariants
- Policy: causal relation / orchestration
- Bounded Context: boundary of evolution

We must support **delta-based evolution** of specifications, because BV/CAP/NFR and other constraints will be added and refined over time.

## Decision
1. **Specs are the single source of truth (SSOT)**. Code and interface descriptions are derived artifacts.
2. Requirements are stored as **per-item specs**:
   - Business Values: one file per `BV-####`
   - Capabilities: one file per `CAP-####`
   - Business Requirements: one file per `BR-####`
   - Non-Functional Requirements: one file per `NFR-####`
3. Traceability is explicit and validated:
   - Cross-requirement links (BV↔CAP↔BR) are stored in `specs/requirements/trace-links.yaml`.
   - Domain trace for a capability is stored in the capability file itself as repo-relative links to domain Command/Event anchors.
4. **Derived-only interfaces**:
   - OpenAPI, AsyncAPI, Structurizr outputs are generated into `docs/derived/` and are never edited as authoritative sources.
5. **Hard rule for implemented capabilities**:
   - If `CAP.status == implemented`, it MUST have non-empty links to domain Commands AND Events (`trace.domain.commands[]`, `trace.domain.events[]`) pointing into `specs/domain/*#CMD-####` and `specs/domain/*#EVT-####`.
6. All changes are made via explicit deltas in `specs/deltas/` and must be reviewable/auditable.

## Decision Drivers
- Controlled evolution by deltas (auditability, reviewability)
- One model supports monolith and distributed deployment modes
- Deterministic generation and reproducibility
- Traceability for impact analysis and governance

## Consequences
Positive:
- Clear, machine-checkable requirements model
- Enforced traceability from business intent to domain behavior
- Deterministic derived artifacts and fewer undocumented decisions

Negative:
- Upfront effort to define schemas and tooling
- Stricter contribution workflow (spec changes require validation)

## Enforcement (CI Gates)
On any PR changing `specs/`:
- Validate YAML files against schemas
- Enforce `id` ↔ filename consistency and unique IDs
- Validate `trace-links.yaml` references and basic coverage:
  - every `CAP-*` links to at least one `BV-*`
  - every `BR-*` links to at least one `CAP-*`
- For `CAP.status == implemented`:
  - enforce non-empty domain command/event links
  - resolve `specs/domain/*.md#CMD-####|EVT-####` anchors
- Regenerate derived docs and fail on non-deterministic diffs

## Notes
This ADR does not prescribe specific DB/messaging/storage technologies; it only requires stable ports/adapters and validated contracts.
