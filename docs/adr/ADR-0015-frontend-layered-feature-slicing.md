# ADR-0002: Use Layered Architecture with Feature / Domain Slicing for Frontend

- Status: Proposed
- Date: 2026-01-27

## Context

The frontend is implemented using Vite, React, and TypeScript and serves as the primary user interface for backend domains.
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

## Consequences

### Positive

- Reduced architectural overhead and cognitive load
- Faster onboarding and feature development
- Better alignment with React and modern frontend best practices
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
- Alignment with ecosystem conventions (React, TypeScript)
- Avoidance of unnecessary architectural complexity
