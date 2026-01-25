# ADR-0004: Gradle Monorepo for Evolutionary Transition from Modular Monolith to Distributed System

- Status: Accepted
- Date: 2026-01-24

## Context

The project is developed as an **evolutionarily evolving service system** that:

- in early stages must work as a **modular monolith**;
- later allows **extraction of individual domains into independent services**;
- while maintaining the ability to run together (monolith / partially distributed system);
- uses the following technology stack:
  - Backend: Java, Spring Boot, stateless
  - BFF: Web BFF, Mobile BFF
  - Frontend: Web, Flutter
  - Build orchestration: Gradle (wrapper)

This ADR defines a **global monorepo principle**: the repository must remain **OS-agnostic**, and the primary way to run tooling must be via **Gradle tasks** (not OS-specific bash/bat scripts).

The key architectural requirement is to **establish domain and contract boundaries from day one** to minimize the cost of subsequent service extraction.

## Decision

We have decided to use a **Gradle-driven monorepo** built on the principles of:

- Modular Monolith
- Domain-Driven Design (bounded contexts)
- Clean Architecture
- Gradle Composite Build for future extraction

### Core Principle

> **Each domain module is a potential service.**

The monorepo is used as an **organizational and engineering measure**, not as an architectural constraint.

### Tooling & Portability (Global)

- The project must be **OS-agnostic** for local development and CI.
- Tooling must be **Gradle-first**: the primary entrypoint to run builds, checks, and developer workflows is via Gradle tasks.
- OS-oriented scripts (bash/bat) must not be a required interface for local developer workflows.
  - Using bash inside CI is acceptable; it must not become a prerequisite for local development.

### Gradle Wrapper (Global)

- A **Gradle Wrapper must be committed at repository root** and used for all Gradle execution:
  - `./gradlew` (Unix/macOS)
  - `gradlew.bat` (Windows)

### Build Orchestration (Aggregate Tasks)

- **Aggregate tasks** (group operations spanning multiple modules/areas, e.g., `build`, `test`, `check`) must be defined **centrally in one place**.
- Submodules may define only **local** tasks; they must not introduce alternative aggregate entrypoints.

### Repository Structure

```text
repo-root/
├── platform/                     # BOM / version catalog
├── shared/                       # Common, non-domain modules
├── domains/                      # Domain bounded contexts
├── bff/                          # BFF layer
├── apps/                         # Runtime composition (monolith / services)
├── frontends/                    # Web / Flutter
└── infra/                        # Docker, Kubernetes, local-dev
```

### Domain Module Structure

Each domain has a fixed structure:

```text
domains/<domain>/
├── api/
├── domain/
├── application/
└── infrastructure/
```

Layer purposes:

- **api** — public contracts (DTOs, events, ports)
- **domain** — pure domain model without framework dependencies
- **application** — use cases and orchestration
- **infrastructure** — Spring Boot, persistence, messaging

### Dependency Rules

- Domains **do not depend on each other directly**
- Domain interaction — only through `api`
- `domain` and `application` contain no Spring annotations
- Common code is placed only in `shared`
- Persistence is a domain boundary

### Application Build

- **Monolith** is built in `apps/monolith-app` and aggregates infrastructure modules of all domains
- **Microservice** is built in `apps/<domain>-service` and depends only on its own domain

### Domain Extraction

To extract a domain into a separate repository:

- move the `domains/<domain>` directory;
- connect via **Gradle Composite Build** (`includeBuild`);
- preserve existing dependency coordinates.

This allows extraction **without changes to consumers**.

## Alternatives

### Multi-repositories from the start
- ❌ High coordination cost
- ❌ Premature optimization

### Pure monolith without modular boundaries
- ❌ High cost of subsequent separation
- ❌ Uncontrolled coupling

### Spring Modulith
- ❌ Strong coupling with Spring
- ❌ Limited domain portability

## Consequences

### Positive

- Clear architectural domain boundaries
- Minimal service extraction cost
- Hybrid deployment capability
- Unified approach for monolith and microservices

### Negative

- Higher initial complexity
- Requires discipline in dependency management
- Architectural checks needed (ArchUnit)

## Related Requirements

- NFR-0004 (architecture conformance in CI)
- NFR-0016 (root wrapper + centralized aggregate tasks)
- NFR-0017 (OS-agnostic, Gradle-first tooling)

## Related Decisions

- Use of Version Catalog
- Introduction of ArchUnit rules
- BFF as composition layer, not business logic

