# Docs Constitution (Documentation Governance)

Last updated: 2026-01-25

This document defines the governance rules for **documentation artifacts under `docs/`**.

Normative language: **MUST**, **MUST NOT**, **SHOULD**, **MAY** are used as in RFC 2119.

## 1) Purpose

The goals of this constitution are to keep documentation changes:
- **Reviewable** (clear diffs)
- **Auditable** (history explains why)
- **Consistent** (shared conventions across the repo)
- **Decoupled** (docs governance does not depend on specs governance)

## 2) Authority Model (Docs vs Specs)

This repository has two independent constitutions:

1. **Docs SSOT**: `docs/constitution.md` is the single source of truth for how documentation is authored and governed.
2. **Specs SSOT**: `specs/constitution.md` is the single source of truth for how specification artifacts are authored and governed.

Rules:
- These constitutions **MUST remain consistent** in shared terminology and cross-references.
- They are **independent**: documentation rules in `docs/` are not derived from `specs/`, and spec rules in `specs/` are not derived from `docs/`.
- If a conflict is discovered between constitutions, it **MUST** be treated as a governance defect and resolved explicitly (e.g., via ADR + aligned edits).

## 3) Documentation Structure

### 3.1 `docs/adr/` — Architecture Decision Records

- This folder contains ADRs that document architectural decisions and their rationale.
- ADRs are the primary mechanism to record “why” and “how” we changed direction.

### 3.2 `docs/derived/` — Generated Documentation Outputs

- This folder contains **generated outputs only** (typically generated from `specs/`).
- Files under `docs/derived/` **MUST NOT** be edited manually.
- If CI regenerates derived artifacts, it **MUST** be deterministic; non-reproducible diffs are treated as failures.

## 4) ADR Policy

### 4.1 ADR File Naming and Numbering

- ADR filenames **MUST** follow: `ADR-####-short-title.md`.
- The numeric sequence **MUST** be monotonically increasing.
- The short title **SHOULD** be kebab-case, concise, and stable.
- Existing ADRs that do not follow kebab-case are tolerated; new ADRs **SHOULD** follow the convention.

### 4.2 ADR Header Format

Each ADR **MUST** start with:

- `# ADR-####: <Title>`
- `- Status: <Proposed|Accepted|Rejected|Superseded>`
- `- Date: YYYY-MM-DD`

### 4.3 Required ADR Sections

Each ADR **MUST** include at least:

- `## Context`
- `## Decision`
- `## Consequences` (positive and negative)

Each ADR **SHOULD** include:

- `## Alternatives Considered`
- `## Decision Drivers`

### 4.4 ADR Status Lifecycle

- New ADRs **SHOULD** start as `Status: Proposed`.
- An ADR becomes `Accepted` when the team agrees to it.
- An ADR becomes `Rejected` when the proposal is explicitly declined.
- An ADR becomes `Superseded` only when a new ADR replaces it.

### 4.5 Updating ADRs (Immutability Policy)

- Accepted ADRs **MUST NOT** be rewritten to change meaning.
- If a decision changes, create a new ADR and mark the old one as `Superseded`.
- Editing an accepted ADR is allowed only for:
  - typos/formatting
  - clarifications that do not change meaning
  - adding forward references (e.g., “Superseded by ADR-00XX”)

### 4.6 ADR Scope and Boundaries

- ADRs **MUST** focus on architectural decisions, constraints, and rationale.
- ADRs **MUST NOT** act as the requirements model.
- ADRs **MAY** link to related specs, deltas, diagrams, and implementation artifacts.

### 4.7 ADR Template and Number Allocation

- To create a new ADR, pick the next number as: `max(existing ADR numbers) + 1`.
- ADR numbers **MUST NOT** be reused.
- Use the ADR template at `docs/adr/TEMPLATE.md` for new ADRs.
- New ADRs **SHOULD** start from the template and only adjust what is necessary.

## 5) Docs-to-Specs Hand-off (Informative)

ADRs often drive changes in the `specs/` area (requirements, traceability, architecture specs). The transformation policy and enforcement rules are defined by the specs constitution:

- See `specs/constitution.md` for how ADRs are translated into spec changes (including deltas and traceability gates).

This section is **informative**: it points to the specs governance, but does not redefine it.

## 6) Writing Rules

- Documentation in `docs/` **MUST** be written in **English**.
- Prefer precise, operational language.
- Use consistent terms across ADRs (e.g., “Shell”, “Domain UI”, “Derived artifacts”).
- Use links over duplication: if something is governed elsewhere, reference it rather than copying.

## 7) Change Expectations

- Any PR adding/changing ADRs **MUST** be reviewable as a clean markdown diff.
- If a doc change introduces new terminology, the change **SHOULD** include a minimal definition in the relevant ADR or in this constitution.
- If an ADR implies downstream changes (e.g., new architecture constraints), the PR **SHOULD** include explicit follow-ups (issues/PR links) or a short “Next steps” note.
