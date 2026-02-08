# Quality Gates Catalog (`qg.*`)

This document defines stable, tool-neutral **quality gate IDs**.

A gate ID is a semantic handle that can be implemented differently per language/toolchain, but its **meaning and expected evidence** remain stable.

Normative language: **MUST**, **MUST NOT**, **SHOULD**, **MAY** are used as in RFC 2119.

## 1) Why gate IDs (not tool tasks)

- Gate IDs decouple governance from build tools.
- CI can require gate IDs (via per-repo mapping) without leaking module topology.

## 2) Activation

- A gate **MUST** exist for every active repository.
- If an area is not active yet, the gate **MAY** run in no-op/informational mode, but it must be explicit and auditable.

## 3) Gate definitions (baseline)

### `qg.specs.validate`

- Meaning: validate SSOT spec artifacts (schemas + traceability + delta rules).
- Evidence: validator output is machine-verifiable (pass/fail).

### `qg.docs.derived.verify`

- Meaning: derived artifacts are deterministic and not manually edited.
- Evidence: regeneration produces no diff.
- Semantic sub-check: `docs.derived.verify.clean`.

### `qg.arch.boundaries`

- Meaning: architectural boundaries and layering rules are enforced.
- Minimum responsibilities:
  - domain core remains framework-agnostic
  - forbidden dependency directions are rejected (layering)
  - disallowed cross-domain coupling is rejected
- Evidence: machine-verifiable rule set + pass/fail signal.

### `qg.tests.unit`

- Meaning: unit tests for domain/application logic.
- Evidence: test runner produces pass/fail.

### `qg.tests.contract`

- Meaning: contract tests at boundaries (shell↔domain container, API/messaging contracts).
- Evidence: pass/fail + contract artifacts where applicable.

### `qg.tests.integration.narrow`

- Meaning: narrow integration tests for infrastructure adapters (DB/messaging/cache) at component boundaries.
- Evidence: pass/fail.

### `qg.tests.component`

- Meaning: component/service-in-a-box tests.
- Evidence: pass/fail.

### `qg.tests.acceptance`

- Meaning: acceptance tests (user/business flows at component boundary).
- Evidence: pass/fail.

### `qg.tests.e2e`

- Meaning: end-to-end tests across components.
- Evidence: pass/fail.

### `qg.tests.smoke`

- Meaning: smoke tests for deployable artifacts/environments.
- Evidence: pass/fail.

### `qg.tests.mutation`

- Meaning: mutation testing for critical decision logic.
- Evidence: pass/fail + machine-verifiable report artifact.

### `qg.tests.contract.external`

- Meaning: contract tests for external provider/system integration.
- Evidence: pass/fail + contract artifacts where applicable.

### `qg.quality.lint`

- Meaning: formatting/lint/static correctness checks.
- Evidence: pass/fail + actionable findings.

### `qg.security.sast`

- Meaning: static security analysis (code-level).
- Evidence: pass/fail + report artifact; policy defines severities.

## 4) Mapping to tooling

- Gate-to-tool mapping is repository-specific and is **not** stored in `repo.yaml`.
- Mapping location is defined by the workspace registry (see `specs/rules/workspace-registry.md`).
