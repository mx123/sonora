# ADR-0012: Persistence and Cache Starters

- Status: Proposed
- Date: 2026-01-26

## Context

ADR-0008 defines the shell backend composition model and introduces optional starters for persistence and caching.

Some domains will be **stateful** and need persistence. Some domains will benefit from caching.

Constraints from the architecture baseline apply:

- Persistence is a domain boundary.
- Framework and technology integrations live in domain `infrastructure`.

This ADR defines how persistence and caching are provided as replaceable starters without violating domain boundaries.

## Decision

TBD (follow-up ADR).

### Core Principles (optional)

- Persistence is owned by the domain (schema/data boundaries).
- Cache is layered:
  - Domain-level caches are domain-scoped via the cache starter.
  - Cross-domain caches are allowed only in the shell app (explicit).
- Tech-agnostic abstractions with pluggable implementations per configuration.

## Consequences

### Positive

- 

### Negative

- 

## Alternatives Considered (optional)

1. **Shared database schema across domains**
   - Rejected: breaks domain boundaries and increases coupling.

2. **Shared cross-domain cache in shared modules**
   - Rejected: violates intentionality; should be a shell-level decision.

## Decision Drivers (optional)

- Stateful domains need a consistent integration model.
- Domain boundaries and extraction path must remain intact.
- Replaceability of infrastructure backends.
