#!/usr/bin/env python3
"""
Task Generation Pipeline — taskgen.py

Reads applied (or proposed) deltas and generates implementation task
specifications for LLM coding agents.

Pipeline stages:
  1. IMPACT    — resolve delta targets to full spec artifacts, gather context
  2. DECOMPOSE — LLM breaks impacts into atomic implementation tasks
  3. SPECIFY   — LLM generates a task spec per unit (contract, criteria, files)
  4. ORDER     — topologically sort tasks by dependency

Usage:
    # From a specific delta file
    python tools/taskgen.py --delta specs/deltas/2026-02-11-auth-domain-model.yaml

    # From all proposed/applied deltas
    python tools/taskgen.py --all-pending

    # Output as YAML task list
    python tools/taskgen.py --delta ... --format yaml

    # Output as individual markdown task files
    python tools/taskgen.py --delta ... --format files --out-dir tasks/

    # Plan mode (show impact analysis, no LLM call)
    python tools/taskgen.py --delta ... --plan

Environment variables:
    TASKGEN_LLM_PROVIDER  — 'openai' (default) or 'anthropic'
    TASKGEN_LLM_BASE_URL  — API base URL (default: https://api.openai.com/v1)
    TASKGEN_LLM_API_KEY   — API key (required)
    TASKGEN_LLM_MODEL     — Model name (default: gpt-4o)
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
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
REQ = SPECS / "requirements"
DOMAIN = SPECS / "domain"
DELTAS = SPECS / "deltas"
ARCH = SPECS / "architecture"
MIDDLEWARE = ARCH / "middleware"
DOM_DIR = ARCH / "domain"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LLM_PROVIDER = os.environ.get("TASKGEN_LLM_PROVIDER", "openai")
LLM_BASE_URL = os.environ.get("TASKGEN_LLM_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.environ.get("TASKGEN_LLM_API_KEY", "")
LLM_MODEL = os.environ.get("TASKGEN_LLM_MODEL", "gpt-4o")

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class DeltaChange:
    """A single change entry from a delta file."""
    change_type: str   # add, amend, deprecate, supersede
    target: str        # BV-0004, CAP-0002, etc.
    description: str


@dataclass
class DeltaInfo:
    """Parsed delta file."""
    delta_id: str
    title: str
    status: str
    changes: List[DeltaChange] = field(default_factory=list)
    file_path: Optional[Path] = None


@dataclass
class ResolvedArtifact:
    """A spec artifact loaded and resolved from its target ID."""
    artifact_id: str
    kind: str           # BV, CAP, BR, NFR
    data: Dict[str, Any]
    file_path: Path
    related_cmds: List[str] = field(default_factory=list)
    related_evts: List[str] = field(default_factory=list)


@dataclass
class ImpactEntry:
    """A single impact resulting from delta analysis."""
    change: DeltaChange
    artifact: Optional[ResolvedArtifact]
    domain: Optional[str]
    cmd_specs: List[Dict[str, Any]] = field(default_factory=list)
    evt_specs: List[Dict[str, Any]] = field(default_factory=list)
    br_specs: List[Dict[str, Any]] = field(default_factory=list)
    middleware_context: List[str] = field(default_factory=list)


@dataclass
class Task:
    """A single implementation task."""
    task_id: str
    title: str
    layer: str          # domain-core, application, adapter-in, adapter-out, middleware, test
    domain: str
    description: str
    acceptance_criteria: List[str] = field(default_factory=list)
    source_artifacts: List[str] = field(default_factory=list)
    target_files: List[str] = field(default_factory=list)
    contracts: List[str] = field(default_factory=list)
    error_codes: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    priority: str = "medium"
    quality_gates: List[str] = field(default_factory=list)


@dataclass
class TaskPlan:
    """Full output of the task generation pipeline."""
    delta: DeltaInfo
    impacts: List[ImpactEntry] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)
    generation_date: str = ""


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False, width=120)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _info(msg: str) -> None:
    print(f"  [INFO] {msg}")


def _warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def _error(msg: str) -> None:
    print(f"  [ERROR] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Delta Loader
# ---------------------------------------------------------------------------

def load_delta(path: Path) -> DeltaInfo:
    """Parse a delta YAML file."""
    doc = _load_yaml(path) or {}
    delta = DeltaInfo(
        delta_id=doc.get("id", ""),
        title=doc.get("title", ""),
        status=doc.get("status", ""),
        file_path=path,
    )
    for ch in doc.get("changes", []):
        if isinstance(ch, dict):
            delta.changes.append(DeltaChange(
                change_type=ch.get("type", ""),
                target=ch.get("target", ""),
                description=ch.get("description", ""),
            ))
    return delta


def find_pending_deltas() -> List[Path]:
    """Find all deltas with status proposed or applied."""
    if not DELTAS.exists():
        return []
    results = []
    for p in sorted(DELTAS.glob("*.yaml")):
        doc = _load_yaml(p) or {}
        if doc.get("status") in ("proposed", "applied"):
            results.append(p)
    return results


# ---------------------------------------------------------------------------
# Artifact Resolver
# ---------------------------------------------------------------------------

def _resolve_requirement(target_id: str) -> Optional[ResolvedArtifact]:
    """Load a requirement artifact (BV/CAP/BR/NFR) by ID."""
    prefix = target_id.split("-")[0] if "-" in target_id else ""
    folder_map = {
        "BV": REQ / "business-values",
        "CAP": REQ / "capabilities",
        "BR": REQ / "business-rules",
        "NFR": REQ / "nfr",
    }
    folder = folder_map.get(prefix)
    if not folder:
        return None

    path = folder / f"{target_id}.yaml"
    if not path.exists():
        return None

    doc = _load_yaml(path) or {}
    artifact = ResolvedArtifact(
        artifact_id=target_id,
        kind=prefix,
        data=doc,
        file_path=path,
    )

    # Extract CMD/EVT traces from capability artifacts
    if prefix == "CAP":
        trace = doc.get("trace", {})
        domain_trace = trace.get("domain", {}) if isinstance(trace, dict) else {}
        cmds = domain_trace.get("commands", [])
        evts = domain_trace.get("events", [])
        for link in cmds:
            m = re.search(r"(CMD-\d{4})", link)
            if m:
                artifact.related_cmds.append(m.group(1))
        for link in evts:
            m = re.search(r"(EVT-\d{4})", link)
            if m:
                artifact.related_evts.append(m.group(1))

    return artifact


def _parse_domain_section(path: Path, section_id: str, prefix: str) -> Dict[str, Any]:
    """Extract a CMD/EVT section from a markdown file."""
    if not path.exists():
        return {"id": section_id}

    text = path.read_text(encoding="utf-8")
    anchor = f'id="{section_id}"'
    idx = text.find(anchor)
    if idx == -1:
        return {"id": section_id}

    next_pattern = re.compile(rf'<a id="{prefix}-\d{{4}}"')
    rest = text[idx + len(anchor):]
    m = next_pattern.search(rest)
    section = rest[:m.start()] if m else rest

    result: Dict[str, Any] = {"id": section_id, "raw": section.strip()}

    for key, pattern in [
        ("name", rf"### {section_id}: (.+)"),
        ("intent", r"\*\*Intent\*\*:\s*(.+)"),
        ("fact", r"\*\*Fact\*\*:\s*(.+)"),
        ("domain", r"\*\*Domain\*\*:\s*(.+)"),
        ("aggregate", r"\*\*Aggregate\*\*:\s*(.+)"),
        ("invariants", r"\*\*Invariants\*\*:\s*(.+)"),
        ("emits", r"\*\*Emits\*\*:\s*(.+)"),
        ("triggered_by", r"\*\*Triggered by\*\*:\s*(.+)"),
        ("consumers", r"\*\*Consumers\*\*:\s*(.+)"),
    ]:
        m_field = re.search(pattern, section)
        if m_field:
            result[key] = m_field.group(1).strip()

    m_errors = re.search(r"\*\*Error codes\*\*:\s*(.+)", section)
    if m_errors:
        result["error_codes"] = [
            code.strip().strip("`")
            for code in m_errors.group(1).split(",")
        ]

    payload_lines = re.findall(r"  - `(\w+)` \(([^)]+)\) — (.+)", section)
    if payload_lines:
        result["payload"] = [
            {"name": name, "type_info": tinfo, "description": desc}
            for name, tinfo, desc in payload_lines
        ]

    return result


def _parse_cmd_section(cmd_id: str) -> Dict[str, Any]:
    return _parse_domain_section(DOMAIN / "commands.md", cmd_id, "CMD")


def _parse_evt_section(evt_id: str) -> Dict[str, Any]:
    return _parse_domain_section(DOMAIN / "events.md", evt_id, "EVT")


def _find_domain_for_artifact(artifact: ResolvedArtifact) -> Optional[str]:
    """Determine which domain a CAP/BR is associated with."""
    if artifact.related_cmds:
        cmd = _parse_cmd_section(artifact.related_cmds[0])
        domain_str = cmd.get("domain", "")
        m = re.search(r"(DOM-\d{4})", domain_str)
        if m:
            return m.group(1)

    if artifact.kind == "BR":
        notes = artifact.data.get("notes", "")
        m = re.search(r"CMD-\d{4}", notes)
        if m:
            cmd = _parse_cmd_section(m.group())
            domain_str = cmd.get("domain", "")
            m2 = re.search(r"(DOM-\d{4})", domain_str)
            if m2:
                return m2.group(1)

    return None


def _load_domain_info(dom_id: str) -> Dict[str, Any]:
    path = DOM_DIR / f"{dom_id}.yaml"
    if path.exists():
        return _load_yaml(path) or {}
    return {}


def _collect_related_brs(cap_id: str) -> List[Dict[str, Any]]:
    """Find BRs linked to a capability via trace-links.yaml."""
    trace_path = REQ / "trace-links.yaml"
    if not trace_path.exists():
        return []

    doc = _load_yaml(trace_path) or {}
    links = doc.get("links", [])
    br_ids: Set[str] = set()
    for link in links:
        if link.get("from") == cap_id and link.get("type") == "satisfies":
            target = link.get("to", "")
            if target.startswith("BR-"):
                br_ids.add(target)

    results = []
    for br_id in sorted(br_ids):
        art = _resolve_requirement(br_id)
        if art:
            results.append(art.data)
    return results


def _get_middleware_context() -> List[Dict[str, str]]:
    """Load middleware registry summary."""
    if not MIDDLEWARE.exists():
        return []

    mw_list = []
    mw_id_re = re.compile(r"\*\*Middleware ID:\*\*\s*`(mw\.\w+)`")
    mw_pos_re = re.compile(r"\*\*Pipeline Position:\*\*\s*(\d+)")
    mw_cat_re = re.compile(r"\*\*Category:\*\*\s*(mandatory|optional)")

    for p in sorted(MIDDLEWARE.glob("*.md")):
        if p.name.lower() == "readme.md":
            continue
        text = p.read_text(encoding="utf-8")
        mid = mw_id_re.search(text)
        pos = mw_pos_re.search(text)
        cat = mw_cat_re.search(text)
        if mid:
            mw_list.append({
                "id": mid.group(1),
                "position": pos.group(1) if pos else "?",
                "category": cat.group(1) if cat else "?",
                "file": str(p.relative_to(REPO_ROOT)),
            })
    return mw_list


# ---------------------------------------------------------------------------
# Stage 1: IMPACT — resolve delta targets to full context
# ---------------------------------------------------------------------------

def analyze_impact(delta: DeltaInfo) -> List[ImpactEntry]:
    """Resolve each delta change to its full spec context."""
    impacts = []

    for ch in delta.changes:
        artifact = _resolve_requirement(ch.target)
        domain: Optional[str] = None
        cmd_specs: List[Dict[str, Any]] = []
        evt_specs: List[Dict[str, Any]] = []
        br_specs: List[Dict[str, Any]] = []
        mw_context: List[str] = []

        if artifact:
            domain = _find_domain_for_artifact(artifact)

            if artifact.kind == "CAP":
                for cmd_id in artifact.related_cmds:
                    cmd_specs.append(_parse_cmd_section(cmd_id))
                for evt_id in artifact.related_evts:
                    evt_specs.append(_parse_evt_section(evt_id))
                br_specs = _collect_related_brs(artifact.artifact_id)

            if artifact.kind == "CAP" and "JWT" in artifact.data.get("title", "").upper():
                mw_context.append("mw.auth")
            if artifact.kind == "NFR":
                statement = artifact.data.get("statement", "").lower()
                if "trace" in statement or "correlation" in statement:
                    mw_context.append("mw.trace")
                if "error" in statement or "problem" in statement:
                    mw_context.append("mw.error")

        impacts.append(ImpactEntry(
            change=ch,
            artifact=artifact,
            domain=domain,
            cmd_specs=cmd_specs,
            evt_specs=evt_specs,
            br_specs=br_specs,
            middleware_context=mw_context,
        ))

    return impacts


# ---------------------------------------------------------------------------
# Stage 2 + 3: DECOMPOSE + SPECIFY (LLM-driven)
# ---------------------------------------------------------------------------

def build_system_prompt(delta: DeltaInfo, impacts: List[ImpactEntry]) -> str:
    """Build the system prompt for task decomposition."""

    shell_spec = ""
    shell_path = ARCH / "backend-shell-app.md"
    if shell_path.exists():
        shell_spec = shell_path.read_text(encoding="utf-8")[:2000]

    mw_registry = _get_middleware_context()

    domain_ids: Set[str] = set()
    for imp in impacts:
        if imp.domain:
            domain_ids.add(imp.domain)

    domain_infos = {}
    for dom_id in domain_ids:
        domain_infos[dom_id] = _load_domain_info(dom_id)

    repo_yaml = REPO_ROOT / "repo.yaml"
    qg_ids: List[str] = []
    if repo_yaml.exists():
        repo_doc = _load_yaml(repo_yaml) or {}
        for qg in repo_doc.get("qualityGates", []):
            if isinstance(qg, dict) and "id" in qg:
                qg_ids.append(qg["id"])

    return textwrap.dedent(f"""\
    You are a software architect generating implementation tasks from a specification delta.
    Your output will be consumed by LLM coding agents that implement each task independently.

    ## Architecture Context

    ### Backend Shell App (summary)
    The backend uses a Shell composition model:
    - **Shell App**: host application composing domain containers + middleware pipeline.
    - **Domain core**: business logic, framework-agnostic. Domain cores MUST NOT depend on
      frameworks, persistence, messaging, or web libraries.
    - **Domain container**: integration layer (routes, handlers, wiring). Lives in adapter/infrastructure.
    - **Middleware**: cross-cutting pipeline stages (auth, trace, error, messaging, audit, cache).

    ### Hexagonal Architecture (ADR-0014)
    - **Domain layer**: aggregates, value objects, domain events, domain services, ports (interfaces).
    - **Application layer**: use cases / command handlers, DTOs, application services.
    - **Adapter layer (in)**: REST controllers, message consumers, CLI handlers.
    - **Adapter layer (out)**: persistence implementations, external service clients, event publishers.
    - **Infrastructure**: framework config, middleware, DI wiring.

    ### Middleware Pipeline
    {json.dumps(mw_registry, indent=2)}

    ### Registered Domains
    {json.dumps(domain_infos, indent=2, default=str)}

    ### Quality Gates
    {json.dumps(qg_ids, indent=2)}

    ## Task Generation Rules

    1. **One task = one unit of work** that can be implemented and tested independently.
    2. **Layer assignment** — each task targets exactly one architectural layer:
       - `domain-core` — aggregates, value objects, domain events, ports (interfaces)
       - `application` — use case / command handler implementations
       - `adapter-in` — REST controllers, message consumers
       - `adapter-out` — persistence, external clients, event publishers
       - `middleware` — middleware component changes
       - `test` — test implementations (unit, integration, contract)
    3. **Dependency ordering** — domain-core tasks come first, then application, then adapters/tests.
       Use `depends_on` to express task dependencies.
    4. **Acceptance criteria** — derived from BR acceptance_criteria and CAP acceptance_criteria.
       Each task MUST have at least one acceptance criterion.
    5. **Error codes** — list all error codes the task must handle.
    6. **Target files** — suggest file paths using hexagonal conventions:
       - `<domain>/core/model/` — aggregates, value objects
       - `<domain>/core/port/in/` — inbound ports (use case interfaces)
       - `<domain>/core/port/out/` — outbound ports (repository interfaces)
       - `<domain>/core/event/` — domain events
       - `<domain>/app/usecase/` — use case implementations
       - `<domain>/adapter/in/rest/` — REST controllers
       - `<domain>/adapter/in/messaging/` — message consumers
       - `<domain>/adapter/out/persistence/` — repository implementations
       - `<domain>/adapter/out/event/` — event publisher implementations
    7. **Contracts** — reference relevant spec artifacts (middleware contracts, error codes, payload schemas).
    8. **Quality gates** — list applicable gate IDs from: {', '.join(qg_ids)}.
    9. **Test tasks** — for each domain-core or application task, generate a corresponding test task.
    10. **Status-only changes** (e.g., "Status proposed → approved") do NOT generate tasks;
        skip them and note in the summary.
    11. Task IDs MUST be sequential: TASK-001, TASK-002, etc.

    ## Output Format

    Respond with a single JSON object (no markdown fences):
    {{
      "tasks": [
        {{
          "task_id": "TASK-001",
          "title": "<concise title>",
          "layer": "domain-core" | "application" | "adapter-in" | "adapter-out" | "middleware" | "test",
          "domain": "<domain name>",
          "description": "<detailed implementation instructions for an LLM agent>",
          "acceptance_criteria": ["<criterion 1>", "<criterion 2>"],
          "source_artifacts": ["CAP-0002", "BR-0003", "CMD-0005"],
          "target_files": ["auth/core/model/User.kt", "auth/core/port/in/ActivateUserUseCase.kt"],
          "contracts": ["mw.auth contract (JWKS validation)", "error-registry AUTH.CREDENTIALS.INVALID"],
          "error_codes": ["COMMON.NOT_FOUND", "COMMON.CONFLICT"],
          "depends_on": [],
          "priority": "high" | "medium" | "low",
          "quality_gates": ["qg.tests.unit", "qg.arch.boundaries"]
        }}
      ],
      "skipped_changes": [
        {{
          "target": "BV-0001",
          "reason": "Status-only change (proposed → approved), no code impact"
        }}
      ],
      "summary": "<brief summary of what the task set covers>"
    }}
    """)


def build_user_prompt(delta: DeltaInfo, impacts: List[ImpactEntry]) -> str:
    """Build the user message with delta changes and resolved context."""

    changes_detail = []
    for imp in impacts:
        entry: Dict[str, Any] = {
            "change_type": imp.change.change_type,
            "target": imp.change.target,
            "description": imp.change.description,
        }

        if imp.artifact:
            entry["artifact_data"] = {
                "kind": imp.artifact.kind,
                "title": imp.artifact.data.get("title", ""),
                "status": imp.artifact.data.get("status", ""),
                "description": imp.artifact.data.get("description", ""),
            }
            if imp.artifact.kind == "CAP":
                entry["artifact_data"]["acceptance_criteria"] = imp.artifact.data.get(
                    "acceptance_criteria", [])
            if imp.artifact.kind == "BR":
                entry["artifact_data"]["statement"] = imp.artifact.data.get("statement", "")
                entry["artifact_data"]["acceptance_criteria"] = imp.artifact.data.get(
                    "acceptance_criteria", [])
            if imp.artifact.kind == "NFR":
                entry["artifact_data"]["metric"] = imp.artifact.data.get("metric", "")
                entry["artifact_data"]["target"] = imp.artifact.data.get("target", "")

        if imp.domain:
            entry["domain"] = imp.domain
        if imp.cmd_specs:
            entry["commands"] = imp.cmd_specs
        if imp.evt_specs:
            entry["events"] = imp.evt_specs
        if imp.br_specs:
            entry["related_business_rules"] = imp.br_specs
        if imp.middleware_context:
            entry["affected_middleware"] = imp.middleware_context

        changes_detail.append(entry)

    return textwrap.dedent(f"""\
    Generate implementation tasks for the following delta:

    **Delta**: {delta.delta_id}
    **Title**: {delta.title}
    **Status**: {delta.status}

    **Changes with full context**:
    {json.dumps(changes_detail, indent=2, default=str)}

    Decompose these changes into implementation tasks. Skip status-only changes
    (e.g., "Status proposed → approved"). Focus on changes that require actual
    code creation or modification: new business rules, new capabilities,
    new commands/events, amended capabilities with new trace links.
    """)


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------

def _call_openai(system: str, user: str) -> str:
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
        url, data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        _error(f"LLM API error {e.code}: {error_body[:500]}")
        raise SystemExit(1)


def _call_anthropic(system: str, user: str) -> str:
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": LLM_MODEL,
        "max_tokens": 16384,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": LLM_API_KEY,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["content"][0]["text"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        _error(f"Anthropic API error {e.code}: {error_body[:500]}")
        raise SystemExit(1)


def call_llm(system: str, user: str) -> str:
    if not LLM_API_KEY:
        _error(
            "TASKGEN_LLM_API_KEY is not set.\n"
            "  export TASKGEN_LLM_API_KEY=sk-...\n"
            "  Optional: TASKGEN_LLM_PROVIDER=openai|anthropic\n"
            "  Optional: TASKGEN_LLM_BASE_URL=https://api.openai.com/v1\n"
            "  Optional: TASKGEN_LLM_MODEL=gpt-4o"
        )
        raise SystemExit(1)
    if LLM_PROVIDER == "anthropic":
        return _call_anthropic(system, user)
    return _call_openai(system, user)


# ---------------------------------------------------------------------------
# Response Parser
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        first_nl = text.index("\n")
        last_fence = text.rfind("```")
        if last_fence > first_nl:
            text = text[first_nl + 1:last_fence].strip()
    return json.loads(text)


def parse_llm_response(response_text: str, delta: DeltaInfo) -> TaskPlan:
    data = _extract_json(response_text)
    plan = TaskPlan(
        delta=delta,
        generation_date=datetime.date.today().isoformat(),
    )
    for t in data.get("tasks", []):
        plan.tasks.append(Task(
            task_id=t.get("task_id", ""),
            title=t.get("title", ""),
            layer=t.get("layer", ""),
            domain=t.get("domain", ""),
            description=t.get("description", ""),
            acceptance_criteria=t.get("acceptance_criteria", []),
            source_artifacts=t.get("source_artifacts", []),
            target_files=t.get("target_files", []),
            contracts=t.get("contracts", []),
            error_codes=t.get("error_codes", []),
            depends_on=t.get("depends_on", []),
            priority=t.get("priority", "medium"),
            quality_gates=t.get("quality_gates", []),
        ))
    return plan


# ---------------------------------------------------------------------------
# Stage 4: ORDER — topological sort by depends_on
# ---------------------------------------------------------------------------

def topological_sort(tasks: List[Task]) -> List[Task]:
    id_to_task = {t.task_id: t for t in tasks}
    visited: Set[str] = set()
    result: List[Task] = []

    layer_order = {
        "domain-core": 0, "application": 1,
        "adapter-in": 2, "adapter-out": 2,
        "middleware": 3, "test": 4,
    }

    def visit(task_id: str, visiting: Set[str]) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            _warn(f"Circular dependency detected involving {task_id}, breaking cycle.")
            return
        if task_id not in id_to_task:
            return
        visiting.add(task_id)
        task = id_to_task[task_id]
        for dep_id in task.depends_on:
            visit(dep_id, visiting)
        visiting.discard(task_id)
        visited.add(task_id)
        result.append(task)

    sorted_tasks = sorted(tasks, key=lambda t: (layer_order.get(t.layer, 99), t.task_id))
    for task in sorted_tasks:
        visit(task.task_id, set())

    return result


# ---------------------------------------------------------------------------
# Output Formatters
# ---------------------------------------------------------------------------

def format_yaml(plan: TaskPlan) -> str:
    output: Dict[str, Any] = {
        "delta": {"id": plan.delta.delta_id, "title": plan.delta.title},
        "generation_date": plan.generation_date,
        "tasks": [],
    }
    for t in plan.tasks:
        task_dict: Dict[str, Any] = {
            "task_id": t.task_id, "title": t.title,
            "layer": t.layer, "domain": t.domain,
            "description": t.description,
            "acceptance_criteria": t.acceptance_criteria,
            "source_artifacts": t.source_artifacts,
            "priority": t.priority,
        }
        if t.target_files:
            task_dict["target_files"] = t.target_files
        if t.contracts:
            task_dict["contracts"] = t.contracts
        if t.error_codes:
            task_dict["error_codes"] = t.error_codes
        if t.depends_on:
            task_dict["depends_on"] = t.depends_on
        if t.quality_gates:
            task_dict["quality_gates"] = t.quality_gates
        output["tasks"].append(task_dict)
    return yaml.dump(output, default_flow_style=False, allow_unicode=True,
                     sort_keys=False, width=120)


def format_task_markdown(task: Task, delta_id: str) -> str:
    lines = [
        f"# {task.task_id}: {task.title}", "",
        f"**Delta**: {delta_id}",
        f"**Layer**: {task.layer}",
        f"**Domain**: {task.domain}",
        f"**Priority**: {task.priority}", "",
    ]
    if task.depends_on:
        lines.append(f"**Depends on**: {', '.join(task.depends_on)}")
        lines.append("")
    lines += ["## Description", "", task.description, ""]
    if task.acceptance_criteria:
        lines.append("## Acceptance Criteria")
        lines.append("")
        for ac in task.acceptance_criteria:
            lines.append(f"- [ ] {ac}")
        lines.append("")
    if task.source_artifacts:
        lines.append("## Source Artifacts")
        lines.append("")
        for sa in task.source_artifacts:
            lines.append(f"- {sa}")
        lines.append("")
    if task.target_files:
        lines.append("## Target Files")
        lines.append("")
        for tf in task.target_files:
            lines.append(f"- `{tf}`")
        lines.append("")
    if task.contracts:
        lines.append("## Contracts & References")
        lines.append("")
        for c in task.contracts:
            lines.append(f"- {c}")
        lines.append("")
    if task.error_codes:
        lines.append("## Error Codes")
        lines.append("")
        for ec in task.error_codes:
            lines.append(f"- `{ec}`")
        lines.append("")
    if task.quality_gates:
        lines.append("## Quality Gates")
        lines.append("")
        for qg in task.quality_gates:
            lines.append(f"- `{qg}`")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def display_impact_analysis(delta: DeltaInfo, impacts: List[ImpactEntry]) -> None:
    print("\n" + "=" * 70)
    print("IMPACT ANALYSIS")
    print("=" * 70)
    print(f"\nDelta: {delta.delta_id}")
    print(f"Title: {delta.title}")
    print(f"Status: {delta.status}")
    print(f"Changes: {len(delta.changes)}")

    code_changes = []
    status_changes = []
    for imp in impacts:
        desc = imp.change.description.lower()
        if "status" in desc and "→" in desc:
            status_changes.append(imp)
        else:
            code_changes.append(imp)

    if status_changes:
        print(f"\nStatus-only changes ({len(status_changes)}) — will be SKIPPED:")
        for imp in status_changes:
            print(f"  {imp.change.target}: {imp.change.description}")

    if code_changes:
        print(f"\nCode-impacting changes ({len(code_changes)}):")
        for imp in code_changes:
            domain_str = f" [{imp.domain}]" if imp.domain else ""
            print(f"  {imp.change.change_type:10s} {imp.change.target}{domain_str}")
            print(f"              {imp.change.description}")
            if imp.cmd_specs:
                print(f"              Commands: {', '.join(c.get('id', '?') for c in imp.cmd_specs)}")
            if imp.evt_specs:
                print(f"              Events: {', '.join(e.get('id', '?') for e in imp.evt_specs)}")
            if imp.br_specs:
                print(f"              BRs: {', '.join(b.get('id', '?') for b in imp.br_specs)}")
            if imp.middleware_context:
                print(f"              Middleware: {', '.join(imp.middleware_context)}")

    print("=" * 70)


def display_task_plan(plan: TaskPlan) -> None:
    print("\n" + "=" * 70)
    print("TASK PLAN")
    print("=" * 70)
    print(f"\nDelta: {plan.delta.delta_id} — {plan.delta.title}")
    print(f"Generated: {plan.generation_date}")
    print(f"Tasks: {len(plan.tasks)}")

    by_layer: Dict[str, List[Task]] = {}
    for t in plan.tasks:
        by_layer.setdefault(t.layer, []).append(t)

    for layer, tasks in by_layer.items():
        print(f"\n  [{layer}]")
        for t in tasks:
            deps = f" (depends: {', '.join(t.depends_on)})" if t.depends_on else ""
            print(f"    {t.task_id}: {t.title}{deps}")
            if t.source_artifacts:
                print(f"           sources: {', '.join(t.source_artifacts)}")

    print("\n" + "=" * 70)


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    delta_path: Path,
    output_format: str = "yaml",
    out_dir: Optional[Path] = None,
    plan_only: bool = False,
) -> TaskPlan:

    print("=" * 70)
    print("  Sonora — Task Generation Pipeline")
    print("=" * 70)

    print("\n[1/4] IMPACT")
    _info(f"Loading delta: {delta_path.relative_to(REPO_ROOT)}")
    delta = load_delta(delta_path)
    _info(f"Delta {delta.delta_id}: {delta.title} ({delta.status})")
    _info(f"Changes: {len(delta.changes)}")

    _info("Resolving artifacts...")
    impacts = analyze_impact(delta)

    code_impacts = [
        imp for imp in impacts
        if not ("status" in imp.change.description.lower() and "→" in imp.change.description)
    ]
    _info(f"Code-impacting: {len(code_impacts)}, status-only: {len(impacts) - len(code_impacts)}")

    display_impact_analysis(delta, impacts)

    if plan_only:
        print("\n[--plan mode] Impact analysis complete. No LLM call made.")
        return TaskPlan(delta=delta, impacts=impacts)

    if not code_impacts:
        _info("No code-impacting changes found. Nothing to generate.")
        return TaskPlan(delta=delta, impacts=impacts)

    print("\n[2-3/4] DECOMPOSE + SPECIFY")
    _info("Building prompt from architecture context...")
    system_prompt = build_system_prompt(delta, impacts)
    user_prompt = build_user_prompt(delta, impacts)

    _info(f"System prompt: {len(system_prompt)} chars")
    _info(f"User prompt: {len(user_prompt)} chars")
    _info(f"Calling LLM ({LLM_PROVIDER}/{LLM_MODEL})...")

    response = call_llm(system_prompt, user_prompt)
    _info("Parsing response...")
    plan = parse_llm_response(response, delta)
    plan.impacts = impacts

    _info(f"Generated {len(plan.tasks)} tasks")

    print("\n[4/4] ORDER")
    plan.tasks = topological_sort(plan.tasks)
    _info(f"Topologically sorted {len(plan.tasks)} tasks")

    display_task_plan(plan)

    if output_format == "yaml":
        output = format_yaml(plan)
        if out_dir:
            out_path = out_dir / f"tasks-{delta.delta_id}.yaml"
            _write_text(out_path, output)
            _info(f"Written to: {out_path}")
        else:
            print("\n--- YAML OUTPUT ---")
            print(output)

    elif output_format == "files":
        target = out_dir or (REPO_ROOT / "tasks" / delta.delta_id)
        _info(f"Writing task files to: {target}")
        for task in plan.tasks:
            md = format_task_markdown(task, delta.delta_id)
            task_file = target / f"{task.task_id}.md"
            _write_text(task_file, md)
            _info(f"  {task_file.relative_to(REPO_ROOT)}")

        index_yaml = format_yaml(plan)
        _write_text(target / "index.yaml", index_yaml)
        _info(f"  {(target / 'index.yaml').relative_to(REPO_ROOT)}")

    print("\n" + "=" * 70)
    print(f"  Pipeline completed. {len(plan.tasks)} tasks generated.")
    print("=" * 70)

    return plan


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Task Generation Pipeline — generate implementation tasks from deltas.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Environment variables:
              TASKGEN_LLM_PROVIDER   'openai' (default) or 'anthropic'
              TASKGEN_LLM_BASE_URL   API base URL (default: https://api.openai.com/v1)
              TASKGEN_LLM_API_KEY    API key (required unless --plan)
              TASKGEN_LLM_MODEL      Model name (default: gpt-4o)

            Examples:
              python tools/taskgen.py --delta specs/deltas/2026-02-11-auth-domain-model.yaml --plan
              python tools/taskgen.py --delta specs/deltas/2026-02-11-auth-domain-model.yaml
              python tools/taskgen.py --all-pending --format files --out-dir tasks/
        """),
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--delta", "-d",
        help="Path to a specific delta YAML file.",
    )
    input_group.add_argument(
        "--all-pending",
        action="store_true",
        help="Process all deltas with status 'proposed' or 'applied'.",
    )

    parser.add_argument(
        "--format", "-f",
        choices=["yaml", "files"],
        default="yaml",
        help="Output format: 'yaml' (single YAML doc) or 'files' (individual .md per task).",
    )
    parser.add_argument(
        "--out-dir", "-o",
        help="Output directory for generated files.",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Show impact analysis only (no LLM call, no task generation).",
    )

    args = parser.parse_args()

    if args.delta:
        delta_path = Path(args.delta)
        if not delta_path.is_absolute():
            delta_path = REPO_ROOT / delta_path
        if not delta_path.exists():
            _error(f"Delta file not found: {args.delta}")
            raise SystemExit(1)
        delta_paths = [delta_path]
    else:
        delta_paths = find_pending_deltas()
        if not delta_paths:
            _info("No pending deltas found.")
            return
        _info(f"Found {len(delta_paths)} pending delta(s)")

    out_dir = Path(args.out_dir) if args.out_dir else None

    for dp in delta_paths:
        run_pipeline(
            delta_path=dp,
            output_format=args.format,
            out_dir=out_dir,
            plan_only=args.plan,
        )


if __name__ == "__main__":
    main()
