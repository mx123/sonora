# Middleware: Cache

## Metadata

- **Middleware ID:** `mw.cache`
- **Category:** optional
- **Pipeline Position:** 600
- **Implementation Ref:** `repo.backend :: entry.middleware.cache`

## Contract

### Purpose

Provides a two-level caching model (domain-scoped and shell-level) with tenant-aware isolation and observability integration. Runs last in the pipeline so that auth context, trace context, and all other concerns are fully resolved before cache key generation and lookup.

### Preconditions

- Auth context has been established by `mw.auth` (position 100) — required for tenant-aware cache isolation.
- Trace context has been established by `mw.trace` (position 200) — required for cache hit/miss observability.
- Error middleware (`mw.error`, position 300) is in place.
- The cache starter is included via build-time dependency; when not included, this middleware does not participate in the pipeline.

### Processing

- For HTTP GET requests (opt-in per endpoint):
  - Generates a **cache key** from request attributes (path, query parameters, tenant context).
  - Performs cache lookup. On **hit**: returns cached response, records cache-hit metric via trace context.
  - On **miss**: delegates to downstream handler, caches the result, records cache-miss metric.
- For all other request/message types:
  - Passes through to downstream handler without caching.
  - Domain code MAY interact with the cache port directly for explicit cache operations.
- Cache key generation MUST include `tenantId` from auth context to enforce **tenant-isolated caching** (no cross-tenant cache leakage).

### Postconditions

- Cached HTTP GET responses are served without reaching domain handlers (on cache hit).
- Cache hit/miss metrics are recorded in the trace context for observability.
- Tenant isolation is enforced: cache entries from one tenant are never served to another.
- No domain state is mutated by the cache middleware itself.

### Domain port

Domain code MAY depend on a narrow cache port (e.g., `CachePort`) for explicit cache operations:

- `get(key)`: retrieve a cached value.
- `put(key, value, ttl?)`: store a value with optional TTL override.
- `evict(key)`: remove a specific cache entry.
- `evictAll(namespace?)`: remove all entries in a namespace (domain-scoped).

This port is a no-op when the cache starter is not included.

#### Two-level model

| Level | Scope | Cache namespace | Access |
|-------|-------|----------------|--------|
| **Domain cache** | Single domain | `<domain-id>.*` | Domain code via `CachePort` |
| **Shell cache** | Cross-domain | `shell.*` | Shell app configuration only |

- Domain caches are **namespace-isolated**: a domain's cache operations are scoped to its own namespace and cannot access other domains' entries.
- Shell-level caches are configured at the shell app level and are explicitly cross-domain (e.g., shared reference data lookups).

### Provider SPI

Cache storage is pluggable via the CacheProvider SPI:

- **Default implementation:** in-memory cache (e.g., Caffeine — bounded size, TTL-based eviction).
- **Alternative implementations:** distributed cache (Redis, Hazelcast) — selected per deployment configuration.
- The provider is selected at deployment time, not per domain (unless explicitly configured for multi-provider scenarios).

### Cache invalidation

- Domain caches: the domain is responsible for invalidating its own cache entries when state changes (typically in response to domain events or command handling).
- Shell caches: invalidation is triggered by configuration-based TTL or explicit shell-level eviction logic.
- The cache starter does NOT provide automatic event-driven cache invalidation — this is a domain responsibility.

## Quality Gates

- `qg.tests.contract` — cache middleware contract tests (tenant isolation, cache hit/miss behavior, key generation, eviction)
- `qg.arch.boundaries` — cache middleware resides in infrastructure/adapter layer, not in domain core

## Related

- ADR-0012: Persistence and Cache Starters
- ADR-0008: Shell Backend Middleware Composition (§ Optional Starters — Cache)
- ADR-0018: Middleware Design Principles and Registry
- Backend shell app spec: `specs/architecture/backend-shell-app.md`
