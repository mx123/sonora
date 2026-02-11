# ADR-0018: Middleware Design Principles and Registry

- Status: Accepted
- Date: 2026-02-11

## Context

ADR-0008 established the Shell Backend composition model and identified four mandatory middleware starters (Auth, Errors, Trace, Messaging) plus optional starters (Audit, Persistence, Cache). The normative spec `specs/architecture/backend-shell-app.md` §5 defines mandatory middleware contracts at a high level — what each middleware **must enforce** — but does not prescribe:

- how a middleware is **designed and implemented** (pipeline model, contract shape, testability),
- how middleware are **ordered** relative to each other in the request/message processing chain,
- how middleware are **registered and discoverable** at the spec level,
- how middleware specs **link to real code** in multi-repo workspaces.

ADR-0014 (Hexagonal Architecture) requires that all infrastructure concerns — including middleware — remain in the adapter/infrastructure layer and never pollute the domain core. ADR-0017 introduced a domain registry pattern under `specs/architecture/domain/` with multi-repo linking via `entry.*` IDs in `repo.yaml`. The same registry and linking patterns can be extended to middleware.

Relevant governance:

- Shell Backend composition: `docs/adr/ADR-0008-shell-backend-middleware-composition.md`
- Hexagonal Architecture: `docs/adr/ADR-0014-backend-hexagonal.md`
- Domain composition and registration: `docs/adr/ADR-0017-domain-composition-and-registration.md`
- Backend Shell App spec: `specs/architecture/backend-shell-app.md`
- Multi-repo baseline: `docs/adr/ADR-0016-multi-repo-registry-quality-gates.md`
- Per-repo index contract: `specs/rules/repo-index.md`
- Quality gates catalog: `specs/rules/quality-gates.md`

## Decision

### 1) Middleware pipeline model

Middleware form an **ordered processing pipeline** (chain of responsibility) that wraps domain handler execution in the Backend Shell App.

- Each middleware is an **independent, composable stage** in the pipeline.
- The pipeline applies to both **HTTP request processing** and **message handling** paths.
- The Shell App is responsible for assembling the pipeline at build time; middleware MUST NOT self-insert.

Execution flow (conceptual):

```
Inbound request/message
  → [Auth] → [Trace] → [Error] → [Messaging*] → Domain Handler → response/ack
```

\* Messaging middleware applies only on the messaging path.

### 2) Middleware ordering contract

Each registered middleware has an explicit **pipeline position** that determines its execution order. Positions are defined as stable numeric ranges to allow future insertions without renumbering.

Baseline ordering:

| Position | Middleware ID | Category  | Rationale |
|----------|--------------|-----------|-----------|
| 100      | `mw.auth`    | mandatory | Identity/tenant context must be established first |
| 200      | `mw.trace`   | mandatory | Correlation IDs available for all downstream stages |
| 300      | `mw.error`   | mandatory | Catches exceptions from all subsequent stages and domain handlers |
| 400      | `mw.messaging` | mandatory | Applies to messaging path; enforces idempotency and trace propagation |
| 500      | `mw.audit`   | optional  | Operates on authenticated, traced context |
| 600      | `mw.cache`   | optional  | Domain-scoped or shell-level caching, after auth/trace are resolved |

Rules:

- Positions MUST be monotonically increasing in execution order.
- New middleware MUST choose a position that preserves the ordering invariant.
- Mandatory middleware positions MUST NOT be changed without a new ADR.
- Position gaps (100-step increments) are intentional to allow future insertions.

### 3) Single middleware design principles

Each middleware MUST follow these design principles:

- **Single Responsibility.** One middleware = one cross-cutting concern. Orthogonal concerns MUST NOT be combined in a single middleware.
- **Framework-agnostic contract.** The middleware contract is defined via an abstract port/interface (aligned with ADR-0014). Concrete framework bindings (e.g., servlet filters, interceptors) are adapters.
- **Stateless processing.** Middleware MUST NOT mutate domain state. Middleware MAY enrich request/message context (e.g., auth identity, trace IDs, locale).
- **Side-effect-free initialization.** Middleware registration MUST be explicit and side-effect-free (no classpath scanning, no global state mutation at load time).
- **Isolated testability.** Each middleware MUST be testable in isolation (unit level) without starting the Shell App or other middleware. Contract tests (`qg.tests.contract`) verify middleware behavior in the context of the assembled pipeline.
- **Narrow interface.** Middleware MUST expose a minimal interface: accept a context/request, perform its concern, delegate to the next stage or short-circuit with an error/response.
- **Fail-fast on misconfiguration.** If a mandatory middleware cannot initialize (e.g., missing auth keys), it MUST fail at startup, not silently degrade at runtime.

### 4) Middleware hexagonal alignment

Per ADR-0014, middleware belongs to the **infrastructure/adapter layer**:

- Middleware implementations MUST NOT reside in the domain core.
- Domain code MUST NOT depend on middleware implementations.
- Domain code MAY depend on narrow abstractions (ports) that middleware provides (e.g., an auth context port that exposes current user identity).
- These ports are part of the domain's **inbound port** contract — the domain declares what context it needs; the middleware adapter satisfies it.

### 5) Middleware registry in specs

We introduce a dedicated architecture registry for middleware, following the pattern established by ADR-0017 for domains:

- Location: `specs/architecture/middleware/`
- Index and README: `specs/architecture/middleware/README.md`
- Per-middleware spec files: `specs/architecture/middleware/<id>.md` (e.g., `auth.md`, `trace.md`, `error.md`, `messaging.md`)

Each middleware spec file MUST contain:

| Section | Description |
|---------|-------------|
| **Middleware ID** | Stable identifier (e.g., `mw.auth`) |
| **Category** | `mandatory` or `optional` |
| **Pipeline Position** | Numeric position from the ordering contract |
| **Contract** | Input expectations, output guarantees, preconditions, postconditions |
| **Quality Gates** | Which `qg.*` gates apply |
| **Implementation Ref** | Entry-point ID: `repo.backend :: entry.middleware.<id>` |

The README serves as the index table listing all registered middleware with their ID, category, position, spec file, and entry-point ID.

### 6) Linking middleware specs to code (multi-repo)

Following the same linking pattern as ADR-0017 §4:

- Middleware spec files reference implementation via **entry-point IDs** with the namespace `entry.middleware.*`.
- Entry-point IDs MUST be declared in the backend repository's root `repo.yaml`.
- Resolution chain: middleware spec → `entry.middleware.<id>` → `repo.backend` (via workspace registry) → `repo.yaml` → `entrypoints[].path` → code.

Convention for backend `repo.yaml`:

```yaml
entrypoints:
  - id: entry.middleware.auth
    path: starters/auth/
  - id: entry.middleware.trace
    path: starters/trace/
  - id: entry.middleware.error
    path: starters/error/
  - id: entry.middleware.messaging
    path: starters/messaging/
```

This is a convention — actual paths are defined by the backend repository, not by this ADR.

### 7) Extensibility model

To add a new middleware:

1. Create a spec file in `specs/architecture/middleware/<id>.md`.
2. Add an entry to the README index table.
3. Choose a pipeline position that preserves ordering invariants.
4. Declare `entry.middleware.<id>` in the backend `repo.yaml`.
5. Implement the middleware as an adapter behind the framework-agnostic port.
6. Ensure `qg.tests.contract` and `qg.arch.boundaries` cover the new middleware.

Optional middleware MAY be contributed by domain repositories if they only apply within that domain's scope. Shell-level middleware MUST reside in the shell/starters area.

### Spec impact (transformation targets)

This ADR is expected to produce:

- `specs/architecture/middleware/README.md` — middleware registry index
- `specs/architecture/middleware/auth.md` — Auth middleware spec
- `specs/architecture/middleware/trace.md` — Trace middleware spec
- `specs/architecture/middleware/error.md` — Error middleware spec
- `specs/architecture/middleware/messaging.md` — Messaging middleware spec
- Update to `specs/architecture/backend-shell-app.md` §8 — cross-reference to middleware registry
- Convention for `entry.middleware.*` in backend `repo.yaml`

## Consequences

### Positive

- Single source of truth for middleware catalog with traceable link to code via `entry.*` IDs.
- Explicit ordering contract prevents implicit or conflicting middleware sequencing.
- Design principles ensure testable, replaceable, hexagonal-compliant middleware.
- Extensibility model provides a clear path for adding new middleware without modifying existing ones.
- Consistent registry pattern (mirrors ADR-0017 domain registry) reduces cognitive overhead.

### Negative

- Additional overhead to maintain middleware spec files alongside code.
- Entry-point IDs must be synchronized between spec repo and backend repo.
- Numeric ordering may need re-evaluation if the pipeline model evolves significantly (e.g., branching pipelines).

## Alternatives Considered

1. **Describe middleware only in `backend-shell-app.md` (no separate registry)**
   - Rejected: §5 of that spec is intentionally minimal; detailed per-middleware contracts, ordering, and code linking need dedicated files.

2. **YAML-based middleware registry (like domain registry)**
   - Rejected: middleware specs have richer narrative content (contract descriptions, pre/postconditions) that benefit from markdown format. Domain registry entries are primarily metadata and suit YAML better.

3. **Convention-based paths instead of entry-point IDs**
   - Rejected: hardcoding paths couples specs to repository layout; entry-point IDs decouple discovery from structure.

4. **Runtime-determined middleware ordering**
   - Rejected: makes pipeline behavior non-deterministic and harder to test; contradicts build-time composition principle from ADR-0008.

## Decision Drivers

- Need for explicit, verifiable middleware ordering in the pipeline.
- Hexagonal architecture compliance for cross-cutting infrastructure.
- Consistent registry patterns across domains (ADR-0017) and middleware.
- Multi-repo discoverability via existing `entry.*` / `repo.yaml` contracts.
- Testability at unit and contract levels.

## Related Decisions

- ADR-0008: Shell Backend Middleware Composition
- ADR-0014: Hexagonal Architecture for Backend Domains
- ADR-0017: Domain Composition and Registration
- ADR-0016: Multi-repo Registry and Quality Gates
- ADR-0005: Stateless JWT in Distributed Domains
- ADR-0007: RFC 9457 Error Handling with i18n
