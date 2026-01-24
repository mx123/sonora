#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]

STATUS_IMPLEMENTED = "implemented"

ID_PATTERNS = {
    "BV": re.compile(r"^BV-\d{4}$"),
    "CAP": re.compile(r"^CAP-\d{4}$"),
    "BR": re.compile(r"^BR-\d{4}$"),
    "NFR": re.compile(r"^NFR-\d{4}$"),
}

DOMAIN_FRAGMENT_RE = re.compile(r"^(specs/domain/.+\.(md|yaml))#((CMD|EVT)-\d{4})$")


@dataclass(frozen=True)
class SpecFile:
    path: Path
    kind: str  # BV/CAP/BR/NFR/TRACE/DELTA


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _fail(msg: str) -> None:
    print(f"ERROR: {msg}")
    raise SystemExit(1)


def _collect_files() -> List[SpecFile]:
    specs = []

    base = REPO_ROOT / "specs"
    req = base / "requirements"

    mapping = [
        (req / "business-values", "BV"),
        (req / "capabilities", "CAP"),
        (req / "business-rules", "BR"),
        (req / "nfr", "NFR"),
    ]

    for folder, kind in mapping:
        if not folder.exists():
            continue
        for p in sorted(folder.glob("*.yaml")):
            specs.append(SpecFile(path=p, kind=kind))

    trace_links = req / "trace-links.yaml"
    if trace_links.exists():
        specs.append(SpecFile(path=trace_links, kind="TRACE"))

    deltas = base / "deltas"
    if deltas.exists():
        for p in sorted(deltas.glob("*.yaml")):
            specs.append(SpecFile(path=p, kind="DELTA"))

    return specs


def _schema_for(kind: str) -> Optional[Path]:
    schemas = REPO_ROOT / "specs" / "schemas"
    return {
        "BV": schemas / "bv.schema.json",
        "CAP": schemas / "cap.schema.json",
        "BR": schemas / "br.schema.json",
        "NFR": schemas / "nfr.schema.json",
        "TRACE": schemas / "trace-links.schema.json",
        "DELTA": schemas / "delta.schema.json",
    }.get(kind)


def _validate_schema(kind: str, path: Path, doc: Any) -> None:
    schema_path = _schema_for(kind)
    if not schema_path or not schema_path.exists():
        _fail(f"Missing schema for {kind}: {schema_path}")

    schema = _load_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    if errors:
        lines = [f"{path.relative_to(REPO_ROOT)}"]
        for e in errors[:10]:
            loc = "/".join(str(x) for x in e.path) if e.path else "<root>"
            lines.append(f"  - {loc}: {e.message}")
        _fail("Schema validation failed:\n" + "\n".join(lines))


def _validate_id_matches_filename(kind: str, path: Path, doc: Any) -> str:
    if kind in {"TRACE", "DELTA"}:
        return ""

    file_stem = path.stem
    spec_id = (doc or {}).get("id")
    if not isinstance(spec_id, str):
        _fail(f"{path.relative_to(REPO_ROOT)}: missing/invalid 'id'")

    if file_stem != spec_id:
        _fail(f"{path.relative_to(REPO_ROOT)}: filename '{file_stem}' must match id '{spec_id}'")

    prefix = kind
    pattern = ID_PATTERNS[prefix]
    if not pattern.match(spec_id):
        _fail(f"{path.relative_to(REPO_ROOT)}: id '{spec_id}' does not match pattern {pattern.pattern}")

    return spec_id


def _resolve_md_anchor(target_path: Path, fragment: str) -> bool:
    text = target_path.read_text(encoding="utf-8")
    needle = f'id="{fragment}"'
    return needle in text


def _validate_domain_links(cap_path: Path, cap_doc: Mapping[str, Any]) -> None:
    status = cap_doc.get("status")
    trace = cap_doc.get("trace") or {}
    domain = (trace.get("domain") or {}) if isinstance(trace, Mapping) else {}

    commands = domain.get("commands")
    events = domain.get("events")

    def _as_list(v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, list) and all(isinstance(x, str) for x in v):
            return v
        _fail(f"{cap_path.relative_to(REPO_ROOT)}: trace.domain.commands/events must be a list of strings")

    cmd_links = _as_list(commands)
    evt_links = _as_list(events)

    if status == STATUS_IMPLEMENTED:
        if not cmd_links:
            _fail(f"{cap_path.relative_to(REPO_ROOT)}: status=implemented requires trace.domain.commands")
        if not evt_links:
            _fail(f"{cap_path.relative_to(REPO_ROOT)}: status=implemented requires trace.domain.events")

    for link in cmd_links + evt_links:
        m = DOMAIN_FRAGMENT_RE.match(link)
        if not m:
            _fail(
                f"{cap_path.relative_to(REPO_ROOT)}: invalid domain trace link '{link}' (expected specs/domain/<file>.md#CMD-#### or #EVT-####)"
            )

        target_rel = m.group(1)
        fragment = m.group(3)
        target = REPO_ROOT / target_rel
        if not target.exists():
            _fail(f"{cap_path.relative_to(REPO_ROOT)}: domain trace target does not exist: {target_rel}")

        if target.suffix == ".md":
            if not _resolve_md_anchor(target, fragment):
                _fail(
                    f"{cap_path.relative_to(REPO_ROOT)}: anchor '{fragment}' not found in {target_rel} (expected <a id=\"{fragment}\"></a> or any element with id=\"{fragment}\")"
                )
        else:
            # YAML domain targets can be added later; for now keep strict.
            _fail(
                f"{cap_path.relative_to(REPO_ROOT)}: only markdown domain targets are supported right now: {target_rel}"
            )


def _load_all_requirement_ids() -> Dict[str, Set[str]]:
    ids: Dict[str, Set[str]] = {"BV": set(), "CAP": set(), "BR": set(), "NFR": set()}

    files = _collect_files()
    for sf in files:
        if sf.kind not in ids:
            continue
        doc = _load_yaml(sf.path) or {}
        spec_id = _validate_id_matches_filename(sf.kind, sf.path, doc)
        ids[sf.kind].add(spec_id)

    return ids


def _validate_trace_links(ids: Dict[str, Set[str]]) -> None:
    trace_path = REPO_ROOT / "specs" / "requirements" / "trace-links.yaml"
    if not trace_path.exists():
        return

    doc = _load_yaml(trace_path) or {}
    _validate_schema("TRACE", trace_path, doc)

    links = doc.get("links")
    if not isinstance(links, list):
        _fail(f"{trace_path.relative_to(REPO_ROOT)}: 'links' must be a list")

    all_known: Set[str] = set().union(*ids.values())

    cap_to_bv: Dict[str, int] = {}
    br_to_cap: Dict[str, int] = {}

    for i, link in enumerate(links):
        if not isinstance(link, dict):
            _fail(f"{trace_path.relative_to(REPO_ROOT)}: links[{i}] must be an object")

        src = link.get("from")
        dst = link.get("to")
        typ = link.get("type")
        if not isinstance(src, str) or not isinstance(dst, str) or not isinstance(typ, str):
            _fail(f"{trace_path.relative_to(REPO_ROOT)}: links[{i}] must contain string from/to/type")

        if src not in all_known:
            _fail(f"{trace_path.relative_to(REPO_ROOT)}: links[{i}].from references unknown id '{src}'")
        if dst not in all_known:
            _fail(f"{trace_path.relative_to(REPO_ROOT)}: links[{i}].to references unknown id '{dst}'")

        if typ == "realizes" and src.startswith("BV-") and dst.startswith("CAP-"):
            cap_to_bv[dst] = cap_to_bv.get(dst, 0) + 1
        if typ == "satisfies" and src.startswith("CAP-") and dst.startswith("BR-"):
            br_to_cap[dst] = br_to_cap.get(dst, 0) + 1

    # Coverage gates (minimal baseline)
    for cap_id in ids["CAP"]:
        if cap_to_bv.get(cap_id, 0) < 1:
            _fail(f"Coverage gate: {cap_id} must realize at least one BV-* via trace-links.yaml")

    for br_id in ids["BR"]:
        if br_to_cap.get(br_id, 0) < 1:
            _fail(f"Coverage gate: {br_id} must be satisfied by at least one CAP-* via trace-links.yaml")


def _validate_deltas(ids: Dict[str, Set[str]]) -> None:
    deltas_dir = REPO_ROOT / "specs" / "deltas"
    if not deltas_dir.exists():
        return

    all_known: Set[str] = set().union(*ids.values())

    for p in sorted(deltas_dir.glob("*.yaml")):
        doc = _load_yaml(p) or {}
        _validate_schema("DELTA", p, doc)

        changes = doc.get("changes")
        if not isinstance(changes, list):
            _fail(f"{p.relative_to(REPO_ROOT)}: changes must be a list")

        for i, ch in enumerate(changes):
            if not isinstance(ch, dict):
                _fail(f"{p.relative_to(REPO_ROOT)}: changes[{i}] must be an object")
            target = ch.get("target")
            if not isinstance(target, str):
                _fail(f"{p.relative_to(REPO_ROOT)}: changes[{i}].target must be a string")
            if target not in all_known:
                _fail(f"{p.relative_to(REPO_ROOT)}: changes[{i}].target references unknown id '{target}'")


def main() -> None:
    files = _collect_files()
    if not files:
        _fail("No spec files found under specs/")

    ids = _load_all_requirement_ids()

    # Schema validation + per-file checks
    for sf in files:
        doc = _load_yaml(sf.path) or {}
        _validate_schema(sf.kind, sf.path, doc)

        if sf.kind in {"BV", "CAP", "BR", "NFR"}:
            _validate_id_matches_filename(sf.kind, sf.path, doc)

        if sf.kind == "CAP":
            if not isinstance(doc, Mapping):
                _fail(f"{sf.path.relative_to(REPO_ROOT)}: expected object")
            _validate_domain_links(sf.path, doc)

    _validate_trace_links(ids)
    _validate_deltas(ids)

    print("OK: specs validation passed")


if __name__ == "__main__":
    main()
