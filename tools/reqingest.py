#!/usr/bin/env python3
"""
Requirements Ingestion Pipeline — reqingest.py

Accepts natural-language or structured requirements and decomposes them
into SSOT-compliant specification artifacts via LLM-assisted pipeline.

Pipeline stages:
  1. CLASSIFY  — determine artifact types (BV, CAP, BR, NFR, CMD, EVT)
  2. DECOMPOSE — split into atomic spec artifacts with proper IDs
  3. PLACE     — write to SSOT locations, update trace-links
  4. DELTA     — generate delta file recording all changes
  5. VALIDATE  — run validate.py as gate (retry up to 3 times)

Usage:
    # Single requirement (natural language)
    python tools/reqingest.py --input "Users should reset passwords via email link"

    # Batch from file (one requirement per line, or YAML list)
    python tools/reqingest.py --file requirements.txt

    # Plan only (show what would be created, no writes)
    python tools/reqingest.py --input "..." --plan

    # Dry-run (show file operations, no actual writes)
    python tools/reqingest.py --input "..." --dry-run

Environment variables:
    REQINGEST_LLM_PROVIDER  — 'openai' (default) or 'anthropic'
    REQINGEST_LLM_BASE_URL  — API base URL (default: https://api.openai.com/v1)
    REQINGEST_LLM_API_KEY   — API key (required)
    REQINGEST_LLM_MODEL     — Model name (default: gpt-4o)
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import os
import re
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SPECS = REPO_ROOT / "specs"
DOCS = REPO_ROOT / "docs"
SCHEMAS = SPECS / "schemas"
REQ = SPECS / "requirements"
DOMAIN = SPECS / "domain"
DELTAS = SPECS / "deltas"
TRACE_LINKS = REQ / "trace-links.yaml"

VALIDATE_SCRIPT = SCRIPT_DIR / "spec-ci" / "validate.py"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LLM_PROVIDER = os.environ.get("REQINGEST_LLM_PROVIDER", "openai")
LLM_BASE_URL = os.environ.get("REQINGEST_LLM_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.environ.get("REQINGEST_LLM_API_KEY", "")
LLM_MODEL = os.environ.get("REQINGEST_LLM_MODEL", "gpt-4o")

MAX_VALIDATE_RETRIES = 3

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ArtifactSpec:
    """A single specification artifact to be written."""
    kind: str           # BV, CAP, BR, NFR, CMD, EVT
    artifact_id: str    # e.g. BV-0004, CMD-0007
    data: Dict[str, Any]
    file_path: Optional[Path] = None  # computed during PLACE


@dataclass
class TraceLink:
    """A traceability link between two artifacts."""
    from_id: str
    to_id: str
    link_type: str
    rationale: str


@dataclass
class IngestionPlan:
    """Full output of the CLASSIFY + DECOMPOSE stages."""
    artifacts: List[ArtifactSpec] = field(default_factory=list)
    trace_links: List[TraceLink] = field(default_factory=list)
    delta_title: str = ""
    delta_rationale: str = ""
    raw_input: str = ""


@dataclass
class SSOTState:
    """Current state of the spec repository."""
    bv_ids: Set[str] = field(default_factory=set)
    cap_ids: Set[str] = field(default_factory=set)
    br_ids: Set[str] = field(default_factory=set)
    nfr_ids: Set[str] = field(default_factory=set)
    cmd_ids: Set[str] = field(default_factory=set)
    evt_ids: Set[str] = field(default_factory=set)
    dom_ids: Set[str] = field(default_factory=set)
    existing_traces: List[Dict[str, str]] = field(default_factory=list)
    domains_summary: str = ""


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _info(msg: str) -> None:
    print(f"  [INFO] {msg}")


def _warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def _error(msg: str) -> None:
    print(f"  [ERROR] {msg}", file=sys.stderr)


def _next_id(prefix: str, existing: Set[str]) -> str:
    """Compute the next sequential ID for a given prefix."""
    max_num = 0
    pat = re.compile(rf"^{prefix}-(\d{{4}})$")
    for eid in existing:
        m = pat.match(eid)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"{prefix}-{max_num + 1:04d}"


def _extract_md_ids(path: Path, prefix: str) -> Set[str]:
    """Extract CMD-#### or EVT-#### IDs from markdown anchor tags."""
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    return set(re.findall(rf'id="({prefix}-\d{{4}})"', text))


# ---------------------------------------------------------------------------
# SSOT State Reader
# ---------------------------------------------------------------------------

def read_ssot_state() -> SSOTState:
    """Read the current state of all specification artifacts."""
    state = SSOTState()

    # Requirement IDs
    for folder, attr, prefix in [
        (REQ / "business-values", "bv_ids", "BV"),
        (REQ / "capabilities", "cap_ids", "CAP"),
        (REQ / "business-rules", "br_ids", "BR"),
        (REQ / "nfr", "nfr_ids", "NFR"),
    ]:
        if folder.exists():
            for p in folder.glob("*.yaml"):
                doc = _load_yaml(p) or {}
                if isinstance(doc, dict) and "id" in doc:
                    getattr(state, attr).add(doc["id"])

    # CMD / EVT IDs from markdown
    commands_md = DOMAIN / "commands.md"
    events_md = DOMAIN / "events.md"
    state.cmd_ids = _extract_md_ids(commands_md, "CMD")
    state.evt_ids = _extract_md_ids(events_md, "EVT")

    # Domain IDs (skip templates)
    dom_dir = SPECS / "architecture" / "domain"
    if dom_dir.exists():
        for p in dom_dir.glob("DOM-*.yaml"):
            if p.name.endswith("-template.yaml"):
                continue
            doc = _load_yaml(p) or {}
            if isinstance(doc, dict) and "id" in doc:
                state.dom_ids.add(doc["id"])

    # Existing trace links
    if TRACE_LINKS.exists():
        doc = _load_yaml(TRACE_LINKS) or {}
        state.existing_traces = doc.get("links", []) if isinstance(doc, dict) else []

    # Domains summary (for LLM context)
    dom_summaries = []
    if dom_dir.exists():
        for p in sorted(dom_dir.glob("DOM-*.yaml")):
            doc = _load_yaml(p) or {}
            if isinstance(doc, dict):
                dom_summaries.append(
                    f"  - {doc.get('id', '?')}: {doc.get('name', '?')} — {doc.get('description', '')[:100]}"
                )
    state.domains_summary = "\n".join(dom_summaries) if dom_summaries else "  (none)"

    return state


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------

def build_system_prompt(state: SSOTState) -> str:
    """Construct the system prompt for the LLM from constitutions + schemas + state."""

    # Load schemas
    schemas = {}
    for name in ["bv", "cap", "br", "nfr", "delta", "trace-links"]:
        schema_path = SCHEMAS / f"{name}.schema.json"
        if schema_path.exists():
            schemas[name] = json.dumps(_load_json(schema_path), indent=2)

    # Next available IDs
    next_ids = {
        "BV": _next_id("BV", state.bv_ids),
        "CAP": _next_id("CAP", state.cap_ids),
        "BR": _next_id("BR", state.br_ids),
        "NFR": _next_id("NFR", state.nfr_ids),
        "CMD": _next_id("CMD", state.cmd_ids),
        "EVT": _next_id("EVT", state.evt_ids),
    }

    # Existing IDs summary
    existing_summary = []
    for label, ids in [
        ("Business Values", state.bv_ids),
        ("Capabilities", state.cap_ids),
        ("Business Rules", state.br_ids),
        ("NFRs", state.nfr_ids),
        ("Commands", state.cmd_ids),
        ("Events", state.evt_ids),
        ("Domains", state.dom_ids),
    ]:
        if ids:
            existing_summary.append(f"  {label}: {', '.join(sorted(ids))}")

    return textwrap.dedent(f"""\
    You are a requirements engineer for the Sonora platform specification repository.
    Your task is to decompose user requirements into SSOT-compliant specification artifacts.

    ## Governance Rules

    - Every governed artifact (BV, CAP, BR, NFR) MUST conform to its JSON schema.
    - Every CAP MUST be linked to at least one BV via a "realizes" trace link.
    - Every BR MUST be linked to at least one CAP via a "satisfies" trace link.
    - New artifacts MUST use status "proposed".
    - Commands (CMD) and Events (EVT) are defined in markdown files with anchor IDs.
    - Each CMD SHOULD emit a corresponding EVT.
    - Trace link types: realizes, satisfies, traces_to, implements, verifies.

    ## Existing IDs in the Repository

    {chr(10).join(existing_summary)}

    ## Next Available IDs

    {json.dumps(next_ids, indent=2)}

    ## Registered Domains

    {state.domains_summary}

    ## JSON Schemas

    ### BV (Business Value)
    ```json
    {schemas.get('bv', '{}')}
    ```

    ### CAP (Capability)
    ```json
    {schemas.get('cap', '{}')}
    ```

    ### BR (Business Rule)
    ```json
    {schemas.get('br', '{}')}
    ```

    ### NFR (Non-Functional Requirement)
    ```json
    {schemas.get('nfr', '{}')}
    ```

    ## Output Format

    Respond with a single JSON object (no markdown fences) with this structure:
    ```
    {{
      "artifacts": [
        {{
          "kind": "BV" | "CAP" | "BR" | "NFR" | "CMD" | "EVT",
          "data": {{ ... fields matching the schema for this kind ... }}
        }}
      ],
      "trace_links": [
        {{
          "from": "<source_id>",
          "to": "<target_id>",
          "type": "realizes" | "satisfies" | "verifies" | "traces_to" | "implements",
          "rationale": "<why this link exists>"
        }}
      ],
      "delta_title": "<concise title for the delta>",
      "delta_rationale": "<why these changes are needed>"
    }}
    ```

    ### For CMD artifacts, use this structure in "data":
    ```
    {{
      "id": "CMD-XXXX",
      "name": "<Command Name>",
      "intent": "<what this command does>",
      "domain": "<Domain Name> (<DOM-XXXX>)",
      "aggregate": "<Aggregate Root>",
      "payload": [
        {{ "name": "<field>", "type": "<type>", "required": true/false, "description": "<desc>" }}
      ],
      "invariants": "<business rules / preconditions>",
      "emits": "EVT-XXXX (<Event Name>)",
      "error_codes": ["<ERROR.CODE.1>", "<ERROR.CODE.2>"]
    }}
    ```

    ### For EVT artifacts, use this structure in "data":
    ```
    {{
      "id": "EVT-XXXX",
      "name": "<Event Name>",
      "fact": "<what happened>",
      "domain": "<Domain Name> (<DOM-XXXX>)",
      "aggregate": "<Aggregate Root>",
      "triggered_by": "CMD-XXXX (<Command Name>)",
      "payload": [
        {{ "name": "<field>", "type": "<type>", "description": "<desc>" }}
      ],
      "consumers": "<who consumes this event>"
    }}
    ```

    ## Rules for Decomposition

    1. One requirement may produce multiple artifacts (e.g., a BV + CAP + BR + CMD + EVT).
    2. DO NOT duplicate existing artifacts. If a requirement extends an existing capability, reference it.
    3. Use the next available IDs sequentially — if you create 2 BVs, use {next_ids['BV']} and the one after.
    4. Every new CAP MUST have at least one acceptance_criteria entry.
    5. Every new BR MUST have a statement and at least one acceptance_criteria entry.
    6. For NFRs: category, statement, metric, target, and scope are required.
    7. CMD/EVT artifacts SHOULD be assigned to an existing domain. If no domain fits, note it.
    8. Trace links MUST connect new artifacts into the existing graph.
    9. The delta_title should be descriptive and concise.
    """)


def build_user_prompt(requirement_text: str) -> str:
    """Build the user message for the LLM."""
    return textwrap.dedent(f"""\
    Decompose the following requirement(s) into SSOT-compliant specification artifacts.
    Create all necessary BV, CAP, BR, NFR, CMD, and EVT artifacts with proper IDs,
    trace links, and a delta summary.

    REQUIREMENT:
    {requirement_text}
    """)


def build_repair_prompt(validation_errors: str, plan: IngestionPlan) -> str:
    """Build a repair prompt when validation fails."""
    artifacts_summary = json.dumps(
        [{"kind": a.kind, "id": a.artifact_id, "data": a.data} for a in plan.artifacts],
        indent=2,
    )
    return textwrap.dedent(f"""\
    The previous artifact placement failed validation. Fix the issues and return
    a corrected JSON response in the same output format.

    VALIDATION ERRORS:
    {validation_errors}

    PREVIOUSLY GENERATED ARTIFACTS:
    {artifacts_summary}

    PREVIOUSLY GENERATED TRACE LINKS:
    {json.dumps([vars(tl) for tl in plan.trace_links], indent=2)}

    Fix only the fields that caused validation errors. Keep IDs the same unless
    the ID format itself is wrong.
    """)


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------

def _call_openai(system: str, user: str) -> str:
    """Call an OpenAI-compatible chat completions API."""
    url = f"{LLM_BASE_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        _error(f"LLM API error {e.code}: {error_body[:500]}")
        raise SystemExit(1)


def _call_anthropic(system: str, user: str) -> str:
    """Call the Anthropic Messages API."""
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": LLM_MODEL,
        "max_tokens": 8192,
        "system": system,
        "messages": [
            {"role": "user", "content": user},
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": LLM_API_KEY,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["content"][0]["text"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        _error(f"Anthropic API error {e.code}: {error_body[:500]}")
        raise SystemExit(1)


def call_llm(system: str, user: str) -> str:
    """Dispatch to the configured LLM provider."""
    if not LLM_API_KEY:
        _error(
            "REQINGEST_LLM_API_KEY is not set.\n"
            "  export REQINGEST_LLM_API_KEY=sk-...\n"
            "  Optional: REQINGEST_LLM_PROVIDER=openai|anthropic\n"
            "  Optional: REQINGEST_LLM_BASE_URL=https://api.openai.com/v1\n"
            "  Optional: REQINGEST_LLM_MODEL=gpt-4o"
        )
        raise SystemExit(1)

    if LLM_PROVIDER == "anthropic":
        return _call_anthropic(system, user)
    else:
        return _call_openai(system, user)


# ---------------------------------------------------------------------------
# Response Parser
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> Dict[str, Any]:
    """Extract JSON from LLM response, handling optional markdown fences."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        first_nl = text.index("\n")
        last_fence = text.rfind("```")
        if last_fence > first_nl:
            text = text[first_nl + 1:last_fence].strip()
    return json.loads(text)


def parse_llm_response(response_text: str, state: SSOTState) -> IngestionPlan:
    """Parse the LLM JSON response into an IngestionPlan."""
    data = _extract_json(response_text)
    plan = IngestionPlan()

    for art in data.get("artifacts", []):
        kind = art.get("kind", "").upper()
        art_data = art.get("data", {})

        # Determine artifact ID
        if kind in ("BV", "CAP", "BR", "NFR"):
            artifact_id = art_data.get("id", "")
        elif kind in ("CMD", "EVT"):
            artifact_id = art_data.get("id", "")
        else:
            _warn(f"Unknown artifact kind '{kind}', skipping")
            continue

        plan.artifacts.append(ArtifactSpec(
            kind=kind,
            artifact_id=artifact_id,
            data=art_data,
        ))

    for tl in data.get("trace_links", []):
        plan.trace_links.append(TraceLink(
            from_id=tl.get("from", ""),
            to_id=tl.get("to", ""),
            link_type=tl.get("type", ""),
            rationale=tl.get("rationale", ""),
        ))

    plan.delta_title = data.get("delta_title", "Requirements ingestion")
    plan.delta_rationale = data.get("delta_rationale", "")

    return plan


# ---------------------------------------------------------------------------
# Stage 1 + 2: CLASSIFY + DECOMPOSE (LLM-driven)
# ---------------------------------------------------------------------------

def classify_and_decompose(requirement_text: str, state: SSOTState) -> IngestionPlan:
    """Send requirement to LLM for classification and decomposition."""
    print("\n[1/5] CLASSIFY + DECOMPOSE")
    _info("Building prompt from SSOT state...")

    system_prompt = build_system_prompt(state)
    user_prompt = build_user_prompt(requirement_text)

    _info(f"Calling LLM ({LLM_PROVIDER}/{LLM_MODEL})...")
    response = call_llm(system_prompt, user_prompt)

    _info("Parsing response...")
    plan = parse_llm_response(response, state)
    plan.raw_input = requirement_text

    _info(f"Decomposed into {len(plan.artifacts)} artifacts and {len(plan.trace_links)} trace links.")
    for art in plan.artifacts:
        _info(f"  {art.kind} {art.artifact_id}: {art.data.get('title', art.data.get('name', '?'))}")

    return plan


# ---------------------------------------------------------------------------
# Stage 3: PLACE — write artifacts to SSOT locations
# ---------------------------------------------------------------------------

def _place_yaml_artifact(art: ArtifactSpec, folder: Path, dry_run: bool) -> None:
    """Write a BV/CAP/BR/NFR artifact as a YAML file."""
    art.file_path = folder / f"{art.artifact_id}.yaml"
    if dry_run:
        _info(f"  [DRY-RUN] Would create: {art.file_path.relative_to(REPO_ROOT)}")
        return
    _write_yaml(art.file_path, art.data)
    _info(f"  Created: {art.file_path.relative_to(REPO_ROOT)}")


def _format_cmd_markdown(data: Dict[str, Any]) -> str:
    """Format a CMD artifact as markdown section."""
    lines = [
        f'<a id="{data["id"]}"></a>',
        f'### {data["id"]}: {data.get("name", "Unnamed Command")}',
        "",
        f'- **Intent**: {data.get("intent", "N/A")}',
        f'- **Domain**: {data.get("domain", "N/A")}',
        f'- **Aggregate**: {data.get("aggregate", "N/A")}',
        "- **Payload**:",
    ]
    for p in data.get("payload", []):
        req_marker = "required" if p.get("required", False) else "optional"
        lines.append(f'  - `{p["name"]}` ({p.get("type", "string")}, {req_marker}) — {p.get("description", "")}')
    lines.append(f'- **Invariants**: {data.get("invariants", "N/A")}')
    lines.append(f'- **Emits**: {data.get("emits", "N/A")}')
    error_codes = data.get("error_codes", [])
    if error_codes:
        lines.append(f'- **Error codes**: {", ".join(f"`{e}`" for e in error_codes)}')
    lines.append("")
    return "\n".join(lines)


def _format_evt_markdown(data: Dict[str, Any]) -> str:
    """Format an EVT artifact as markdown section."""
    lines = [
        f'<a id="{data["id"]}"></a>',
        f'### {data["id"]}: {data.get("name", "Unnamed Event")}',
        "",
        f'- **Fact**: {data.get("fact", "N/A")}',
        f'- **Domain**: {data.get("domain", "N/A")}',
        f'- **Aggregate**: {data.get("aggregate", "N/A")}',
        f'- **Triggered by**: {data.get("triggered_by", "N/A")}',
        "- **Payload**:",
    ]
    for p in data.get("payload", []):
        lines.append(f'  - `{p["name"]}` ({p.get("type", "string")}) — {p.get("description", "")}')
    lines.append(f'- **Consumers**: {data.get("consumers", "N/A")}')
    lines.append("")
    return "\n".join(lines)


def _append_to_markdown(path: Path, section: str, dry_run: bool) -> None:
    """Append a section to a markdown file."""
    if dry_run:
        _info(f"  [DRY-RUN] Would append to: {path.relative_to(REPO_ROOT)}")
        return
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if not existing.endswith("\n"):
        existing += "\n"
    _write_text(path, existing + section)
    _info(f"  Appended to: {path.relative_to(REPO_ROOT)}")


def _update_trace_links(new_links: List[TraceLink], dry_run: bool) -> None:
    """Append new trace links to trace-links.yaml."""
    if not new_links:
        return

    if dry_run:
        _info(f"  [DRY-RUN] Would add {len(new_links)} trace links to trace-links.yaml")
        return

    doc = {"links": []}
    if TRACE_LINKS.exists():
        doc = _load_yaml(TRACE_LINKS) or {"links": []}

    for tl in new_links:
        entry: Dict[str, str] = {
            "from": tl.from_id,
            "to": tl.to_id,
            "type": tl.link_type,
        }
        if tl.rationale:
            entry["rationale"] = tl.rationale
        doc["links"].append(entry)

    _write_yaml(TRACE_LINKS, doc)
    _info(f"  Updated trace-links.yaml with {len(new_links)} new links")


def place_artifacts(plan: IngestionPlan, dry_run: bool = False) -> None:
    """Write all artifacts to their SSOT locations."""
    print("\n[3/5] PLACE")

    folder_map = {
        "BV": REQ / "business-values",
        "CAP": REQ / "capabilities",
        "BR": REQ / "business-rules",
        "NFR": REQ / "nfr",
    }

    for art in plan.artifacts:
        if art.kind in folder_map:
            _place_yaml_artifact(art, folder_map[art.kind], dry_run)
        elif art.kind == "CMD":
            section = _format_cmd_markdown(art.data)
            _append_to_markdown(DOMAIN / "commands.md", section, dry_run)
            art.file_path = DOMAIN / "commands.md"
        elif art.kind == "EVT":
            section = _format_evt_markdown(art.data)
            _append_to_markdown(DOMAIN / "events.md", section, dry_run)
            art.file_path = DOMAIN / "events.md"

    _update_trace_links(plan.trace_links, dry_run)


# ---------------------------------------------------------------------------
# Stage 4: DELTA — generate delta file
# ---------------------------------------------------------------------------

def generate_delta(plan: IngestionPlan, dry_run: bool = False) -> Optional[Path]:
    """Generate a delta file recording all changes."""
    print("\n[4/5] DELTA")

    # Only governed artifacts go into delta changes (BV, CAP, BR, NFR)
    governed_kinds = {"BV", "CAP", "BR", "NFR"}
    changes = []
    for art in plan.artifacts:
        if art.kind in governed_kinds:
            changes.append({
                "type": "add",
                "target": art.artifact_id,
                "description": art.data.get("title", art.data.get("name", "")),
            })

    if not changes:
        _info("No governed artifacts (BV/CAP/BR/NFR) created — skipping delta.")
        return None

    # Compute next delta sequence number for today
    today = datetime.date.today()
    date_str = today.strftime("%Y-%m-%d")
    existing_deltas = sorted(DELTAS.glob(f"*.yaml")) if DELTAS.exists() else []
    seq = 1
    delta_id_pat = re.compile(rf"^DELTA-{date_str}-(\d{{3}})$")
    for dp in existing_deltas:
        doc = _load_yaml(dp) or {}
        did = doc.get("id", "")
        m = delta_id_pat.match(did)
        if m:
            seq = max(seq, int(m.group(1)) + 1)

    delta_id = f"DELTA-{date_str}-{seq:03d}"
    delta_data = {
        "id": delta_id,
        "title": plan.delta_title or "Requirements ingestion",
        "status": "proposed",
        "changes": changes,
        "compatibility": {
            "claim": "non-breaking",
            "rationale": plan.delta_rationale or "New artifacts added via requirements ingestion pipeline.",
        },
    }

    # Filename: date + slugified title
    slug = re.sub(r"[^a-z0-9]+", "-", plan.delta_title.lower().strip())[:40].strip("-")
    delta_filename = f"{date_str}-{slug}.yaml" if slug else f"{date_str}-reqingest.yaml"
    delta_path = DELTAS / delta_filename

    if dry_run:
        _info(f"  [DRY-RUN] Would create delta: {delta_path.relative_to(REPO_ROOT)}")
        _info(f"  Delta ID: {delta_id}")
        _info(f"  Changes: {len(changes)} governed artifacts")
        return delta_path

    _write_yaml(delta_path, delta_data)
    _info(f"  Created: {delta_path.relative_to(REPO_ROOT)}")
    _info(f"  Delta ID: {delta_id}, {len(changes)} changes")
    return delta_path


# ---------------------------------------------------------------------------
# Stage 5: VALIDATE — run validate.py as gate
# ---------------------------------------------------------------------------

def run_validation(dry_run: bool = False) -> Tuple[bool, str]:
    """Run validate.py and return (success, output)."""
    if dry_run:
        _info("  [DRY-RUN] Would run validate.py")
        return True, ""

    if not VALIDATE_SCRIPT.exists():
        _warn(f"Validator not found at {VALIDATE_SCRIPT.relative_to(REPO_ROOT)}, skipping.")
        return True, ""

    try:
        result = subprocess.run(
            [sys.executable, str(VALIDATE_SCRIPT)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=60,
        )
        output = result.stdout + result.stderr
        if result.returncode == 0:
            return True, output
        return False, output
    except subprocess.TimeoutExpired:
        return False, "Validation timed out after 60 seconds."


def validate_with_retry(
    plan: IngestionPlan,
    state: SSOTState,
    dry_run: bool = False,
) -> bool:
    """Run validation, retry with LLM repair on failure (max 3 attempts)."""
    print("\n[5/5] VALIDATE")

    for attempt in range(1, MAX_VALIDATE_RETRIES + 1):
        _info(f"Validation attempt {attempt}/{MAX_VALIDATE_RETRIES}...")
        success, output = run_validation(dry_run)

        if success:
            _info("Validation PASSED.")
            return True

        _warn(f"Validation FAILED:\n{output}")

        if attempt >= MAX_VALIDATE_RETRIES:
            _error("Max retries reached. Manual intervention required.")
            return False

        _info("Attempting LLM-assisted repair...")
        system_prompt = build_system_prompt(state)
        repair_prompt = build_repair_prompt(output, plan)

        try:
            response = call_llm(system_prompt, repair_prompt)
            repaired_plan = parse_llm_response(response, state)

            # Re-place the repaired artifacts
            _info("Placing repaired artifacts...")
            _rollback_artifacts(plan)
            plan.artifacts = repaired_plan.artifacts
            plan.trace_links = repaired_plan.trace_links
            place_artifacts(plan, dry_run=dry_run)
        except Exception as e:
            _error(f"Repair failed: {e}")

    return False


def _rollback_artifacts(plan: IngestionPlan) -> None:
    """Remove YAML artifacts that were created during PLACE (for retry)."""
    for art in plan.artifacts:
        if art.file_path and art.kind in ("BV", "CAP", "BR", "NFR"):
            if art.file_path.exists():
                art.file_path.unlink()
                _info(f"  Rolled back: {art.file_path.relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# Input Readers
# ---------------------------------------------------------------------------

def read_input_text(args: argparse.Namespace) -> str:
    """Read requirement text from --input or --file."""
    if args.input:
        return args.input

    if args.file:
        path = Path(args.file)
        if not path.exists():
            _error(f"Input file not found: {args.file}")
            raise SystemExit(1)

        text = path.read_text(encoding="utf-8")

        # If YAML, extract requirements list
        if path.suffix in (".yaml", ".yml"):
            doc = yaml.safe_load(text)
            if isinstance(doc, dict) and "requirements" in doc:
                items = doc["requirements"]
                if isinstance(items, list):
                    return "\n\n".join(
                        f"- {item}" if isinstance(item, str) else yaml.dump(item, default_flow_style=False)
                        for item in items
                    )
            elif isinstance(doc, list):
                return "\n\n".join(str(item) for item in doc)

        return text

    _error("Either --input or --file is required.")
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# Display Plan
# ---------------------------------------------------------------------------

def display_plan(plan: IngestionPlan) -> None:
    """Print a summary of the ingestion plan."""
    print("\n" + "=" * 70)
    print("INGESTION PLAN SUMMARY")
    print("=" * 70)

    print(f"\nInput: {plan.raw_input[:200]}{'...' if len(plan.raw_input) > 200 else ''}")
    print(f"\nDelta: {plan.delta_title}")
    if plan.delta_rationale:
        print(f"Rationale: {plan.delta_rationale}")

    print(f"\nArtifacts ({len(plan.artifacts)}):")
    for art in plan.artifacts:
        title = art.data.get("title", art.data.get("name", "?"))
        print(f"  {art.kind:4s} {art.artifact_id:10s}  {title}")

    print(f"\nTrace Links ({len(plan.trace_links)}):")
    for tl in plan.trace_links:
        print(f"  {tl.from_id} --[{tl.link_type}]--> {tl.to_id}")
        if tl.rationale:
            print(f"    {tl.rationale}")

    governed = sum(1 for a in plan.artifacts if a.kind in ("BV", "CAP", "BR", "NFR"))
    cmd_evt = sum(1 for a in plan.artifacts if a.kind in ("CMD", "EVT"))
    print(f"\nGoverned artifacts: {governed} (delta-tracked)")
    print(f"Domain artifacts: {cmd_evt} (CMD/EVT in markdown)")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Requirements Ingestion Pipeline — decompose requirements into SSOT artifacts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Environment variables:
              REQINGEST_LLM_PROVIDER   'openai' (default) or 'anthropic'
              REQINGEST_LLM_BASE_URL   API base URL (default: https://api.openai.com/v1)
              REQINGEST_LLM_API_KEY    API key (required)
              REQINGEST_LLM_MODEL      Model name (default: gpt-4o)

            Examples:
              python tools/reqingest.py --input "Users should reset passwords via email"
              python tools/reqingest.py --file requirements.txt --dry-run
              python tools/reqingest.py --file batch.yaml --plan
        """),
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--input", "-i",
        help="Single requirement text (natural language).",
    )
    input_group.add_argument(
        "--file", "-f",
        help="Path to input file (.txt = one requirement per line; .yaml = structured list).",
    )

    parser.add_argument(
        "--plan",
        action="store_true",
        help="Show the ingestion plan (LLM decomposition) without writing any files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what files would be created/modified, but do not write them.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip the validate.py gate (not recommended).",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("  Sonora — Requirements Ingestion Pipeline")
    print("=" * 70)

    # Read the current SSOT state
    _info("Reading SSOT state...")
    state = read_ssot_state()
    _info(
        f"Found: {len(state.bv_ids)} BV, {len(state.cap_ids)} CAP, "
        f"{len(state.br_ids)} BR, {len(state.nfr_ids)} NFR, "
        f"{len(state.cmd_ids)} CMD, {len(state.evt_ids)} EVT, "
        f"{len(state.dom_ids)} DOM"
    )

    # Read input
    requirement_text = read_input_text(args)
    _info(f"Input: {requirement_text[:120]}{'...' if len(requirement_text) > 120 else ''}")

    # Stage 1+2: CLASSIFY + DECOMPOSE (LLM)
    plan = classify_and_decompose(requirement_text, state)

    # If --plan, display and exit
    if args.plan:
        display_plan(plan)
        print("\n[--plan mode] No files written.")
        return

    display_plan(plan)

    # Stage 3: PLACE
    place_artifacts(plan, dry_run=args.dry_run)

    # Stage 4: DELTA
    generate_delta(plan, dry_run=args.dry_run)

    # Stage 5: VALIDATE
    if args.skip_validation:
        _info("Skipping validation (--skip-validation).")
    else:
        success = validate_with_retry(plan, state, dry_run=args.dry_run)
        if not success and not args.dry_run:
            _error("Pipeline completed with validation errors. Review the output above.")
            raise SystemExit(1)

    print("\n" + "=" * 70)
    if args.dry_run:
        print("  [DRY-RUN] Pipeline completed. No files were written.")
    else:
        print("  Pipeline completed successfully.")
        print(f"  {len(plan.artifacts)} artifacts written, {len(plan.trace_links)} trace links added.")
    print("=" * 70)


if __name__ == "__main__":
    main()
