# Frontend Shells (Web/Mobile) and Domain UIs

Status: Adopted (via ADR-0016)

This document specifies the **authoritative, normative** frontend shell contract and its relation to domain UIs.

It complements `specs/architecture/federated-ui-composition.md` by making the “landing place” and responsibilities explicit.

## 1) Terms

- **Shell (frontend)**: the host application that composes multiple Domain UIs into a single product experience.
- **Domain UI**: a bounded UI module/package owned by a domain.
- **Runtime entrypoint**: the explicit integration point a Domain UI exposes to the Shell (e.g., `entrypoint(context)`).

## 2) Shell responsibilities (normative)

A frontend Shell MUST own:
- global routing/navigation
- authentication/session integration
- global theming/layout primitives
- composition/runtime integration

## 3) Domain UI responsibilities (normative)

A Domain UI MUST own:
- screens/components within its bounded context
- internal UI state and internal navigation within the module
- an explicit runtime entrypoint callable by the Shell

## 4) Boundary rules (hard constraints)

- A Domain UI MUST NOT directly import another Domain UI.
- A Domain UI MUST NOT depend on another Domain UI’s runtime state.
- Cross-domain flows MUST be orchestrated by the Shell via navigation and explicit event contracts.

## 5) Communication model

Allowed:
- Domain → Shell: events and navigation requests via a Shell-owned facade
- Shell → Domain: context passed at mount time; optional explicit callbacks

Not allowed:
- direct cross-domain UI calls
- shared mutable global UI state across domains

## 6) Placement in a multi-repo world

- A repository may contain:
  - the Shell app for a platform (web or mobile)
  - one or more Domain UIs
- The central workspace registry defines which repos participate and which quality gates apply.

## 7) Related specs and governance

- Federated composition contract: `specs/architecture/federated-ui-composition.md`
- Quality gates: `qg.arch.boundaries`, `qg.tests.contract`, `qg.quality.lint`

Implementations MAY vary by framework/module system/runtime; this specification intentionally avoids naming specific technologies.

References:
- ADR-0016 (multi-repo baseline): `docs/adr/ADR-0016-multi-repo-registry-quality-gates.md`
- ADR-0006 (federated UI composition): `docs/adr/ADR-0006-Federated-UI-Composition.md`
- ADR-0015 (frontend slicing): `docs/adr/ADR-0015-frontend-layered-feature-slicing.md`
- Quality gates catalog: `specs/rules/quality-gates.md`
