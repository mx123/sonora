# ADR-0006: Federated UI Composition for Multi-Domain Systems

- Status: Accepted
- Date: 2026-01-25

## Context

The system is a multi-domain service architecture where each domain owns:
- A Web UI implemented as SPA (React + Vite + TypeScript)
- A Mobile UI implemented in Flutter

The system must:
- Present a unified user experience across domains
- Preserve strict domain ownership and modular development
- Avoid tight coupling and excessive UI integration complexity
- Support evolution from a modular monolith to distributed services

The primary architectural challenge is how to integrate domain-specific UI parts into a cohesive application without violating domain boundaries or creating a fragile UI architecture.

## Decision

We adopt a **Shell-based Federated UI Composition** model for both Web and Mobile platforms.

### Core Principles

1. Each domain fully owns its UI and internal navigation.
2. UI integration occurs only at the composition level, not via shared business components.
3. Domains expose UI entry points through explicit contracts.
4. Cross-domain communication is limited to events and navigation APIs.
5. Shared UI libraries are restricted to stateless visual primitives.

### Web (React SPA)

- A central **Application Shell** is responsible for:
  - Layout
  - Global routing
  - Authentication
  - Navigation
  - Theming

- Each domain exposes a single runtime entry point:
  ```ts
  mount(context: DomainUIContext): DomainUIHandle
  ```

- Domains are loaded dynamically and mounted by the Shell.
- Direct imports between domain UI modules are forbidden.

### Mobile (Flutter)

- A central **Flutter App Shell** composes domain UI packages at compile time.
- Each domain UI is implemented as an independent Flutter package.
- Domains expose a screen/router entry implementing a common interface.
- Navigation and cross-domain communication are mediated via facades.

### Communication Model

Allowed integration mechanisms:
- Domain events via an EventBus
- Navigation via a Navigation/Router Facade
- Explicit read-only APIs

Disallowed mechanisms:
- Shared global state across domains
- Direct widget/component reuse between domains
- Cross-domain business UI components

## Consequences

### Positive

- Strong domain isolation
- Independent development and release cycles
- Clear ownership boundaries
- Scalable UI architecture aligned with domain-driven design
- Smooth transition path from monolith to distributed systems

### Negative

- Initial overhead in defining UI contracts and facades
- Limited direct UI reuse across domains
- Requires architectural discipline and enforcement

## Alternatives Considered

1. **Global UI State (Redux/Bloc across domains)**
   - Rejected due to tight coupling and hidden dependencies

2. **Direct Component Sharing Between Domains**
   - Rejected due to violation of domain ownership

3. **Backend-Driven UI Orchestration**
   - Rejected due to loss of frontend autonomy and increased latency

4. **Full Micro-Frontend Frameworks (e.g., single-spa everywhere)**
   - Rejected as overly complex for the required level of federation

## Decision Drivers

- Maintain modularity and domain autonomy
- Minimize UI integration complexity
- Support both Web and Mobile consistently
- Enable long-term architectural evolution

## Notes

This ADR applies equally to:
- Modular monolith deployments
- Partially or fully distributed domain services

The Shell remains the only integration point for UI composition.
