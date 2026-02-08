# ADR-0014: Adopt Hexagonal Architecture for Backend Domains

- Status: Proposed
- Date: 2026-01-27

## Context

The project is a multi-domain backend system.
The system is expected to evolve from a deployable monolith into a highly distributed architecture while preserving
the ability to run in a monolithic mode when appropriate.

Key constraints and drivers include:
- Long-lived and complex business domains with strict invariants
- Multiple delivery mechanisms (e.g., HTTP APIs, async messaging, scheduled jobs)
- Infrastructure volatility (databases, messaging systems, deployment topology)
- Need to prevent architectural erosion over time

An architectural approach is required that isolates business logic from infrastructure concerns and supports long-term evolution.

## Decision

Adopt **Hexagonal Architecture (Ports and Adapters)** as the primary architectural style for backend domain implementation.

Each backend domain will expose its capabilities through explicit ports and interact with infrastructure via adapters,
while the domain core remains independent of frameworks, persistence, and delivery mechanisms.

### Core Principles

- Domain logic is framework-agnostic and infrastructure-independent
- Business invariants are enforced exclusively inside the domain core
- Infrastructure concerns are isolated behind adapters
- Deployment topology (monolith vs distributed) must not affect domain design

## Consequences

### Positive

- Strong isolation of business logic from technical concerns
- Improved testability of domain logic without infrastructure dependencies
- Enables gradual evolution from monolith to distributed architecture
- Reduces coupling to specific frameworks, ORMs, and databases
- Supports multiple adapters without modifying domain code

### Negative

- Higher upfront design and modeling effort
- Increased number of abstractions (ports, adapters)
- Requires architectural discipline and enforcement (e.g., architecture tests / static analysis)
- Steeper learning curve for developers unfamiliar with hexagonal architecture

## Alternatives Considered

1. **Traditional Layered Architecture**
   - Rejected due to high risk of business logic leaking into infrastructure layers
   - Poor resistance to long-term architectural erosion

2. **Framework-Centric (Framework-driven) Architecture**
   - Rejected due to tight coupling between domain logic and framework APIs
   - Limits future adaptability and testability

## Decision Drivers

- Long-term maintainability of complex domains
- Ability to evolve deployment topology safely
- Protection of business invariants
- Framework and infrastructure independence
