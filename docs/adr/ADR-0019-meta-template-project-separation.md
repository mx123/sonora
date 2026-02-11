# ADR-0019: Meta-Template and Project-Instance Separation with Bootstrap Automation

- Status: Accepted
- Date: 2026-02-11

## Context

The current specification repository serves a dual purpose:

1. **Meta-template**: reusable platform patterns, governance rules, validation tooling, schemas, and baseline ADRs applicable to any distributed service platform project.
2. **Project instance**: concrete domain definitions (Auth), business requirements, C4 model, trace links, and delta history specific to this particular platform.

This dual nature creates several problems:

- New projects must fork the repo and manually find/replace project-specific values (`CHANGE_ME`, `errors.kx.example.com`, `KX Platform`, `Example Domain`).
- There is no clear boundary between what can be safely updated from upstream (meta) and what the project owns (instance).
- Stale generated artifacts (e.g., `workspace.json`, derived Mermaid diagrams) accumulate when the C4 model changes.
- Mixed files (e.g., `error-registry.md`, `commands.md`) contain both reusable structure and project-specific content, making upstream merges conflict-prone.

## Decision

We adopt a **layered meta/project separation** with a deterministic **bootstrap CLI** for instantiation and a **submodule-based upgrade path** for ongoing meta updates.

### 1) Layer Classification

Every artifact falls into one of four categories:

| Category | Description | Ownership |
|----------|-------------|-----------|
| **meta** | Reusable platform patterns, schemas, tools, governance, baseline ADRs, baseline middleware specs, NFRs | Upstream template repo |
| **project** | Domain definitions, business values, capabilities, business rules, trace links, deltas, derived artifacts | Project team |
| **parameterized** | Meta structure with `{{placeholder}}` tokens replaced during bootstrap | Meta → project at bootstrap time |
| **baseline seed** | Optional pre-built Auth domain package (DOM-0001, BV-0001–0003, CAP-0001–0002, BR-0001–0005, CMD/EVT-0001–0006) shipped as a working example | Meta; adopted or discarded during bootstrap |

### 2) Repository Structure

```
<project-root>/
├── meta/                          # git submodule → upstream template
│   ├── docs/
│   │   ├── constitution.md
│   │   └── adr/                   # all 18+ baseline ADRs + TEMPLATE.md
│   ├── specs/
│   │   ├── constitution.md
│   │   ├── schemas/               # JSON schemas (bv, cap, br, nfr, delta, trace, repo)
│   │   ├── rules/                 # quality-gates.md, repo-index.md, workspace-registry.md
│   │   ├── architecture/
│   │   │   ├── backend-shell-app.md
│   │   │   ├── federated-ui-composition.md
│   │   │   ├── frontend-shells.md
│   │   │   ├── middleware/        # auth, trace, error, messaging, audit, cache + README
│   │   │   └── domain/
│   │   │       ├── README.md
│   │   │       └── DOM-0000-template.yaml
│   │   ├── requirements/
│   │   │   └── nfr/               # NFR-0001 through NFR-0021
│   │   ├── adapters/README.md
│   │   ├── api/README.md
│   │   └── messaging/README.md
│   ├── seed/                      # optional Auth domain seed package
│   │   ├── domain/
│   │   │   └── DOM-0001.yaml
│   │   ├── requirements/
│   │   │   ├── business-values/   # BV-0001, BV-0002, BV-0003
│   │   │   ├── capabilities/      # CAP-0001, CAP-0002, CAP-0003
│   │   │   └── business-rules/    # BR-0001 through BR-0005
│   │   ├── domain-model/
│   │   │   ├── commands.md        # CMD-0001 through CMD-0006
│   │   │   └── events.md          # EVT-0001 through EVT-0006
│   │   ├── trace-links.yaml
│   │   └── error-seeds.md         # Auth error codes section
│   ├── templates/                 # parameterized file templates
│   │   ├── workspace-registry.yaml.tmpl
│   │   ├── gate-mapping.yaml.tmpl
│   │   ├── workspace.dsl.tmpl
│   │   ├── error-registry.md.tmpl
│   │   ├── commands.md.tmpl       # structure-only (empty domain sections)
│   │   ├── events.md.tmpl
│   │   └── domains.yaml.tmpl
│   └── tools/
│       ├── spec-ci/               # validate.py, generate_structurizr.py, requirements.txt
│       └── bootstrap.py           # project instantiation CLI
│
├── docs/                          # project-owned (generated + project ADRs)
│   ├── adr/                       # → symlink or copy from meta/docs/adr/ + project-specific ADRs
│   └── derived/                   # generated artifacts (structurizr, openapi, asyncapi, trace)
│
├── specs/                         # project-owned
│   ├── architecture/
│   │   ├── domain/                # DOM-*.yaml, domains.yaml
│   │   └── structurizr/           # workspace.dsl (project-specific)
│   ├── domain/                    # commands.md, events.md (project-specific)
│   ├── requirements/
│   │   ├── business-values/
│   │   ├── capabilities/
│   │   ├── business-rules/
│   │   └── trace-links.yaml
│   ├── deltas/                    # project-specific change history
│   ├── registry/                  # workspace-registry.yaml, gate-mapping per repo
│   ├── rules/
│   │   └── error-registry.md      # project-specific error codes
│   ├── adapters/
│   ├── api/
│   └── messaging/
│
├── .github/workflows/ci.yml       # meta-provided, project may extend
├── repo.yaml                      # project-specific
└── bootstrap.yaml                 # project configuration input
```

### 3) Bootstrap CLI

`python meta/tools/bootstrap.py --config bootstrap.yaml`

The bootstrap CLI reads `bootstrap.yaml` and performs:

1. **Render templates**: replaces `{{project.name}}`, `{{project.errorBaseUri}}`, `{{repos.*}}` in all `.tmpl` files and writes output to `specs/` and `docs/`.
2. **Seed adoption**: if `bootstrap.yaml` contains `seed: auth`, copies the Auth domain seed package into `specs/`.
3. **Domain scaffolding**: for each domain in `bootstrap.yaml`, generates `DOM-XXXX.yaml`, updates `domains.yaml`, adds skeleton sections to `commands.md` and `events.md`.
4. **Clean placeholders**: removes `DOM-0002` (Example Domain) and any remaining `CHANGE_ME` markers.
5. **Validate**: runs `validate.py` as a final gate.
6. **Report**: outputs a summary of generated files and remaining manual steps.

### 4) Upgrade Path

Meta updates are consumed via git submodule:

```bash
cd meta && git pull origin main && cd ..
python meta/tools/upgrade.py --from v1.0 --to v1.1
python meta/tools/spec-ci/validate.py
```

The upgrade script:
- Updates schemas, tools, and NFRs automatically (no project conflict).
- Reports new/changed baseline ADRs for manual review.
- Reports new middleware specs for manual review.
- Never touches project-owned files (`specs/domain/`, `specs/requirements/`, `specs/deltas/`).

### 5) Validate.py Adaptation

The validator MUST resolve paths in both layers:
- Schemas: `meta/specs/schemas/`
- NFRs: `meta/specs/requirements/nfr/`
- Project requirements: `specs/requirements/`
- Domain registry: `specs/architecture/domain/`
- Middleware registry: `meta/specs/architecture/middleware/`

A `META_ROOT` environment variable or auto-detection (`meta/` subdirectory presence) configures the dual-root behavior.

## Consequences

### Positive

- Clean separation: project teams never edit meta files; meta updates never conflict with project content.
- Deterministic bootstrap: new projects are instantiated in seconds with a single config file.
- Selective seed adoption: Auth domain seed is opt-in, not forced.
- Version-controlled upgrades: meta submodule pinning prevents surprise breaking changes.

### Negative

- Submodule management adds git workflow complexity.
- Dual-root path resolution in `validate.py` adds implementation complexity.
- Bootstrap CLI must be maintained as meta evolves (new templates, new config fields).
- Seed package must be kept in sync with ADRs and middleware specs.

## Alternatives Considered

1. **Fork-and-merge**: simple git fork with periodic merge from upstream.
   - Rejected: merge conflicts on every mixed file; no selective adoption.

2. **Package manager distribution**: publish meta as an npm/pip package.
   - Rejected: over-engineered for a spec-only repo; git submodule is sufficient.

3. **Monorepo with directory convention**: keep everything in one repo with README markers.
   - Rejected: no tooling-enforced boundary; human discipline insufficient at scale.
