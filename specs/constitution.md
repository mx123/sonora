# Specs Constitution (Governance)

Last updated: 2026-01-25

This document defines the governance rules for how this repository evolves. It exists to keep changes **reviewable, auditable, and traceable** as the system moves from greenfield specs toward implemented software.

Normative language: **MUST**, **MUST NOT**, **SHOULD**, **MAY** are used as in RFC 2119.

## 1) Source of Truth

1. **Specs are SSOT** (single source of truth).
   - Authoritative intent lives under `specs/`.
   - Code and interface descriptions are derived artifacts.

2. **Derived artifacts are never authoritative**.
   - Anything generated into `docs/derived/` MUST NOT be edited as a source of truth.

3. **ADRs are decision/rationale records**, not the requirements model.
   - ADRs explain *why* and *how* we change specs.
   - ADRs do not replace deltas or requirement specs.

## 2) Governed Artifacts (Delta-Governed)

Deltas are required only for changes that affect the repository’s governed requirements model.

A change is **delta-governed** if it modifies any of the following:

- **Business Values**: `specs/requirements/business-values/BV-####.yaml`
- **Capabilities**: `specs/requirements/capabilities/CAP-####.yaml`
- **Business Rules**: `specs/requirements/business-rules/BR-####.yaml`
- **Non-Functional Requirements**: `specs/requirements/nfr/NFR-####.yaml`
- **Trace graph**: `specs/requirements/trace-links.yaml`

Rules:
- Any PR that changes any delta-governed artifact **MUST** include at least one delta file under `specs/deltas/` that references the affected requirement IDs.
- A PR that only updates non-governed markdown (e.g., `specs/**/README.md`) **MAY** omit deltas.

## 3) Delta Workflow

### 3.1 Delta file format

- A delta file MUST be a YAML file under `specs/deltas/`.
- The delta `id` MUST match: `DELTA-YYYY-MM-DD-NNN`.
- Delta `status` MUST be one of: `draft`, `proposed`, `applied`.
- Each delta `changes[]` entry MUST include:
  - `type`: `add | amend | deprecate | supersede`
  - `target`: a known requirement ID (`BV-*`, `CAP-*`, `BR-*`, `NFR-*`)

### 3.2 When to use which delta status

- Use `draft` while exploring or iterating.
- Use `proposed` when requesting review/approval (typically aligned with a Proposed ADR).
- Use `applied` once the change is merged and becomes part of the baseline.

## 4) ADR → Specs Transformation Policy

### 4.1 ADR status expectations

- New ADRs SHOULD start as `Status: Proposed`.
- An ADR becomes `Accepted` when the team agrees to the decision and the corresponding spec changes are merged.

### 4.2 What happens when a **new Proposed ADR** appears

When a new file appears under `docs/adr/` with `Status: Proposed`, it MUST be treated as a **change proposal** that is transformed into concrete spec changes.

A Proposed ADR PR MUST:

1. **Identify targets**: explicitly list which spec areas are impacted (see mapping table below).
2. **Change specs**:
   - Update or add the relevant specs under `specs/`.
   - If the ADR impacts the requirements model (BV/CAP/BR/NFR and/or `trace-links.yaml`), it MUST follow the delta workflow.
3. **Add/Update deltas (when governed artifacts change)**:
   - Add a delta file in `specs/deltas/` referencing every affected requirement ID.
   - Keep the delta’s title and rationale aligned with the ADR decision.
4. **Preserve traceability**:
   - Ensure `trace-links.yaml` stays consistent and meets coverage gates.
   - If a capability is marked `implemented`, ensure domain command/event traces resolve.

### 4.3 Mapping: ADR topic → spec area(s)

Use this table when transforming ADRs into spec changes:

| ADR topic | Primary spec targets |
|---|---|
| Business intent / product outcomes | `specs/requirements/business-values/` |
| Capability definition / scope | `specs/requirements/capabilities/` |
| Business rule / invariants | `specs/requirements/business-rules/` |
| Non-functional requirement / governance gate | `specs/requirements/nfr/` |
| Cross-requirement traceability | `specs/requirements/trace-links.yaml` |
| Domain behavior alphabet (commands/events) | `specs/domain/commands.md`, `specs/domain/events.md` |
| API surface (derived projections) | `specs/api/` (non-authoritative), generated docs in `docs/derived/` |
| Messaging contracts | `specs/messaging/` |
| Adapter contracts and mappings | `specs/adapters/` |
| Architecture decisions and constraints | `specs/architecture/` |
| Extra machine-checkable rules | `specs/rules/` |
| Change sets / evolution history | `specs/deltas/` |

## 5) Traceability Rules (Minimum Gates)

Traceability is explicit and validated.

1. **Cross-requirement links** live in `specs/requirements/trace-links.yaml` and MUST:
   - Reference only known IDs.
   - Use an allowed `type` (e.g., `realizes`, `satisfies`, `verifies`, etc.).

2. **Coverage gates (baseline)** MUST hold:
   - Every `CAP-*` MUST realize at least one `BV-*` via a `realizes` link.
   - Every `BR-*` MUST be satisfied by at least one `CAP-*` via a `satisfies` link.

3. **Hard rule for implemented capabilities**:
   - If `CAP.status == implemented`, it MUST include non-empty:
     - `trace.domain.commands[]` pointing to `specs/domain/<file>.md#CMD-####`
     - `trace.domain.events[]` pointing to `specs/domain/<file>.md#EVT-####`
   - The referenced anchors MUST exist in the target markdown.

## 6) When Code Exists: Alignment via Delta Approach (Explicit)

If project code exists, implementation MUST align with the delta approach.

This means:
- Any change to implemented behavior that affects BV/CAP/BR/NFR or traceability MUST be expressed in the governed specs and accompanied by deltas.
- Code changes MUST NOT contradict SSOT specs. If they do, the specs and deltas are updated first (or in the same PR) and code is updated to match.
- “Implemented” capability status MUST remain meaningful: it implies the domain traces exist and (once code gates activate) the implementation can be validated.

### 6.1 Objective definition: “codebase exists”

For the purpose of activating implementation-oriented gates (see ADR-0002), the codebase is considered present when any of the following is true:

- **Backend active** when:
  - a JVM app exists under `apps/` with a build descriptor (`build.gradle(.kts)` or `pom.xml`), AND
  - at least one file exists under `apps/**/src/main/java/`.

- **Web frontend active** when:
  - `frontends/web/package.json` exists, AND
  - at least one file exists under `frontends/web/src/`.

- **Mobile frontend active** when:
  - `frontends/mobile/pubspec.yaml` exists, AND
  - at least one file exists under `frontends/mobile/lib/`.

## 7) Tooling & Enforcement

- The current enforced gates for specs are implemented by `tools/spec-ci/validate.py`.
- CI MUST at least run this validation on any PR touching `specs/`.

## 8) PR Checklist (Quick)

For PRs that touch delta-governed artifacts (BV/CAP/BR/NFR/trace-links):
- Add a delta in `specs/deltas/` referencing every changed requirement ID.
- Keep `trace-links.yaml` consistent and meeting coverage gates.
- If any `CAP` is `implemented`, ensure domain trace links resolve to `CMD-####` / `EVT-####` anchors.

For PRs adding a Proposed ADR:
- Ensure the ADR clearly states which spec areas it changes.
- Apply the transformation into specs in the same PR (or a tightly coupled follow-up), using deltas when governed artifacts are affected.
