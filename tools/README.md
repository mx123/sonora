# Sonora Tooling — Pipeline Architecture

This document describes the two automated pipelines that drive the Sonora lifecycle:
**Requirements Ingestion** and **Task Generation**, their internal architecture,
and how they connect into a continuous spec-to-code workflow.

For CLI usage and configuration, see the [root README](../README.md#tooling).

---

## Overview

```
                  ┌──────────────────────────────────────────────────────────┐
                  │              Sonora Pipeline Architecture                │
                  └──────────────────────────────────────────────────────────┘

  ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
  │  Business Intent │         │   Specification  │         │  Implementation  │
  │  (natural lang)  │  ────►  │   Artifacts      │  ────►  │  Tasks           │
  │                  │         │   (SSOT YAML/MD) │         │  (for LLM agents)│
  └──────────────────┘         └──────────────────┘         └──────────────────┘
        reqingest.py               delta file                   taskgen.py
```

The two pipelines form a **relay**: the output of `reqingest.py` (a delta file)
is the input of `taskgen.py`. Together they close the loop from business intent
to implementation-ready task specifications.

---

## Stage 1: Requirements Ingestion Pipeline (`reqingest.py`)

### Problem

A user (product owner, architect) arrives with a business requirement in free form:

> *"Customers can reset their password via a time-limited email link.
> The link must expire after 30 minutes and be single-use."*

This needs to be decomposed into the SSOT structure — BV, CAP, BR, NFR, CMD, EVT,
trace-links — and a delta file must be created to record the change.

### Approach: LLM Agent with Validator-in-the-Loop

```
  ┌────────────┐
  │  Raw Input │  (natural language / YAML / file)
  └─────┬──────┘
        │
        ▼
  ┌────────────┐     ┌───────────────────────────────┐
  │  CLASSIFY  │ ◄── │  SSOT State Reader            │
  │            │     │  • existing IDs (BV-0001..003)│
  └─────┬──────┘     │  • domains (DOM-0001..002)    │
        │            │  • trace graph                │
        ▼            │  • JSON schemas               │
  ┌────────────┐     └───────────────────────────────┘
  │  DECOMPOSE │  LLM splits compound requirements
  │            │  into atomic spec artifacts
  └─────┬──────┘
        │
        ▼
  ┌────────────┐
  │   PLACE    │  Writes YAML files (BV/CAP/BR/NFR)
  │            │  Appends CMD/EVT markdown sections
  │            │  Updates trace-links.yaml
  └─────┬──────┘
        │
        ▼
  ┌────────────┐
  │   DELTA    │  Generates specs/deltas/YYYY-MM-DD-<slug>.yaml
  │            │  status: proposed
  └─────┬──────┘
        │
        ▼
  ┌────────────┐     ┌───────────────┐
  │  VALIDATE  │────►│  validate.py  │──── PASS ──►  Done
  │            │     └───────┬───────┘
  └────────────┘             │
        ▲                  FAIL
        │                    │
        └────── LLM repair ──┘  (up to 3 retries)
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Dynamic system prompt** | Built from constitutions + schemas + current SSOT state; LLM always sees the latest artifact IDs, domains, trace graph |
| **Sequential ID assignment** | SSOT reader scans existing files → next ID is `max + 1`; prevents collisions without a central counter |
| **Validator-in-the-loop** | On validation failure, errors are fed back to the LLM for self-repair; up to 3 retry cycles |
| **Dry-run / plan modes** | `--plan` shows LLM decomposition without writes; `--dry-run` shows file operations without writes |
| **Zero framework deps** | Uses only stdlib + PyYAML; HTTP calls via `urllib.request` |

### Output

```
specs/requirements/business-values/BV-0004.yaml
specs/requirements/capabilities/CAP-0004.yaml
specs/requirements/business-rules/BR-0006.yaml
specs/domain/commands.md        ← CMD-0007 section appended
specs/domain/events.md          ← EVT-0007 section appended
specs/requirements/trace-links.yaml   ← new links added
specs/deltas/2026-03-01-password-reset.yaml   ← delta (proposed)
```

---

## Stage 2: Task Generation Pipeline (`taskgen.py`)

### Problem

A delta file contains changes to specification artifacts (new BRs, amended CAPs,
new CMD/EVT). These need to be translated into **concrete implementation tasks**
for LLM coding agents, respecting the hexagonal architecture (ADR-0014),
middleware pipeline (ADR-0018), and quality gates (ADR-0013).

### Approach: Delta-Driven Task Decomposition

```
  ┌────────────────────────────┐
  │  Delta File                │
  │  (proposed or applied)     │
  │                            │
  │  changes:                  │
  │    - add BR-0003           │
  │    - add BR-0004           │
  │    - amend CAP-0002        │
  │    - status BV-0001 ✓      │  ← skipped (no code impact)
  └──────────┬─────────────────┘
             │
             ▼
  ┌────────────────────┐     ┌──────────────────────────────────┐
  │  1. IMPACT         │ ◄── │  Artifact Resolver               │
  │                    │     │  • loads CAP/BR/NFR YAML         │
  │  Resolve targets   │     │  • parses CMD/EVT markdown       │
  │  to full context   │     │  • follows trace-links → related │
  └──────────┬─────────┘     │    BRs                           │
             │               │  • identifies domain (DOM-*)     │
             ▼               │  • detects middleware (mw.*)     │
  ┌────────────────────┐     └──────────────────────────────────┘
  │  2. DECOMPOSE +    │
  │     SPECIFY        │     ┌──────────────────────────────────┐
  │                    │ ◄── │  Architecture Context            │
  │  LLM generates     │     │  • backend-shell-app.md          │
  │  task specs        │     │  • middleware registry           │
  │                    │     │  • domain definitions            │
  └──────────┬─────────┘     │  • quality gate IDs (repo.yaml)  │
             │               └──────────────────────────────────┘
             ▼
  ┌────────────────────┐
  │  3. ORDER          │
  │                    │
  │  Topological sort  │     Layer priority:
  │  by depends_on     │     domain-core → application →
  │                    │     adapter-in/out → middleware → test
  └──────────┬─────────┘
             │
             ▼
  ┌────────────────────┐
  │  Tasks             │     YAML (single doc) or
  │  (TASK-001..N)     │     individual .md files
  └────────────────────┘
```

### Task Structure

Each generated task includes:

```yaml
task_id: TASK-003
title: "Implement ActivateUser use case"
layer: application                      # one of 6 layers
domain: auth
description: |
  Create the ActivateUserUseCase implementing the ActivateUserPort.
  The use case loads the user by ID, verifies inactive state (BR-0003),
  transitions to active, persists, and emits UserActivated event.
acceptance_criteria:
  - "Given an inactive user, When ActivateUser is called, Then user.status becomes ACTIVE"
  - "Given an already-active user, When ActivateUser is called, Then AUTH.USER.CONFLICT is raised"
source_artifacts: [CAP-0002, BR-0003, CMD-0005]
target_files:
  - auth/app/usecase/ActivateUserUseCase.kt
  - auth/core/port/in/ActivateUserPort.kt
error_codes: [AUTH.USER.NOT_FOUND, AUTH.USER.CONFLICT]
contracts: ["mw.auth JWKS validation", "error-registry AUTH.USER.CONFLICT"]
depends_on: [TASK-001, TASK-002]        # domain-core tasks first
priority: high
quality_gates: [qg.tests.unit, qg.arch.boundaries]
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Status-only filtering** | Changes like "Status proposed → approved" have no code impact — automatically skipped |
| **Full context resolution** | Each CAP is resolved to its CMD/EVT specs (payload, invariants, error codes) and related BRs via trace-links |
| **Hexagonal layer assignment** | Tasks target exactly one layer; file paths follow hexagonal conventions (`<domain>/core/model/`, `<domain>/app/usecase/`, etc.) |
| **Topological ordering** | `domain-core` → `application` → `adapter` → `test`; agents can execute tasks sequentially without forward references |
| **Plan mode** | `--plan` runs impact analysis without LLM call — useful for reviewing what the pipeline "sees" before generating tasks |
| **Dual output format** | `--format yaml` for machine consumption; `--format files` for per-task markdown with checkboxes |

---

## Pipeline Relay: How the Two Stages Connect

```
  Product Owner                      Team Review                    LLM Agents
  ─────────────                      ───────────                    ──────────
       │                                  │                             │
       │  "Users can reset                │                             │
       │   passwords via email"           │                             │
       │                                  │                             │
       ▼                                  │                             │
  ┌──────────┐                            │                             │
  │reqingest │  generates:                │                             │
  │  .py     │  • BV-0004.yaml            │                             │
  │          │  • CAP-0004.yaml           │                             │
  │          │  • BR-0006.yaml            │                             │
  │          │  • CMD-0007 / EVT-0007     │                             │
  │          │  • trace-links             │                             │
  │          │  • delta (proposed) ──────►│  PR review                  │
  └──────────┘                            │  Is the decomposition       │
                                          │  correct?                   │
                                          │  Are traces complete?       │
                                          │                             │
                                          │  ✓ Merge → status: applied  │
                                          │                             │
                                          ▼                             │
                                    ┌──────────┐                        │
                                    │ taskgen  │  generates:            │
                                    │  .py     │  • TASK-001..N         │
                                    │          │  • acceptance criteria │
                                    │          │  • target files   ────►│  Implement
                                    │          │  • error codes         │  task by task
                                    │          │  • contracts           │
                                    │          │  • dependency order    │
                                    └──────────┘                        │
                                                                        │
                                                                        ▼
                                                                   ┌──────────┐
                                                                   │validate  │
                                                                   │  .py     │
                                                                   │  (CI)    │
                                                                   └──────────┘
```

### Data Flow Summary

| From | Artifact | To |
|------|----------|----|
| User | natural-language requirement | `reqingest.py` |
| `reqingest.py` | BV/CAP/BR/NFR YAML, CMD/EVT markdown, trace-links | SSOT folders |
| `reqingest.py` | `specs/deltas/YYYY-MM-DD-*.yaml` (proposed) | Team review |
| Team | delta status → `applied` | `taskgen.py` |
| `taskgen.py` | TASK-001..N (YAML or markdown) | LLM agents / developers |
| LLM agents | code changes | `validate.py` (CI) |
| `validate.py` | pass / fail | Build pipeline |

---

## Other Tools

| Tool | Purpose |
|------|---------|
| **bootstrap.py** | One-time project instantiation from the meta-template. Replaces placeholders, adopts/discards seed domain, scaffolds additional domains. |
| **spec-ci/validate.py** | SSOT validation: schema compliance, trace completeness, domain registry consistency, delta integrity. Runs in CI on every commit. |
| **spec-ci/generate_structurizr.py** | Generates C4 diagrams from `specs/architecture/structurizr/workspace.dsl`. |
| **upgrade.py** *(planned)* | Applies upstream meta-template updates to a bootstrapped project instance. |
