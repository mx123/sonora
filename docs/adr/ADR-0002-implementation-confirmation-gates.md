# ADR-0002: Implementation Confirmation Gates (Definition of Done)

- Status: Accepted
- Date: 2026-01-24

## Context
We are using Spec-Driven Development (specs are SSOT). We need a clear, enforceable definition of what it means for work to be "implemented" without freezing the project in early greenfield stages.

We also need the system to evolve from a monolith to a distributed topology while remaining runnable as a monolith.

## Decision
We adopt a two-tier model:

1) **Enforced now (spec-only gates)**
- These gates run on any PR that changes `specs/` and are enforced immediately.
- They are implemented by `tools/spec-ci/validate.py`.

2) **Deferred gates (code quality gates), auto-activated when code appears**
- These gates are defined now, but become mandatory *automatically* when the repository contains real backend/frontend code.
- Before activation, CI checks must run in informational/no-op mode and pass.
- After activation, CI checks become hard merge gates.

### Enforced now (spec-only gates)
On any PR touching `specs/`:
- YAML files validate against schemas in `specs/schemas/`.
- Per-item requirement `id` matches filename for BV/CAP/BR/NFR.
- `specs/requirements/trace-links.yaml` references known IDs and meets minimum coverage:
  - every `CAP-*` realizes at least one `BV-*`
  - every `BR-*` is satisfied by at least one `CAP-*`
- Hard gate for implemented capabilities:
  - if `CAP.status == implemented`, it must include non-empty `trace.domain.commands[]` and `trace.domain.events[]`
  - links must resolve to anchors in `specs/domain/*.md#CMD-####|EVT-####`

### Deferred gates (auto-activated)
Once activated (see criteria below), the following become required for merge:
- Acceptance testing for backend/frontend (project-defined test suites)
- End-to-end testing (cross-component flows)
- Architectural conformance testing (hexagonal boundaries, dependency rules)

Mutation testing is explicitly **deferred** until the codebase and test strategy stabilize.

#### Activation criteria (objective)
These gates become enforceable when **either** backend or frontend is considered *active*.

- **Backend active** when:
  - at least one backend application/module exists with a build descriptor (tool/language-specific), AND
  - at least one production source file exists (excluding tests).
  - The exact descriptors and source roots are a CI detection detail and MUST remain toolchain-agnostic.

- **Web frontend active** when:
  - at least one web frontend application/module exists with a build descriptor, AND
  - at least one production source file exists (excluding tests).

- **Mobile frontend active** when:
  - at least one mobile frontend application/module exists with a build descriptor, AND
  - at least one production source file exists (excluding tests).

If any of the above becomes active, the corresponding gates become mandatory.

## Decision Drivers
- Enforce governance early without blocking greenfield scaffolding.
- Make "implemented" meaningful as soon as real code exists.
- Keep the model auditable and automated.

## Consequences
Positive:
- Immediate spec integrity guarantees.
- A clear, automatic transition to code quality gates.

Negative:
- Requires CI jobs that can run in no-op mode before activation.

## CI Implementation Note
Branch protection can require the CI checks from day 1 because the deferred quality-gate job runs in no-op mode until activation criteria are met, then becomes a hard gate automatically.

## Notes
This ADR documents gates; it does not yet define the CI implementation.
