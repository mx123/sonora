# ADR-0003: LLM Agent Transformation Workflow (Specs → Change Tasks)

- Status: Accepted
- Date: 2026-01-24

## Context
We want to use an LLM stream to accelerate Spec-Driven Development while keeping changes deterministic, reviewable, and governed.

The system must evolve through deltas and maintain traceability from business intent (BV/CAP/BR/NFR) to domain behavior (commands/events) and derived artifacts.

## Decision
The LLM agent operates as a **spec compiler and change planner**, not an autonomous designer.

### Inputs (authoritative)
- `specs/requirements/**` (BV/CAP/BR/NFR + trace graph)
- `specs/domain/**` (commands/events and related domain vocabulary)
- `specs/deltas/**` (explicit change sets)

### Outputs (reviewable)
1. **Spec changes** (when requested):
   - new/updated per-item requirement specs
   - updated `trace-links.yaml`
   - new delta file describing the change

2. **Derived artifacts** (generated, non-authoritative):
   - OpenAPI/AsyncAPI/Structurizr/trace reports under `docs/derived/`

3. **Implementation work plan** (tasks) that maps specs to code changes:
   - backend tasks (ports/adapters boundaries, application services)
   - frontend tasks (BFF projections, UI flows)
   - testing tasks (acceptance/e2e/arch tests, when activated)

### Guardrails
- The agent must not invent business intent; it can only propose transformations that are traceable to explicit requirement specs and deltas.
- The agent must not directly change production code unless explicitly requested by a human.
- All outputs must be diffable and suitable for PR review.
- Any generated artifact under `docs/derived/` is never treated as source of truth.

### Determinism requirements
- Given the same inputs, the generation pipeline should be reproducible.
- Non-deterministic outputs must be treated as failures once generators are introduced and enforced.

## Consequences
Positive:
- Faster iteration with preserved governance and traceability.
- Clear boundaries on what an agent can change.

Negative:
- Requires discipline: specs first, code second.

## Notes
This ADR describes the workflow; implementation may start with minimal validation and evolve toward full generators + CI enforcement.
