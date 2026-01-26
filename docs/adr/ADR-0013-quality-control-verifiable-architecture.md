# ADR-0013: Quality Control and Verifiable Architecture

- Status: Proposed
- Date: 2026-01-26

## Context

The system is expected to evolve over time with controlled change. Architectural rules must remain enforceable rather than aspirational.

ADR-0008 introduces the principle that architectural and middleware constraints MUST be phrased in testable terms.

This ADR defines a governance approach to keep the architecture under control via:

- modern test pyramid practices,
- architecture tests (e.g., for layering and dependency boundaries),
- mutation testing for critical logic.

This ADR must remain compatible with documentation/spec governance in:

- `docs/constitution.md`
- `specs/constitution.md`

## Decision

We adopt a **Gradle-first**, **non-bypassable** quality control system based on:

1. a modern test pyramid (multiple test levels),
2. built-in architecture tests,
3. built-in mutation testing.

The contract of this ADR is defined as **stable root Gradle façade tasks** that can be referenced from documentation and CI without leaking Gradle subproject paths (i.e., without using `:`).

This ADR must remain compatible with:

- ADR-0002 (confirmation gates and auto-activation approach)
- ADR-0004 (Gradle-first, centralized aggregate tasks)
- ADR-0008 (rules must be phrased in testable/verifiable terms)

### Core Principles

- **Gradle-first**: quality gates MUST be executable as Gradle tasks.
- **Non-bypassable**: merge/release MUST be protected by required CI checks that run the quality gate tasks.
- **Stable doc-to-exec mapping**: documentation MUST reference only façade tasks and/or gate IDs, not Gradle subproject paths.
- **Presence always, quantity by context**: all gate tasks exist; their scope/coverage is configured per component and depends on business interactions and risk.

### Quality Gates as Root Façade Tasks

The repository MUST define the following root tasks (names stable):

- `tests-arch` — architecture conformance checks (layering, dependency boundaries)
- `tests-mutation` — mutation testing for critical decision logic
- `tests-unit` — unit tests
- `tests-integration-narrow` — narrow integration tests
- `tests-contract` — internal contract tests
- `tests-component` — component/service-in-a-box tests
- `tests-contract-external` — external system contract tests
- `tests-acceptance` — acceptance tests
- `tests-e2e` — end-to-end tests
- `tests-smoke` — smoke tests
- `tests-ci` — required merge gate aggregate
- `tests-all` — full suite aggregate (profile-driven)

Notes:

- These tasks MAY be implemented via delegation to any underlying module structure.
- The exact test frameworks/tools are intentionally not fixed by this ADR.

### Non-bypassability and CI Contract

- `tests-ci` MUST run as a required CI check for merge.
- `tests-ci` MUST include at least `tests-arch` and `tests-mutation` (see activation policy below).
- Other test levels MAY be included into `tests-ci` depending on context, but MUST be captured via explicit configuration (reviewable diff).

### Context-driven Suite Activation (Objective)

Because test suite selection depends on business components and their interactions, the project MUST make this selection explicit and auditable.

- Each deployable component (project-defined) MUST have a version-controlled **quality profile** that declares which suites from the catalog are required.
- `tests-ci` MUST enforce the declared profile by running the required façade tasks.
- A required suite MUST NOT be silently skipped. If a required suite has no tests/configured targets, the task MUST fail (or fail via an explicit “not implemented” signal), rather than passing as an empty no-op.

This makes the “quantity by context” rule enforceable without guessing intent from module topology.

Informative examples of objective triggers for declaring suites in a component profile:

- If the component integrates with an external provider/system, declare `tests-contract-external`.
- If the component participates in cross-component user/business flows, declare `tests-e2e` and/or `tests-acceptance`.
- If the component is deployed to an environment, declare `tests-smoke`.
- If the component includes infrastructure adapters (DB/messaging/cache), declare `tests-integration-narrow`.

### Architecture Tests (Minimum Responsibilities)

`tests-arch` MUST, at minimum, verify:

- `domain` and `application` layers are framework-free (no Spring or equivalent)
- domains do not directly depend on other domains (interaction via stable contracts only)
- shared modules remain bounded and do not become a “dumping ground” for business logic
- cross-cutting starters do not contain domain/business logic

### Mutation Testing (Minimum Responsibilities)

`tests-mutation` MUST be present and automated.

Scope MUST target “critical decision logic” (project-defined), such as:

- security/authz decisions
- error mapping / problem response mapping
- idempotency and deduplication rules

Numeric thresholds MAY be introduced later; this ADR only requires that mutation testing is continuously executable and enforced once activated.

### Activation and No-op Policy (Compatibility with ADR-0002)

To avoid blocking greenfield scaffolding while keeping the system non-bypassable, the following policy applies:

- When the backend/frontend is not yet active (per ADR-0002 activation criteria), the façade tasks MUST exist and MUST pass in no-op/informational mode.
- Once a code area becomes active (per ADR-0002), `tests-ci` becomes a hard merge gate for that area.
- `tests-mutation` MAY remain in no-op/informational mode until mutation testing is considered ready (objective criteria to be defined alongside the implementation), but the task MUST remain present and MUST be invoked via `tests-ci`.

#### Mutation-ready Activation Criteria (Objective)

Mutation testing is considered **ready** (i.e., `tests-mutation` switches from informational/no-op to an enforceable gate) when all of the following are true:

- `tests-mutation` executes a real mutation run (not a stub) and produces a machine-verifiable report artifact.
- The mutation scope is explicitly configured in version control (what modules/packages/classes are in scope and what is excluded).
- At least one mutation target exists in the configured scope (i.e., the mutation run actually generates mutants).

Once mutation testing is considered ready:

- `tests-mutation` MUST fail the build when its configured expectations are not met.
- `tests-ci` MUST fail when `tests-mutation` fails.

### Controlled Change (Governance)

- Accepted ADRs MUST NOT be rewritten to change meaning.
- Any change to a quality gate definition MUST be made via a new ADR.
- The previous ADR MUST be marked `Status: Superseded` and SHOULD include a forward reference: “Superseded by ADR-00XX”.

## Consequences

### Positive

- Establishes a stable, verifiable contract for quality gates (Gradle façade tasks).
- Makes architecture conformance and mutation testing continuously enforceable once activated.
- Avoids leaking Gradle module topology into documentation (no `:` coupling).
- Supports evolutionary growth: test scope scales by context without breaking governance.

### Negative

- Requires maintaining façade tasks and CI required-check configuration.
- Mutation testing can be expensive; careful scoping is needed to keep feedback loops reasonable.
- No-op/activation behavior adds complexity to CI plumbing (as per ADR-0002).

## Alternatives Considered (optional)

1. **Rely on review discipline only**
   - Rejected: does not scale and is not deterministic.

2. **Only unit tests, no architecture/mutation tests**
   - Rejected: insufficient to prevent architectural drift.

## Decision Drivers (optional)

- Controlled evolution requires continuous verification.
- Preventing architectural drift is cheaper than refactoring later.
- Confidence for extracting domains into services.
