# ADR-0015: Use Layered Architecture with Feature / Domain Slicing for Frontend

- Status: Accepted
- Date: 2026-02-11

## Context

The frontend serves as the primary user interface for backend domains.
Unlike the backend, the frontend does not own business invariants and is not a system of record.

Key characteristics:
- Rapidly evolving UI and UX requirements
- Strong dependency on backend APIs and contracts
- Shorter lifecycle of abstractions compared to backend domain models
- Primary responsibilities include orchestration, presentation, and client-side state management

Applying the same architectural rigor as the backend (e.g., Hexagonal Architecture) risks introducing unnecessary complexity
without proportional benefits.

## Decision

Adopt a **Layered Architecture combined with Feature / Domain Slicing** for frontend development.

Frontend code will be organized primarily by feature (aligned with backend domains where applicable),
with clear internal layering for UI, state, and API interaction.

### Core Principles

- Organize code by feature, not by technical layer alone
- Keep abstractions lightweight and purpose-driven
- Avoid duplicating backend domain models and invariants
- Optimize for readability, change locality, and team scalability

### Internal Layer Model

Each feature slice MUST be organized into the following internal layers, ordered from outermost (closest to user) to innermost (closest to backend):

| Layer | Responsibility | Allowed Dependencies |
|-------|---------------|----------------------|
| **UI** | Components, pages, layout, styling, user interaction handling | State, API |
| **State** | Client-side state management, derived/computed state, UI-relevant caching | API |
| **API** | Backend communication, request/response mapping, contract types | *(none within feature)* |

Dependency rules:

- **UI → State → API** (strict top-down; no reverse dependencies)
- **API layer MUST NOT depend on UI or State layers**
- **State layer MUST NOT depend on UI layer**
- **Cross-feature imports MUST go through a public API (barrel export) at the feature root**, not reach into another feature's internals
- **Shared utilities** (e.g., design system components, formatting helpers) live in a `shared/` area outside feature slices and MUST NOT contain feature-specific business logic

### Feature Slice Structure (Normative)

A feature slice directory SHOULD follow this layout:

```
features/<feature-name>/
  index.ts          # Public API (barrel export)
  ui/               # Components, pages
  state/            # State management (store, selectors, hooks)
  api/              # API client, request/response types
  types.ts          # Feature-scoped type definitions (optional)
```

Rules:

- Feature names SHOULD align with backend domain names where applicable (e.g., `features/inventory/`, `features/cart/`).
- A feature MUST NOT import from another feature's internal directories; only via the target feature's `index.ts`.
- The Shell app owns cross-cutting concerns (routing, auth context, theming) and composes features — it is NOT a feature itself.

## Consequences

### Positive

- Reduced architectural overhead and cognitive load
- Faster onboarding and feature development
- Better alignment with modern component-based frontend best practices
- Clear ownership and isolation of feature-related changes
- Avoids premature or artificial abstractions

### Negative

- Weaker enforcement of architectural boundaries compared to hexagonal backend
- Potential for logic duplication across features if not governed
- Requires discipline to avoid cross-feature coupling

## Alternatives Considered

1. **Hexagonal Architecture on the Frontend**
   - Rejected due to lack of a stable, long-lived domain core
   - Introduces abstraction layers without clear business value

2. **Pure Flat Structure**
   - Rejected due to poor scalability and maintainability as the application grows
   - Increases risk of tight coupling and unclear ownership

## Decision Drivers

- Different nature and lifecycle of frontend code compared to backend
- Need for development speed and flexibility
- Alignment with common frontend ecosystem conventions
- Avoidance of unnecessary architectural complexity

### Spec impact (transformation targets)

- `specs/architecture/frontend-shells.md` — add reference to internal layer model
- `specs/architecture/federated-ui-composition.md` — add reference to feature slice convention
- `specs/rules/quality-gates.md` — frontend `qg.arch.boundaries` enforcement covers layer dependency rules
