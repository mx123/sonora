#!/usr/bin/env python3
"""
Bootstrap CLI — instantiate a new project from the meta-template.

Usage:
    python tools/bootstrap.py --config bootstrap.yaml [--dry-run]

Reads bootstrap.yaml and performs:
  1. Validates config against specs/schemas/bootstrap.schema.json
  2. Replaces parameterized placeholders in target files
  3. Adopts seed package (auth or none)
  4. Scaffolds additional domains
  5. Cleans Example Domain placeholder
  6. Runs validate.py as final gate
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema is required. Install: pip install jsonschema")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent  # assumes tools/bootstrap.py
SPECS = REPO_ROOT / "specs"
DOCS = REPO_ROOT / "docs"
SCHEMAS = SPECS / "schemas"

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _replace_in_file(path: Path, replacements: Dict[str, str]) -> bool:
    """Replace multiple strings in a file. Returns True if any replacement was made."""
    if not path.exists():
        return False
    text = _read_text(path)
    original = text
    for old, new in replacements.items():
        text = text.replace(old, new)
    if text != original:
        _write_text(path, text)
        return True
    return False


# ---------------------------------------------------------------------------
# Step 1: Validate config
# ---------------------------------------------------------------------------


def validate_config(config: Dict[str, Any]) -> None:
    schema_path = SCHEMAS / "bootstrap.schema.json"
    if not schema_path.exists():
        print(f"WARNING: Bootstrap schema not found at {schema_path}; skipping validation.")
        return
    schema = _load_json(schema_path)
    try:
        jsonschema.validate(instance=config, schema=schema)
    except jsonschema.ValidationError as e:
        print(f"ERROR: bootstrap.yaml validation failed: {e.message}")
        sys.exit(1)
    print("  ✓ bootstrap.yaml validated against schema")


# ---------------------------------------------------------------------------
# Step 2: Replace parameterized placeholders
# ---------------------------------------------------------------------------


def apply_parameterized_replacements(config: Dict[str, Any], dry_run: bool) -> List[str]:
    """Replace CHANGE_ME and known placeholders across project files."""
    project = config["project"]
    repos = config.get("repos", {})
    changed: List[str] = []

    # --- workspace-registry.yaml ---
    reg_path = SPECS / "registry" / "workspace-registry.yaml"
    if reg_path.exists():
        doc = _load_yaml(reg_path)
        if isinstance(doc, dict) and isinstance(doc.get("repos"), list):
            repo_map = {
                "repo.specs": repos.get("specs", "CHANGE_ME"),
                "repo.backend": repos.get("backend", "CHANGE_ME"),
                "repo.frontend.web": repos.get("frontendWeb", "CHANGE_ME"),
                "repo.frontend.mobile": repos.get("frontendMobile", "CHANGE_ME"),
            }
            modified = False
            for r in doc["repos"]:
                rid = r.get("id", "")
                if rid in repo_map and repo_map[rid] != "CHANGE_ME":
                    if r.get("url") == "CHANGE_ME":
                        r["url"] = repo_map[rid]
                        modified = True
            if modified and not dry_run:
                _write_yaml(reg_path, doc)
                changed.append(str(reg_path.relative_to(REPO_ROOT)))

    # --- error-registry.md ---
    err_reg = SPECS / "rules" / "error-registry.md"
    if _replace_in_file(err_reg, {"errors.kx.example.com": project["errorBaseUri"].rstrip("/")}):
        changed.append(str(err_reg.relative_to(REPO_ROOT)))

    # --- workspace.dsl ---
    dsl_path = SPECS / "architecture" / "structurizr" / "workspace.dsl"
    if _replace_in_file(dsl_path, {"KX Platform": project["name"]}):
        changed.append(str(dsl_path.relative_to(REPO_ROOT)))

    return changed


# ---------------------------------------------------------------------------
# Step 3: Seed adoption
# ---------------------------------------------------------------------------


def adopt_seed(config: Dict[str, Any], dry_run: bool) -> List[str]:
    """If seed == 'auth', ensure Auth domain artifacts are present (they are baseline).
    If seed == 'none', remove Auth domain artifacts."""
    seed = config.get("seed", "auth")
    removed: List[str] = []

    if seed == "none":
        # Remove Auth domain seed files
        auth_files = [
            SPECS / "architecture" / "domain" / "DOM-0001.yaml",
        ]
        auth_req_dirs = [
            SPECS / "requirements" / "business-values",
            SPECS / "requirements" / "capabilities",
            SPECS / "requirements" / "business-rules",
        ]
        for f in auth_files:
            if f.exists() and not dry_run:
                f.unlink()
                removed.append(str(f.relative_to(REPO_ROOT)))

        # Remove BV/CAP/BR files (all are Auth seed)
        for d in auth_req_dirs:
            if d.exists():
                for f in d.glob("*.yaml"):
                    if not dry_run:
                        f.unlink()
                    removed.append(str(f.relative_to(REPO_ROOT)))

        # Clear commands.md and events.md to structure-only
        for md_name in ["commands.md", "events.md"]:
            md_path = SPECS / "domain" / md_name
            if md_path.exists() and not dry_run:
                if md_name == "commands.md":
                    _write_text(md_path, textwrap.dedent("""\
                        # Domain Commands

                        This file defines domain Commands for traceability.
                        Commands are NOT APIs; APIs are projections of the domain.

                        ---

                        <!-- Add domain command sections below -->
                    """))
                else:
                    _write_text(md_path, textwrap.dedent("""\
                        # Domain Events

                        This file defines domain Events for traceability.
                        Events are guaranteed facts — they represent something that has already happened.

                        ---

                        <!-- Add domain event sections below -->
                    """))
                removed.append(str(md_path.relative_to(REPO_ROOT)))

        # Clear trace-links.yaml
        trace_path = SPECS / "requirements" / "trace-links.yaml"
        if trace_path.exists() and not dry_run:
            _write_text(trace_path, "links: []\n")
            removed.append(str(trace_path.relative_to(REPO_ROOT)))

        # Update domains.yaml to empty
        domains_path = SPECS / "architecture" / "domain" / "domains.yaml"
        if domains_path.exists() and not dry_run:
            doc = _load_yaml(domains_path)
            if isinstance(doc, dict):
                doc["domains"] = []
                _write_yaml(domains_path, doc)
                removed.append(str(domains_path.relative_to(REPO_ROOT)))

    return removed


# ---------------------------------------------------------------------------
# Step 4: Domain scaffolding
# ---------------------------------------------------------------------------


def scaffold_domains(config: Dict[str, Any], dry_run: bool) -> List[str]:
    """Create DOM-XXXX.yaml files and update domains.yaml for each domain in config."""
    domains = config.get("domains", [])
    if not domains:
        return []

    created: List[str] = []
    domains_yaml_path = SPECS / "architecture" / "domain" / "domains.yaml"
    domains_doc = _load_yaml(domains_yaml_path) if domains_yaml_path.exists() else {"schemaVersion": 1, "domains": []}
    domain_list = domains_doc.get("domains", [])

    # Determine next DOM ID
    existing_ids = []
    for entry in domain_list:
        if isinstance(entry, str):
            m = re.match(r"DOM-(\d+)", entry.split("#")[0].strip())
            if m:
                existing_ids.append(int(m.group(1)))
    next_id = max(existing_ids, default=0) + 1

    # Also check for standalone DOM files
    dom_dir = SPECS / "architecture" / "domain"
    for f in dom_dir.glob("DOM-*.yaml"):
        m = re.match(r"DOM-(\d+)", f.stem)
        if m:
            existing_ids.append(int(m.group(1)))
    next_id = max(max(existing_ids, default=0) + 1, next_id)

    commands_md = SPECS / "domain" / "commands.md"
    events_md = SPECS / "domain" / "events.md"

    for domain in domains:
        dom_id = f"DOM-{next_id:04d}"
        name = domain["name"]
        desc = domain.get("description", f"{name} domain.")
        entrypoint_slug = name.lower().replace(" ", "-").replace("_", "-")

        # Create DOM file
        dom_content = {
            "id": dom_id,
            "status": "proposed",
            "name": name,
            "description": desc,
            "repoId": "repo.backend",
            "entrypoints": {
                "core": f"entry.domain.{entrypoint_slug}.core",
                "container": f"entry.domain.{entrypoint_slug}.container",
            },
        }
        dom_path = dom_dir / f"{dom_id}.yaml"
        if not dry_run:
            _write_yaml(dom_path, dom_content)
        created.append(str(dom_path.relative_to(REPO_ROOT)))

        # Add to domains.yaml
        domain_list.append(f"{dom_id}  # {name}")

        # Add skeleton section to commands.md
        if commands_md.exists() and not dry_run:
            cmd_section = f"\n\n---\n\n## {name} Domain ({dom_id})\n\n<!-- Add {name} commands here -->\n"
            with commands_md.open("a", encoding="utf-8") as f:
                f.write(cmd_section)

        # Add skeleton section to events.md
        if events_md.exists() and not dry_run:
            evt_section = f"\n\n---\n\n## {name} Domain ({dom_id})\n\n<!-- Add {name} events here -->\n"
            with events_md.open("a", encoding="utf-8") as f:
                f.write(evt_section)

        next_id += 1

    # Write updated domains.yaml
    if not dry_run:
        domains_doc["domains"] = domain_list
        _write_yaml(domains_yaml_path, domains_doc)
        created.append(str(domains_yaml_path.relative_to(REPO_ROOT)))

    return created


# ---------------------------------------------------------------------------
# Step 5: Clean placeholders
# ---------------------------------------------------------------------------


def clean_placeholders(dry_run: bool) -> List[str]:
    """Remove Example Domain (DOM-0002) and stale generated artifacts."""
    cleaned: List[str] = []

    # Remove DOM-0002
    dom2 = SPECS / "architecture" / "domain" / "DOM-0002.yaml"
    if dom2.exists() and not dry_run:
        dom2.unlink()
        cleaned.append(str(dom2.relative_to(REPO_ROOT)))

    # Remove DOM-0002 from domains.yaml
    domains_path = SPECS / "architecture" / "domain" / "domains.yaml"
    if domains_path.exists():
        text = _read_text(domains_path)
        new_text = "\n".join(
            line for line in text.splitlines()
            if "DOM-0002" not in line
        ) + "\n"
        if new_text != text and not dry_run:
            _write_text(domains_path, new_text)
            cleaned.append(str(domains_path.relative_to(REPO_ROOT)))

    # Remove Example Domain Service from workspace.dsl
    dsl_path = SPECS / "architecture" / "structurizr" / "workspace.dsl"
    if dsl_path.exists():
        text = _read_text(dsl_path)
        # Remove exampleDomain container and its relationships
        lines = text.splitlines()
        filtered = []
        skip_block = False
        for line in lines:
            if "exampleDomain" in line and "container" in line:
                skip_block = True
                continue
            if skip_block and line.strip() == "}":
                skip_block = False
                continue
            if "exampleDomain" in line:
                continue
            filtered.append(line)
        new_text = "\n".join(filtered) + "\n"
        if new_text != text + "\n" and not dry_run:
            _write_text(dsl_path, new_text)
            cleaned.append(str(dsl_path.relative_to(REPO_ROOT)))

    # Remove stale workspace.json
    ws_json = SPECS / "architecture" / "structurizr" / "workspace.json"
    if ws_json.exists() and not dry_run:
        ws_json.unlink()
        cleaned.append(str(ws_json.relative_to(REPO_ROOT)))

    # Remove .structurizr state directory
    structurizr_state = SPECS / "architecture" / "structurizr" / ".structurizr"
    if structurizr_state.exists() and not dry_run:
        shutil.rmtree(structurizr_state)
        cleaned.append(str(structurizr_state.relative_to(REPO_ROOT)))

    # Remove stale derived mermaid diagrams
    derived_structurizr = DOCS / "derived" / "structurizr"
    if derived_structurizr.exists():
        for f in derived_structurizr.glob("*.mmd"):
            if not dry_run:
                f.unlink()
            cleaned.append(str(f.relative_to(REPO_ROOT)))

    # Clear all deltas (project-specific history)
    deltas_dir = SPECS / "deltas"
    if deltas_dir.exists():
        for f in deltas_dir.glob("*.yaml"):
            if not dry_run:
                f.unlink()
            cleaned.append(str(f.relative_to(REPO_ROOT)))

    return cleaned


# ---------------------------------------------------------------------------
# Step 6: Validate
# ---------------------------------------------------------------------------


def run_validator() -> bool:
    validate_script = REPO_ROOT / "tools" / "spec-ci" / "validate.py"
    if not validate_script.exists():
        print("  ⚠ validate.py not found; skipping validation.")
        return True
    result = subprocess.run(
        [sys.executable, str(validate_script)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("  ✓ specs validation passed")
        return True
    else:
        print(f"  ✗ specs validation failed:\n{result.stdout}\n{result.stderr}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap a new project from meta-template.")
    parser.add_argument("--config", required=True, help="Path to bootstrap.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)

    config = _load_yaml(config_path)
    dry_run = args.dry_run

    prefix = "[DRY RUN] " if dry_run else ""

    print(f"\n{'='*60}")
    print(f"  {prefix}KX Platform Bootstrap")
    print(f"{'='*60}\n")
    print(f"  Project: {config['project']['name']}")
    print(f"  Org:     {config['project']['org']}")
    print(f"  Seed:    {config.get('seed', 'auth')}")
    print(f"  Domains: {len(config.get('domains', []))} additional")
    print()

    # Step 1: Validate config
    print("Step 1: Validating configuration...")
    validate_config(config)

    # Step 2: Parameterized replacements
    print("\nStep 2: Applying parameterized replacements...")
    changed = apply_parameterized_replacements(config, dry_run)
    for f in changed:
        print(f"  {prefix}→ {f}")
    if not changed:
        print("  (no replacements needed)")

    # Step 3: Seed adoption
    print(f"\nStep 3: Seed adoption ({config.get('seed', 'auth')})...")
    if config.get("seed") == "none":
        removed = adopt_seed(config, dry_run)
        for f in removed:
            print(f"  {prefix}✗ removed {f}")
    else:
        print("  ✓ Auth seed retained")

    # Step 4: Domain scaffolding
    print("\nStep 4: Scaffolding additional domains...")
    created = scaffold_domains(config, dry_run)
    for f in created:
        print(f"  {prefix}+ {f}")
    if not created:
        print("  (no additional domains)")

    # Step 5: Clean placeholders
    print("\nStep 5: Cleaning placeholders and stale artifacts...")
    cleaned = clean_placeholders(dry_run)
    for f in cleaned:
        print(f"  {prefix}✗ {f}")
    if not cleaned:
        print("  (nothing to clean)")

    # Step 6: Validate
    if not dry_run:
        print("\nStep 6: Running spec validator...")
        if not run_validator():
            print("\n⚠ Bootstrap completed with validation errors. Review and fix manually.")
            sys.exit(1)
    else:
        print("\nStep 6: [DRY RUN] Skipping validation.")

    # Summary
    print(f"\n{'='*60}")
    print(f"  {prefix}Bootstrap complete!")
    print(f"{'='*60}")

    remaining = []
    if config.get("repos", {}).get("frontendMobile") in (None, "", "CHANGE_ME"):
        remaining.append("- Set frontendMobile repo URL (if needed)")
    if not config.get("tech"):
        remaining.append("- Define tech stack in bootstrap.yaml for code conventions and gate mapping")
    remaining.append("- Create initial delta file for project baseline")
    remaining.append("- Review and customize Auth seed business values/capabilities (if retained)")
    remaining.append("- Add project-specific ADRs as needed")

    if remaining:
        print("\n  Remaining manual steps:")
        for r in remaining:
            print(f"    {r}")
    print()


if __name__ == "__main__":
    main()
