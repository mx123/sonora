# Derived Artifacts

This directory contains **generated outputs only**.

Sources of truth live under `specs/`.

Examples of derived outputs:
- `openapi/`
- `asyncapi/`
- `structurizr/`
- `trace/` (traceability matrices/reports)

Rules:
- Do not edit files here manually.
- CI regenerates outputs deterministically and fails on non-reproducible diffs.
