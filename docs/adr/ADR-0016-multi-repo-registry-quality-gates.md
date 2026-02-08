# ADR-0016: Multi-repo Baseline with Central Registry and Tool-neutral Quality Gates

- Status: Accepted
- Date: 2026-02-08

## Context

This decision is made in a **spec-first** phase where implementation details are intentionally deferred. Therefore the **architecture and governance contracts** defined here MUST be **language- and toolchain-agnostic**, and phrased in stable, verifiable terms.

Earlier decisions established a monorepo and build-tool-first tooling. During planning we identified new constraints:

- Avoid binding the architecture baseline to a single repository topology (monorepo) and a single build tool.
- Keep architectural patterns (Shell, domain boundaries, federation) first-class, and treat framework/tool choices as reference implementations.
- Introduce a central way (in SSOT documentation) to discover related repositories and define integration expectations for CI and local development.

## Decision

We adopt a **multi-repository workspace baseline** with the following governance contracts:

1. **Central workspace registry in specs**
   - A workspace registry under `specs/` lists related repositories (URL + revision) and defines minimum expectations.

2. **Per-repository index (`repo.yaml`) is non-SSOT and minimal**
   - Each repository MUST contain a root `repo.yaml` that declares only:
     - navigation entrypoints (`entry.*` IDs + paths)
     - participation in stable quality gate IDs (`qg.*`)
   - `repo.yaml` MUST NOT contain executable commands or duplicate requirements content.

3. **Quality gates are stable, tool-neutral IDs**
   - The meaning of each `qg.*` gate is defined in specs (rules).
   - Implementations may differ per language/toolchain, but semantics remain stable.

4. **Shell-app and frontend shells are patterns-first**
   - Shell patterns and boundaries are defined as contracts.
   - Technology-specific stacks are treated as reference implementations.

### Relationship to existing ADRs

- Upon acceptance, this ADR supersedes the topology/tooling constraints in ADR-0004 that require a single tool-driven monorepo.
- This ADR is compatible with the intent of verifiable architecture and non-bypassable gates, but shifts the contract from “build-tool façade tasks” to “gate IDs with per-repo adapters”.

## Consequences

### Positive

- Planning and governance become language-agnostic.
- Multi-repo becomes a first-class, auditable topology.
- Quality gates remain enforceable without build-tool lock-in.
- Shell and federation contracts stay stable while implementations can vary.

### Negative

- Requires maintaining a workspace registry and per-repo indices.
- Introduces an additional mapping layer (gate IDs to concrete tools) per repository.
- Some existing documentation that assumes build-tool-specific façade tasks will need to be updated or superseded.

## Alternatives Considered

1. **Keep tool-driven monorepo as the only supported topology**
   - Rejected: locks the baseline to one ecosystem and inhibits language-agnostic planning.

2. **Use only repo URLs, no `repo.yaml`**
   - Rejected: makes discovery and automation ambiguous; forces repeated manual documentation and drifts quickly.

## Decision Drivers

- Language-agnostic planning before code exists.
- Decoupling architecture from tooling and repository topology.
- Enforceable, non-bypassable quality governance.
- Lower coordination friction when splitting into multiple repositories.
