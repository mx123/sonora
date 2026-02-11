# ADR-0012: Persistence and Cache Starters

- Status: Accepted
- Date: 2026-02-11

## Context

ADR-0008 defines the shell backend composition model and introduces optional starters for persistence and caching.

Some domains will be **stateful** and need persistence. Some domains will benefit from caching.

Constraints from the architecture baseline apply:

- Persistence is a domain boundary.
- Framework and technology integrations live in domain `infrastructure`.

This ADR defines how persistence and caching are provided as replaceable starters without violating domain boundaries.

## Decision

We adopt **two optional starters** — persistence and cache — each following the narrow-port, SPI-based packaging model established in ADR-0009 and ADR-0010.

### 1) Persistence Starter

The persistence starter provides a **port-driven persistence integration** for stateful domains, keeping the domain core free of infrastructure coupling.

#### Architecture alignment (ADR-0014 Hexagonal)

Per ADR-0014, persistence integration follows the hexagonal pattern:

- Domain core defines **output ports** (repository interfaces) specifying the persistence contract.
- The persistence starter provides **adapter implementations** of those ports using a concrete persistence technology.
- Domain core MUST NOT reference any persistence framework, ORM, or database driver directly.

#### Starter abstraction

The persistence starter does **not** introduce a generic repository base class or universal CRUD abstraction. Instead, it provides:

- **Transaction management port**: a narrow interface for declarative transaction boundaries, usable by application-layer use cases without coupling to a specific transaction manager.
- **Connection/session lifecycle management**: automatic lifecycle management integrated with the middleware pipeline (request-scoped for HTTP, message-scoped for messaging).
- **Schema migration integration**: supports schema migration tooling (e.g., Flyway, Liquibase) as a pluggable SPI. Migrations are **domain-scoped**: each domain owns its schema and migration scripts.

#### Provider SPI

- **PersistenceProvider SPI**: implementations supply connection pool, transaction manager, and ORM/query-builder integration.
- Default implementation: to be selected per deployment (e.g., JPA/Hibernate, jOOQ, JDBC template). The SPI contract is defined; the technology choice is a deployment decision.
- All providers MUST satisfy:
  - Request/message-scoped session lifecycle.
  - Declarative transaction support.
  - Schema isolation per domain (separate schema/namespace or explicit table prefix).

#### Domain boundary enforcement

- Each domain's persistence schema is **isolated**: domains MUST NOT share tables, schemas, or data access paths.
- Cross-domain data access happens only via published APIs or messaging (never via shared database queries).
- The persistence starter MUST support **multiple data sources** when domains with different storage requirements are composed into the same shell app.
- Schema migration scripts live within each domain's source tree, not in a shared location.

### 2) Cache Starter

The cache starter provides a **two-level caching model** with domain-scoped and shell-level caches.

#### Two-level model (per ADR-0008)

| Level | Scope | Owner | Use case |
|-------|-------|-------|----------|
| **Domain cache** | Single domain boundary | Domain | Domain-specific read optimization, computed value caching |
| **Shell cache** | Cross-domain, shell-level | Shell app | Shared reference data, cross-cutting lookup caches |

Rules:

- Domain-level caches are provided via the cache starter and remain **domain-scoped**. A domain's cache MUST NOT be accessible to other domains.
- Cross-domain caches are allowed **only at the shell application level** and MUST be explicit and intentional (never implicit leakage).
- Cache invalidation for domain caches aligns with domain events: when state changes, the domain is responsible for invalidating its own cache entries.

#### Starter abstraction

- **CachePort**: a narrow cache interface (get, put, evict, evictAll) that domain code depends on. No framework-specific cache annotations or APIs in domain/application layers.
- **CacheConfiguration**: per-domain cache configuration (TTL, max size, eviction policy) defined in version-controlled configuration files.

#### Provider SPI

- **CacheProvider SPI**: implementations supply the underlying cache engine.
- Default implementation: in-memory cache (e.g., Caffeine, Guava).
- Alternative implementations: distributed cache (Redis, Hazelcast) swappable via configuration.
- The provider is selected per deployment, not per domain (unless explicitly configured).

#### Middleware integration

The cache middleware (pipeline position 600, optional) provides:

- Automatic cache key generation from request/message attributes.
- Cache-aside pattern support for HTTP GET responses (opt-in per endpoint).
- Integration with auth context for tenant-aware cache isolation.
- Integration with trace context for cache hit/miss observability.

### 3) Starter packaging model

Both starters follow the packaging contract from ADR-0009 §3:

- Single build-time dependency with auto-activation.
- Public contract via narrow ports.
- Default implementation auto-configured.
- Implementation in infrastructure/adapter layer (ADR-0014).
- SPIs for technology pluggability.

Both starters are **optional** (per ADR-0008): domains that don't need persistence or caching don't carry the dependency.

### Spec impact (transformation targets)

- `specs/architecture/middleware/cache.md` — **new**: cache middleware contract (this ADR creates it)
- `specs/architecture/middleware/README.md` — update cache entry from *(follow-up)* to `cache.md`

## Consequences

### Positive

- Port-driven persistence keeps domain core completely infrastructure-free.
- Schema isolation per domain preserves the domain extraction path.
- Two-level cache model prevents accidental cross-domain cache leakage.
- SPI-based pluggability allows technology selection at deployment time.
- Transaction management port simplifies application-layer use case implementation.

### Negative

- Multiple data source support adds configuration complexity.
- Schema isolation means no cross-domain joins — requires messaging or API-based data aggregation.
- Cache invalidation responsibility falls on domain code — no automatic cache/event synchronization is provided.
- Two SPIs (persistence provider, cache provider) per starter increase maintenance surface.

## Alternatives Considered

1. **Shared database schema across domains**
   - Rejected: breaks domain boundaries and increases coupling; prevents independent domain extraction.

2. **Shared cross-domain cache in shared modules**
   - Rejected: violates intentionality; should be a shell-level decision.

3. **Generic repository base class (Spring Data-style)**
   - Rejected: leaks framework abstractions into domain ports; prefer explicit domain-defined repository interfaces.

4. **No cache starter, use framework-native caching**
   - Rejected: inconsistent caching behavior across compositions; no tenant-aware isolation.

## Decision Drivers

- Stateful domains need a consistent integration model.
- Domain boundaries and extraction path must remain intact.
- Replaceability of infrastructure backends.
- Cache isolation aligns with tenant isolation requirements (ADR-0005).
