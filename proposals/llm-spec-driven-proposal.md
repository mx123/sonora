# Proposal: Dedicated LLM Stream for Spec-Driven Development Repository Structure

> NOTE: This proposal is being converted into an ADR.
> See docs/adr/ADR-0001-llm-stream-sdd.md for the current decision record.

## 1. Purpose

This document proposes the implementation of a **dedicated LLM-driven workflow (LLM stream)** to support a **Spec-Driven Development (SDD)** approach for the reference project described below.

The goal is to ensure:
- specifications are the **single source of truth**;
- architectural evolution is **controlled, delta-based, and auditable**;
- monolithic and distributed deployment modes are supported **without branching the domain logic**;
- LLM usage is **deterministic, constrained, and enforceable**.

This proposal is intended to be used as a reference implementation and internal standard.

---

## 2. Reference Project Description

### 2.1 Project Nature

The reference project is an **evolving enterprise system** with the following characteristics:

- Starts as a **logical monolith** and incrementally evolves into a **highly distributed system**
- Even in its final distributed form, it **must remain runnable as a functional monolith**, with reduced scalability but full business functionality
- Evolution occurs through **explicit, incremental deltas**, affecting:
  - the whole system
  - or isolated bounded contexts / aspects

### 2.2 Technology Stack

#### Frontend
- Web: TypeScript + Vite + React
- Mobile: Flutter

#### Backend
- Java 21+
- Spring Boot
- Architecture aligned with Ports & Adapters (Hexagonal)

#### Infrastructure
- Messaging, databases, and storage are **deployment-dependent**
- Infrastructure technologies are **not part of the core project**
- Only **adapters and contracts** for infrastructure integration are included

#### Architectural Principles
- Backend-for-Frontend (BFF) pattern
- Strong separation of:
  - domain
  - application logic
  - adapters
  - deployment concerns

---

## 3. Core Architectural Requirement

### 3.1 Spec as Source of Truth

All architectural, domain, and contract decisions must be expressed as **machine-readable specifications**, not code.

Code is considered a **derived artifact**.

### 3.2 Domain-First Modeling

- Domain behavior is modeled using a **formalized EventStorming DSL**
- Commands, Events, Aggregates, Invariants, and Policies are explicit
- APIs, messaging, and adapters are projections of the domain, not drivers of it

### 3.3 Delta-Based Evolution

- No destructive changes to existing specifications
- All evolution is expressed via **delta specifications**
- Each delta must be:
  - analyzable
  - reviewable
  - backward-compatibility checked

### 3.4 Requirements Model (BV/CAP/BR/NFR) and Traceability

Business requirements are modeled as machine-readable specs using per-item files:

- **BV-#### (Business Value)**: why we do it; owner and measurable success metrics
- **CAP-#### (Capability)**: what the system must enable from a business perspective
- **BR-#### (Business Requirement)**: specific rule/obligation that refines a capability
- **NFR-#### (Non-Functional Requirement)**: quality attribute/constraint (stored separately)

Traceability rules:

- Cross-layer requirement links live in a single graph file: `specs/requirements/trace-links.yaml`.
- Domain trace for a capability lives in the capability file itself (`trace.domain.commands[]`, `trace.domain.events[]`) as **repo-relative links** to `specs/domain/*#CMD-####` and `specs/domain/*#EVT-####`.
- **Hard gate:** if `CAP.status == implemented`, commands and events trace lists must be present and non-empty, and anchors must resolve.

---

## 4. Proposed Repository Structure (Reference)

```text
repo-root/
├─ specs/                     # Single Source of Truth
│  ├─ architecture/
│  ├─ domain/
│  ├─ api/
│  ├─ messaging/
│  ├─ adapters/
│  ├─ deltas/
│  ├─ requirements/
│  │  ├─ business-values/
│  │  ├─ capabilities/
│  │  ├─ business-rules/
│  │  ├─ nfr/
│  │  └─ trace-links.yaml
│  ├─ schemas/
│  └─ rules/
│
├─ tools/                     # LLM + validation + generators
├─ apps/                      # Runtime composition (monolith / services)
├─ frontends/
│  ├─ web/
│  └─ mobile/
├─ infra/                     # Docker, Kubernetes, local-dev
└─ docs/
  └─ derived/                # GENERATED ONLY (OpenAPI/AsyncAPI/Structurizr/trace reports)
```

The `specs/` directory is **authoritative**.  
Any change in behavior must originate there.

---

## 5. Dedicated LLM Stream: Scope and Responsibilities

### 5.1 What the LLM Stream IS

The LLM stream acts as a **spec compiler and verifier**, not as an autonomous designer.

Primary responsibilities:

1. Specification validation
2. Delta impact analysis
3. Consistency checking across layers
4. Controlled generation of derived artifacts

### 5.2 What the LLM Stream IS NOT

The LLM stream:
- does not invent domain behavior
- does not bypass specifications
- does not directly modify production code
- does not replace architectural decision-making

---

## 6. LLM Stream Functional Capabilities

### 6.1 Specification Validation

- Validate domain DSL consistency
- Enforce invariants and rules
- Detect illegal cross-context dependencies

### 6.2 Delta Analysis

For each delta:
- identify affected bounded contexts
- determine API and messaging impact
- verify backward compatibility rules
- produce a human-readable impact report

### 6.3 Projection Generation (Controlled)

From validated specs:
- OpenAPI (core + BFFs)
- AsyncAPI
- Adapter contracts
- Typed client SDKs (TypeScript, Dart)

Generated artifacts are written under `docs/derived/` and are never treated as authoritative sources.
Generation is deterministic and reproducible.

---

## 7. Enforcement Model

### 7.1 CI/CD Integration

The LLM stream is invoked:
- on pull requests touching `specs/`
- before code generation
- before merge to main

Failure conditions:
- invalid delta
- broken invariant
- unauthorized architectural change

### 7.2 Human-in-the-Loop

LLM output is:
- reviewable
- diffable
- never auto-merged

---

## 8. Expected Benefits

- Long-term architectural stability
- Safe evolution from monolith to distributed system
- Reduced accidental complexity
- Explicit and reviewable system knowledge
- Technology-agnostic core

---

## 9. Success Criteria

The implementation is considered successful if:

- The same domain specs can drive:
  - monolithic deployment
  - distributed deployment
- Adding a new capability requires:
  - a delta spec
  - zero undocumented architectural decisions
- LLM output is predictable and explainable

---

## 10. Conclusion

This proposal establishes a **disciplined, spec-first development model** supported by a dedicated LLM stream.

It treats LLMs as:
> *strict processors of intent, not authors of architecture.*

This makes the approach suitable for **long-lived, evolving enterprise systems** with high architectural integrity requirements.
