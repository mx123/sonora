# ADR-0017: Domain Composition and Registration for Hexagonal Backend Domains

- Status: Accepted
- Date: 2026-02-11

## Context

We need a consistent, verifiable way to:

- define what a backend **Domain** is (composition principles) under the adopted Hexagonal Architecture approach,
- integrate domains into a **Backend Shell App** without violating shell boundaries,
- register domains in SSOT documentation while linking them to their implementation code in a **multi-repository workspace**.

Existing governance and contracts:

- Hexagonal Architecture baseline: `docs/adr/ADR-0014-backend-hexagonal.md`.
- Shell integration and boundary contract: `specs/architecture/backend-shell-app.md`.
- Multi-repo baseline and per-repository indexing: `docs/adr/ADR-0016-multi-repo-registry-quality-gates.md`.
- Workspace repository discovery: `specs/registry/workspace-registry.yaml`.
- Minimal per-repo index contract: root `repo.yaml` (see `specs/rules/repo-index.md`).

Constraints:

- The definition MUST be toolchain-agnostic and repository-topology-agnostic.
- The registry MUST be auditable and suitable for CI validation.
- The registry MUST NOT become a requirements model.

## Decision

### 1) Domain composition model (Hexagonal)

A backend domain is composed of two explicit parts:

1. **Domain Core**
   - Includes the domain model and application use-cases.
   - Defines inbound and outbound **ports** (interfaces) that describe what the domain needs and what it offers.
   - MUST be free of frameworks, infrastructure dependencies, and side-effectful initialization.

2. **Domain Container**
   - Provides integration wiring between the Domain Core and concrete adapters.
   - Exposes an explicit, side-effect-free registration entrypoint that can be invoked by the Backend Shell App.
   - MUST NOT self-register via classpath scanning or global initialization.

Adapters MAY live alongside the container or in separate modules, but they MUST remain outside the Domain Core.

### 2) Backend Shell participation model

- Domains participate in a Backend Shell App via **build-time inclusion**.
- Inclusion MUST be explicit: the shell selects which domain containers are wired into the application.
- Exclusion MUST be strict: excluded domains MUST NOT contribute routes, consumers, jobs, persistence, or other runtime effects.

This aligns with the shell contract in `specs/architecture/backend-shell-app.md`.

### 3) Domain registration in specs

We introduce a dedicated architecture registry for domains:

- Location: `specs/architecture/domain/`
- Index file: `specs/architecture/domain/domains.yaml`
- Detailed per-domain files: `specs/architecture/domain/DOM-####.yaml`

Domain IDs:

- Each registered domain MUST have a stable ID in the form `DOM-####`.
- The ID is a registry identifier and does not replace requirement identifiers (e.g., `CAP-*`, `BR-*`).

### 4) Linking registry entries to real domain code (multi-repo)

To link SSOT architecture registry entries to actual code without duplicating repository metadata:

- The domain registry MUST reference the implementation repository by **repoId**.
- `repoId` MUST match an entry in `specs/registry/workspace-registry.yaml` (`repos[].id`).
- The domain registry MUST reference implementation locations via **entrypoint IDs** defined in that repository's root `repo.yaml`.

Linking chain:

`DOM-####` (domain registry) → `repoId` (workspace registry) → repository `url/ref` → repository root `repo.yaml` → `entrypoints[].id/path` → code

This keeps:

- repository discovery in one place (workspace registry),
- code navigation contracts minimal and per-repo (`repo.yaml`),
- domain registry focused on architecture-level registration.

#### Example (non-normative)

Domain index (`specs/architecture/domain/domains.yaml`):

```yaml
schemaVersion: 1

domains:
   - DOM-0001
```

Domain entry (`specs/architecture/domain/DOM-0001.yaml`):

```yaml
id: DOM-0001
status: proposed
name: Example Domain

repoId: repo.backend

entrypoints:
   core: entry.domain.example.core
   container: entry.domain.example.container
```

Workspace registry (`specs/registry/workspace-registry.yaml`):

```yaml
repos:
   - id: repo.backend
      url: <backend-repo-url>
      ref: <branch|tag|commit>
```

Implementation repository root index (`repo.yaml` in the backend repository):

```yaml
entrypoints:
   - id: entry.domain.example.core
      path: <path-to-domain-core>
   - id: entry.domain.example.container
      path: <path-to-domain-container>
```

## Consequences

### Positive

- Domains become discoverable and auditable in specs without becoming a requirements model.
- Hexagonal boundaries become enforceable at the integration point (domain container).
- Multi-repo linking uses existing, minimal contracts (`workspace-registry.yaml` + `repo.yaml`).

### Negative

- Requires maintaining domain registry entries alongside per-repo `repo.yaml` entrypoints.
- Cross-repository validation may require workspace tooling that can materialize repositories (clone/checkout) when desired.

## Alternatives Considered

1. **Store repo URL/ref directly in each domain entry**
   - Rejected: duplicates workspace registry concerns and drifts quickly.

2. **Register domains only in code (no spec registry)**
   - Rejected: reduces auditability and makes shell participation ambiguous.

3. **Runtime plugin loading**
   - Rejected: adds operational/security complexity and is not required for the baseline.

## Decision Drivers

- Verifiable, toolchain-agnostic architecture contracts.
- Clear domain boundaries and integration points.
- Multi-repo workspace discoverability with minimal duplication.
