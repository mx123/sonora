# Repository Index (`repo.yaml`) — Non-SSOT Contract

This document defines the repository-level indexing contract used for multi-repository discovery and automation.

Normative language: **MUST**, **MUST NOT**, **SHOULD**, **MAY** are used as in RFC 2119.

## 1) Purpose

`repo.yaml` is a **non-authoritative index** that answers:

- what areas exist in a repository (navigation), and
- which stable quality gate IDs the repository participates in.

`repo.yaml` **MUST NOT** become a second requirements model. Authoritative intent remains under `specs/` (see `specs/constitution.md`).

## 2) Discovery

- A repository **MUST** place the index at the repository root: `./repo.yaml`.
- Tooling **MUST NOT** search alternate paths by default.

## 3) Scope and constraints

`repo.yaml`:

- **MUST** contain only:
  - `id`
  - `entrypoints[]` (`id`, `path`)
  - `qualityGates[]` (`id`)
- **MUST NOT** contain:
  - executable commands / scripts / task invocations
  - duplicated requirement content (BV/CAP/BR/NFR bodies)
  - secrets, tokens, environment values

## 4) Terms

- **Repo entrypoint**: a navigation/automation handle (`id` + `path`) pointing to a repository area.
- **Runtime entrypoint**: a runtime integration contract (e.g., federated UI `mount/init`). It is a different concept.

## 5) Entry point IDs

- `entry.*` IDs are stable identifiers for areas in the repository.
- `path` is repository-relative and **MUST** use forward slashes.

## 6) Quality gate IDs

- `qualityGates[].id` values are stable, tool-neutral IDs defined in `specs/rules/quality-gates.md`.
- `repo.yaml` only declares participation. Gate semantics live in the catalog.

## 7) Change policy

- Changing the meaning of this contract **MUST** be done via ADR.
- Adding new entrypoints or declaring new quality gates **SHOULD** be reviewable and minimal.
