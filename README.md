# Sonora

**Meta-documentation framework for distributed service platforms.**

Sonora is a governance-first specification repository that defines platform architecture, domain models, quality gates, and operational contracts — all as code. It serves as a **reusable meta-template** from which concrete project instances are bootstrapped, and provides tooling to keep those instances synchronized with upstream evolution.

## Repository Structure

```
├── docs/
│   ├── constitution.md              # Documentation governance (ADR policy, derived artifacts)
│   ├── adr/                         # Architecture Decision Records (ADR-0001 — ADR-0019)
│   └── derived/                     # Generated artifacts (Mermaid, OpenAPI, AsyncAPI, traces)
├── specs/
│   ├── constitution.md              # Specification governance (SSOT, delta workflow, traces)
│   ├── architecture/
│   │   ├── domain/                  # Domain registry (DOM-*.yaml, domains.yaml)
│   │   ├── middleware/              # Middleware pipeline specs (auth → cache, 6 positions)
│   │   └── structurizr/             # C4 workspace model
│   ├── domain/                      # Command & event catalog (CMD-*, EVT-*)
│   ├── requirements/
│   │   ├── business-values/         # BV-*.yaml
│   │   ├── capabilities/            # CAP-*.yaml
│   │   ├── business-rules/          # BR-*.yaml
│   │   ├── nfr/                     # NFR-*.yaml
│   │   └── trace-links.yaml         # Full traceability graph
│   ├── deltas/                      # Change records (delta-governed workflow)
│   ├── schemas/                     # JSON schemas for all artifact types
│   ├── registry/                    # Workspace registry, gate mapping
│   └── rules/                       # Error registry, naming conventions
├── tools/
│   ├── bootstrap.py                 # Project instantiation CLI
│   ├── reqingest.py                 # Requirements ingestion pipeline (LLM-assisted)
│   ├── taskgen.py                   # Task generation from deltas (LLM-assisted)
│   └── spec-ci/
│       ├── validate.py              # SSOT validation (schemas, traces, domains, deltas)
│       └── generate_structurizr.py  # C4 diagram generation
├── bootstrap.yaml                   # Project configuration template
└── repo.yaml                        # Repository identity and quality gate IDs
```

## Dual Nature: Meta-Template vs Project Instance

Every artifact in this repository falls into one of four categories:

| Category          | Description                                                   | Ownership          |
|-------------------|---------------------------------------------------------------|---------------------|
| **meta**          | Reusable patterns, schemas, tools, governance, baseline ADRs  | Upstream template   |
| **project**       | Domain definitions, business rules, traces, deltas            | Project team        |
| **parameterized** | Meta structure with `{{placeholder}}` tokens replaced at bootstrap | Meta → project |
| **baseline seed** | Optional Auth domain package (DOM-0001, BV/CAP/BR, CMD/EVT)  | Meta; adopted or discarded |

See [ADR-0019](docs/adr/ADR-0019-meta-template-project-separation.md) for the full rationale.

## Bootstrap: Creating a Real Project

A new project is instantiated from Sonora in three steps:

### 1. Configure

Copy and fill `bootstrap.yaml` with project-specific values:

```yaml
project:
  name: "Acme Platform"
  org: "acme"
  errorBaseUri: "https://errors.acme.example.com/"

repos:
  specs: "https://github.com/acme/specs"
  backend: "https://github.com/acme/backend"
  frontendWeb: "https://github.com/acme/frontend-web"

tech:
  backend:
    lang: kotlin
    framework: spring-boot
  frontend:
    framework: react
  ci: github-actions
  containerRegistry: "ghcr.io/acme"

seed: auth          # 'auth' adopts the baseline Auth domain; 'none' starts empty

domains:
  - name: Billing
    description: "Subscription and payment management"
```

The full schema is defined in `specs/schemas/bootstrap.schema.json`.

### 2. Bootstrap

```bash
python tools/bootstrap.py --config bootstrap.yaml
```

The CLI performs:
1. **Validates** config against the JSON schema.
2. **Replaces** parameterized placeholders (`CHANGE_ME`, `{{project.*}}`) in all target files.
3. **Adopts** the seed package (Auth domain) or discards it.
4. **Scaffolds** additional domains from the `domains` list.
5. **Cleans** the Example Domain placeholder (DOM-0002) and stale artifacts.
6. **Validates** the result by running `tools/spec-ci/validate.py` as a final gate.

Use `--dry-run` to preview changes without writing files.

### 3. Verify

```bash
python tools/spec-ci/validate.py
```

The validator checks schema compliance, trace completeness, domain registry consistency, and delta integrity.

## Working with a Real Project

After bootstrap, the project enters a continuous lifecycle driven by two automated pipelines and governed by the delta workflow. The goal is to keep the path **from business intent to running code fully traceable and machine-verifiable**.

### Product Lifecycle Overview

```
                     ┌─────────────────────────────────────────────────────┐
                     │                  Sonora Lifecycle                   │
                     └─────────────────────────────────────────────────────┘

  ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
  │  Phase 0 │ ───► │  Phase 1 │ ───► │  Phase 2 │ ───► │  Phase 3 │ ───► │  Phase 4 │
  │Bootstrap │      │ Require- │      │  Delta   │      │  Task    │      │  Code &  │
  │          │      │  ments   │      │ Govern-  │      │  Genera- │      │  Verify  │
  │          │      │ Ingest   │      │  ance    │      │  tion    │      │          │
  └──────────┘      └──────────┘      └──────────┘      └──────────┘      └──────────┘
  bootstrap.py       reqingest.py     manual review      taskgen.py       LLM agents +
                     (LLM-assisted)   + delta apply                       validate.py
```

### Phase 0 — Bootstrap (one-time)

Create the project instance from the meta-template (see [Bootstrap](#bootstrap-creating-a-real-project) above). The result is a repo with governance, schemas, and optionally the Auth domain seed — ready for requirements work.

### Phase 1 — Requirements Ingestion

New business requirements enter the system through `reqingest.py`. The tool accepts natural language or structured input and decomposes it into SSOT-compliant artifacts:

```bash
# A product owner describes a new capability
python tools/reqingest.py --input \
  "Customers can reset their password via a time-limited email link. \
   The link must expire after 30 minutes and be single-use."

# Or batch from a file
python tools/reqingest.py --file sprint-requirements.yaml
```

The pipeline automatically:
- Creates **BV** (Business Value), **CAP** (Capability), **BR** (Business Rule), **NFR** (Non-Functional Requirement) YAML files in their SSOT folders.
- Appends **CMD** (Command) and **EVT** (Event) sections to the domain model markdown.
- Adds **trace links** connecting the new artifacts into the existing traceability graph.
- Generates a **delta file** recording all changes.
- Runs **validate.py** as a gate to ensure structural consistency.

### Phase 2 — Delta Governance

Every delta-governed change flows through the delta workflow:

1. `reqingest.py` generates delta files with status `proposed`.
2. The team reviews the generated artifacts and the delta in a PR.
3. On merge, the delta status advances to `applied`.
4. `validate.py` runs in CI, enforcing schema compliance, trace coverage, and domain consistency.

**What the team reviews:**
- Are the decomposed artifacts correct and complete?
- Do trace links accurately connect BV → CAP → BR/NFR → CMD/EVT?
- Does the delta accurately describe the change scope?

### Phase 3 — Task Generation

Once a delta is `applied`, `taskgen.py` reads it and generates implementation task specifications for LLM coding agents:

```bash
# Generate tasks from a specific delta
python tools/taskgen.py --delta specs/deltas/2026-03-01-password-reset.yaml

# Preview impact analysis without calling LLM
python tools/taskgen.py --delta specs/deltas/2026-03-01-password-reset.yaml --plan

# Generate individual markdown task files
python tools/taskgen.py --delta ... --format files --out-dir tasks/

# Process all pending deltas
python tools/taskgen.py --all-pending
```

Each task includes:
- **Layer** — architectural layer (`domain-core`, `application`, `adapter-in`, `adapter-out`, `middleware`, `test`).
- **Target files** — which code modules to create or modify (hexagonal path conventions).
- **Acceptance criteria** — derived from the BR and CAP that triggered the delta.
- **Contracts** — API schemas, event payloads, error codes from the spec artifacts.
- **Dependency order** — tasks are topologically sorted so agents can work sequentially.
- **Quality gates** — applicable gate IDs from `repo.yaml`.

### Phase 4 — Code & Verify

LLM agents (or developers) implement tasks against the specification contracts. Validation gates ensure alignment:

- `validate.py` — spec integrity (always active).
- Quality gate IDs from `repo.yaml` map to CI checks: unit tests, contract tests, architecture conformance, SAST.
- If `CAP.status == implemented`, the validator enforces that `trace.domain.commands[]` and `trace.domain.events[]` resolve to actual anchors in the codebase.

### Cycle Repeats

Each new business requirement re-enters at Phase 1. The delta log in `specs/deltas/` provides a complete, auditable history of how the system evolved from intent to implementation.

## Upstream Synchronisation

After bootstrap, the project maintains a link to Sonora for ongoing platform evolution:

### Submodule Setup

```bash
# In the bootstrapped project
git submodule add <sonora-upstream-url> meta
```

### Pulling Updates

```bash
cd meta && git pull origin main && cd ..
python meta/tools/upgrade.py --from v1.0 --to v1.1   # (planned)
python meta/tools/spec-ci/validate.py
```

**Upgrade boundaries:**
- Meta updates (schemas, tools, NFRs, middleware specs) are applied automatically — no project conflict.
- New/changed baseline ADRs are reported for manual review.
- Project-owned files (`specs/domain/`, `specs/requirements/`, `specs/deltas/`) are **never touched** by upstream.

## Governance Model

Sonora uses a **dual-constitution** governance model:

- **[docs/constitution.md](docs/constitution.md)** — governs documentation artifacts (ADRs, derived outputs).
- **[specs/constitution.md](specs/constitution.md)** — governs specification artifacts (requirements, domains, deltas).

### Delta Workflow

Any change to delta-governed artifacts (BV, CAP, BR, NFR, traces) **MUST** include a delta file under `specs/deltas/`:

```
specs/deltas/YYYY-MM-DD-short-description.yaml
```

Deltas flow through statuses: `draft` → `proposed` → `applied`.

### Traceability

All requirements are linked via `specs/requirements/trace-links.yaml`:

```
BV → CAP → BR → CMD/EVT
BV → CAP → NFR
```

## Tooling

| Tool | Path | Purpose |
|------|------|---------|
| **validate.py** | `tools/spec-ci/validate.py` | SSOT validation — schemas, traces, domains, middleware, deltas |
| **bootstrap.py** | `tools/bootstrap.py` | Project instantiation from meta-template |
| **generate_structurizr.py** | `tools/spec-ci/generate_structurizr.py` | C4 diagram generation from workspace.dsl |
| **reqingest.py** | `tools/reqingest.py` | Requirements ingestion pipeline (LLM-assisted) |
| **taskgen.py** | `tools/taskgen.py` | LLM task generation from deltas |

### Requirements Ingestion Pipeline (reqingest.py)

LLM-assisted pipeline that accepts natural-language or structured requirements and decomposes them into SSOT-compliant specification artifacts.

#### Pipeline Stages

```
Input → CLASSIFY → DECOMPOSE → PLACE → DELTA → VALIDATE → Output
```

| Stage | What happens |
|-------|-------------|
| **CLASSIFY** | LLM reads the requirement and determines which artifact types are needed (BV, CAP, BR, NFR, CMD, EVT). |
| **DECOMPOSE** | LLM splits compound requirements into atomic spec artifacts. Each artifact gets the next available sequential ID (e.g., if BV-0003 exists, the next BV is BV-0004). |
| **PLACE** | Writes each artifact to its SSOT location: YAML files for BV/CAP/BR/NFR, appends markdown sections with `<a id="CMD-XXXX">` anchors for CMD/EVT, updates `trace-links.yaml`. |
| **DELTA** | Generates a delta file (`specs/deltas/YYYY-MM-DD-<slug>.yaml`) with `status: proposed`, listing all governed artifact changes. |
| **VALIDATE** | Runs `validate.py` as a gate. On failure, the LLM receives the validation errors and attempts a repair (up to 3 retries). |

#### Context Awareness

Before calling the LLM, `reqingest.py` reads the full SSOT state:
- All existing artifact IDs (prevents ID collisions and duplicates).
- Registered domains (ensures CMD/EVT are assigned to valid domains).
- Current trace graph (LLM connects new artifacts into the existing graph).
- JSON schemas for all artifact types (LLM output conforms to schemas).

The system prompt is constructed dynamically from constitutions, schemas, and current state.

#### Usage

```bash
# Single requirement (natural language)
python tools/reqingest.py --input "Users should reset passwords via email link"

# Batch from file (one per line or YAML list)
python tools/reqingest.py --file sprint-requirements.yaml

# Preview plan only (LLM decomposition, no file writes)
python tools/reqingest.py --input "..." --plan

# Dry-run (show file operations, no actual writes)
python tools/reqingest.py --input "..." --dry-run

# Skip validation gate (not recommended)
python tools/reqingest.py --input "..." --skip-validation
```

#### Configuration (environment variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `REQINGEST_LLM_PROVIDER` | `openai` | LLM provider: `openai` or `anthropic` |
| `REQINGEST_LLM_BASE_URL` | `https://api.openai.com/v1` | API base URL (supports any OpenAI-compatible endpoint) |
| `REQINGEST_LLM_API_KEY` | *(required)* | API key for the LLM provider |
| `REQINGEST_LLM_MODEL` | `gpt-4o` | Model name |

#### Output Example

For input `"Users should reset passwords via email link"`, the pipeline might produce:

```
specs/requirements/business-values/BV-0004.yaml   # Self-service password recovery
specs/requirements/capabilities/CAP-0004.yaml      # Password reset via email link
specs/requirements/business-rules/BR-0006.yaml     # Password reset link expiry
specs/domain/commands.md                           # CMD-0007: Request Password Reset (appended)
specs/domain/events.md                             # EVT-0007: Password Reset Requested (appended)
specs/requirements/trace-links.yaml                # 2 new links added
specs/deltas/2026-03-01-password-reset.yaml        # Delta with 3 governed changes
```

### Task Generation Pipeline (taskgen.py)

LLM-assisted pipeline that reads applied deltas and generates implementation task specifications for LLM coding agents.

#### Pipeline Stages

```
Delta → IMPACT → DECOMPOSE → SPECIFY → ORDER → Tasks
```

| Stage | What happens |
|-------|-------------|
| **IMPACT** | Resolves delta targets to full spec context: loads CAP/BR/NFR YAML, parses CMD/EVT markdown sections, finds related BRs via trace links, identifies affected middleware and domains. |
| **DECOMPOSE** | LLM breaks each code-impacting change into atomic implementation tasks. Status-only changes (e.g., "proposed → approved") are automatically skipped. |
| **SPECIFY** | LLM generates a task spec per unit: target files (hexagonal path conventions), acceptance criteria, error codes, contracts, quality gates. |
| **ORDER** | Topologically sorts tasks by `depends_on` with layer-priority tie-breaking: `domain-core` → `application` → `adapter-in/out` → `middleware` → `test`. |

#### Context Awareness

Before calling the LLM, `taskgen.py` reads:
- Backend Shell App spec (composition model, domain inclusion semantics).
- Middleware registry (IDs, positions, categories).
- Domain definitions from `specs/architecture/domain/`.
- Full CMD/EVT specs (payload, invariants, error codes) from `specs/domain/`.
- Related BRs via `trace-links.yaml`.
- Quality gate IDs from `repo.yaml`.

The system prompt includes hexagonal architecture guidance, middleware pipeline layout, and task structuring rules.

#### Usage

```bash
# Impact analysis only (no LLM call)
python tools/taskgen.py --delta specs/deltas/2026-02-11-auth-domain-model.yaml --plan

# Full task generation (requires API key)
python tools/taskgen.py --delta specs/deltas/2026-02-11-auth-domain-model.yaml

# Output as individual markdown files
python tools/taskgen.py --delta ... --format files --out-dir tasks/

# Process all pending deltas
python tools/taskgen.py --all-pending
```

#### Configuration (environment variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `TASKGEN_LLM_PROVIDER` | `openai` | LLM provider: `openai` or `anthropic` |
| `TASKGEN_LLM_BASE_URL` | `https://api.openai.com/v1` | API base URL (supports any OpenAI-compatible endpoint) |
| `TASKGEN_LLM_API_KEY` | *(required)* | API key for the LLM provider |
| `TASKGEN_LLM_MODEL` | `gpt-4o` | Model name |

## Architecture References

| ADR | Title |
|-----|-------|
| [ADR-0001](docs/adr/ADR-0001-llm-stream-sdd.md) | LLM Stream SDD |
| [ADR-0004](docs/adr/ADR-0004-gradle-monorepo.md) | Gradle Monorepo (Superseded) |
| [ADR-0005](docs/adr/ADR-0005-stateless-jwt-distributed-domains.md) | Stateless JWT for Distributed Domains |
| [ADR-0006](docs/adr/ADR-0006-federated-ui-composition.md) | Federated UI Composition |
| [ADR-0007](docs/adr/ADR-0007-rfc-9457-error-handling-i18n.md) | RFC 9457 Error Handling & i18n |
| [ADR-0008](docs/adr/ADR-0008-shell-backend-middleware-composition.md) | Shell Backend Middleware Composition |
| [ADR-0009](docs/adr/ADR-0009-security-starters-auth-audit.md) | Security Starters (Auth & Audit) |
| [ADR-0010](docs/adr/ADR-0010-observability-starters-trace-errors.md) | Observability Starters |
| [ADR-0011](docs/adr/ADR-0011-messaging-starter-inter-domain-communication.md) | Messaging Starter |
| [ADR-0012](docs/adr/ADR-0012-persistence-and-cache-starters.md) | Persistence & Cache Starters |
| [ADR-0013](docs/adr/ADR-0013-quality-control-verifiable-architecture.md) | Quality Control & Verifiable Architecture |
| [ADR-0014](docs/adr/ADR-0014-backend-hexagonal.md) | Backend Hexagonal Architecture |
| [ADR-0015](docs/adr/ADR-0015-frontend-layered-feature-slicing.md) | Frontend Layered Feature Slicing |
| [ADR-0016](docs/adr/ADR-0016-multi-repo-registry-quality-gates.md) | Multi-Repo Registry & Quality Gates |
| [ADR-0017](docs/adr/ADR-0017-domain-composition-and-registration.md) | Domain Composition & Registration |
| [ADR-0018](docs/adr/ADR-0018-middleware-design-principles-registry.md) | Middleware Design Principles & Registry |
| [ADR-0019](docs/adr/ADR-0019-meta-template-project-separation.md) | Meta-Template and Project Separation |

## License

Sonora is licensed under **AGPL-3.0-or-later**.

- Full license terms: see [LICENSE](LICENSE)
- Output exception (generated project instances may be licensed separately): see [LICENSE-EXCEPTION](LICENSE-EXCEPTION)
