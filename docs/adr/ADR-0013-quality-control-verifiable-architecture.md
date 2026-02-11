# ADR-0013: Quality Control and Verifiable Architecture

- Status: Accepted
- Date: 2026-02-11

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

We adopt a **tool-neutral**, **non-bypassable** quality control system based on:

1. a modern test pyramid (multiple test levels),
2. built-in architecture tests,
3. built-in mutation testing.

The contract of this ADR is defined as stable, tool-neutral **quality gate IDs** (`qg.*`) that can be referenced from documentation and CI without leaking build tool topology.

This ADR must remain compatible with:

- ADR-0002 (confirmation gates and auto-activation approach)
- ADR-0016 (tool-neutral gates + multi-repo baseline)
- ADR-0008 (rules must be phrased in testable/verifiable terms)

### Core Principles

- **Tool-neutral**: quality gates are identified by stable `qg.*` IDs; execution is implemented per repository/toolchain.
- **Non-bypassable**: merge/release MUST be protected by required CI checks that run the quality gate tasks.
- **Stable doc-to-exec mapping**: documentation MUST reference gate IDs (and MAY reference repo-local façade tasks/commands), but MUST NOT leak tool-specific module topology.
- **Presence always, quantity by context**: all gate tasks exist; their scope/coverage is configured per component and depends on business interactions and risk.

### Quality Gates as Stable IDs

The baseline gate catalog is defined in specs:

- `specs/rules/quality-gates.md`

Repositories MUST map those gate IDs to concrete tooling via a repository-specific adapter.
The exact test frameworks/tools are intentionally not fixed by this ADR.

### Non-bypassability and CI Contract

- The repository MUST expose a single required CI check (or a small set) that enforces the required gate IDs for the change.
- At minimum, active areas MUST enforce `qg.arch.boundaries` and `qg.tests.unit`.
- Other gate IDs MAY be required depending on context, but MUST be captured via explicit configuration (reviewable diff).

### Context-driven Suite Activation (Objective)

Because test suite selection depends on business components and their interactions, the project MUST make this selection explicit and auditable.

- Each deployable component (project-defined) MUST have a version-controlled **quality profile** that declares which gate IDs from the catalog are required.
- CI MUST enforce the declared profile by running the required gate implementations.
- A required suite MUST NOT be silently skipped. If a required suite has no tests/configured targets, the task MUST fail (or fail via an explicit “not implemented” signal), rather than passing as an empty no-op.

This makes the “quantity by context” rule enforceable without guessing intent from module topology.

Informative examples of objective triggers for declaring suites in a component profile:

- If the component integrates with an external provider/system, declare `tests-contract-external`.
- If the component participates in cross-component user/business flows, declare `tests-e2e` and/or `tests-acceptance`.
- If the component is deployed to an environment, declare `tests-smoke`.
- If the component includes infrastructure adapters (DB/messaging/cache), declare `tests-integration-narrow`.

### Architecture Tests (Minimum Responsibilities)

`tests-arch` MUST, at minimum, verify:

- `domain` and `application` layers are framework-free (no framework coupling)
- domains do not directly depend on other domains (interaction via stable contracts only)
- shared modules remain bounded and do not become a “dumping ground” for business logic
- cross-cutting starters do not contain domain/business logic

### Mutation Testing (Minimum Responsibilities)

`qg.tests.mutation` MUST be present and automated.

Scope MUST target “critical decision logic” (project-defined), such as:

- security/authz decisions
- error mapping / problem response mapping
- idempotency and deduplication rules

Numeric thresholds MAY be introduced later; this ADR only requires that mutation testing is continuously executable and enforced once activated.

### Activation and No-op Policy (Compatibility with ADR-0002)

To avoid blocking greenfield scaffolding while keeping the system non-bypassable, the following policy applies:

- When the backend/frontend is not yet active (per ADR-0002 activation criteria), gate implementations MUST exist and MUST pass in no-op/informational mode.
- Once a code area becomes active (per ADR-0002), required gate IDs become hard merge gates for that area.
- `qg.tests.mutation` MAY remain in no-op/informational mode until mutation testing is considered ready (objective criteria to be defined alongside the implementation), but the gate MUST remain present and MUST be invoked by the required CI checks.

#### Mutation-ready Activation Criteria (Objective)

Mutation testing is considered **ready** (i.e., `qg.tests.mutation` switches from informational/no-op to an enforceable gate) when all of the following are true:

- `qg.tests.mutation` executes a real mutation run (not a stub) and produces a machine-verifiable report artifact.
- The mutation scope is explicitly configured in version control (what modules/packages/classes are in scope and what is excluded).
- At least one mutation target exists in the configured scope (i.e., the mutation run actually generates mutants).

Once mutation testing is considered ready:

- `qg.tests.mutation` MUST fail the build when its configured expectations are not met.
- Required CI checks MUST fail when `qg.tests.mutation` fails.

### Controlled Change (Governance)

- Accepted ADRs MUST NOT be rewritten to change meaning.
- Any change to a quality gate definition MUST be made via a new ADR.
- The previous ADR MUST be marked `Status: Superseded` and SHOULD include a forward reference: “Superseded by ADR-00XX”.

## Consequences

### Positive

- Establishes a stable, verifiable contract for quality gates (gate IDs).
- Makes architecture conformance and mutation testing continuously enforceable once activated.
- Avoids leaking build-tool module topology into documentation.
- Supports evolutionary growth: test scope scales by context without breaking governance.

### Negative

- Requires maintaining gate-to-tool mappings and CI required-check configuration.
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
