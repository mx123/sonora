# Federated UI Composition (Shell-based)

Status: Adopted (via ADR-0006)

This document is the **authoritative, normative** specification for federated UI
composition in this repository. It restates ADR-0006 as enforceable constraints.

## 1) Intent

Enable independently delivered domain UIs (web and mobile) to compose into a
single product without cross-domain coupling while preserving a unified user
experience.

## 2) Ownership model

- The **Shell** owns:
  - global routing/navigation
  - authentication integration
  - global theming and layout
  - composition/runtime integration
- Each **Domain UI** owns:
  - its UI screens/components within its bounded context
  - its internal UI state and internal navigation (within its module)

## 3) Integration contract

Domains MUST integrate with the Shell only through an explicit entrypoint.

Minimum contract requirements:
- Domain UI MUST expose an entrypoint callable by the Shell (e.g., `entrypoint(context)`)
  that renders into a container controlled by the Shell.
- The Shell MUST pass a minimal `context` containing only:
  - navigation facade (Shell-owned)
  - auth/session access abstraction (read-only where possible)
  - theme tokens/design primitives
  - event bus or event-emitter interface for domain->shell notifications

## 4) Boundary rules (hard constraints)

- A Domain UI MUST NOT directly import another Domain UI package/module.
- A Domain UI MUST NOT depend on another Domain UI’s runtime state.
- Shared libraries across domains MUST be restricted to stateless primitives
  (types, design tokens, logging, small utilities) and MUST NOT contain business
  UI components or domain business logic.
- Cross-domain flows MUST be orchestrated by the Shell via navigation and
  explicit event contracts.

## 5) Communication model

Allowed:
- Domain -> Shell: events (e.g., `DomainActionCompleted`) and navigation requests
  through the Shell navigation facade.
- Shell -> Domain: context passed at mount time; optional explicit callbacks.

Not allowed:
- direct cross-domain UI calls
- shared mutable global UI state across domains

## 6) Versioning and compatibility

- Domain entrypoint contracts SHOULD be versioned.
- The Shell SHOULD remain backward-compatible with at least the previous contract
  version to enable independent releases.

## 7) Relation to requirements

- BV-0003 is realized by CAP-0003.
- NFR-0020 defines the mandatory boundary constraints for composed UIs.

References:
- ADR-0006 (rationale): docs/adr/ADR-0006-federated-ui-composition.md

Related:
- Frontend shell contract: `specs/architecture/frontend-shells.md`
