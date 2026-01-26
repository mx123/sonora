#!/usr/bin/env python3

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _fail(msg: str) -> None:
    print(f"ERROR: {msg}")
    raise SystemExit(1)


def _run(args: list[str]) -> None:
    proc = subprocess.run(args, text=True)
    if proc.returncode != 0:
        _fail(f"Command failed (exit={proc.returncode}): {' '.join(args)}")


def _clean_dir(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return

    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def main() -> int:
    workspace = REPO_ROOT / "specs" / "architecture" / "structurizr" / "workspace.dsl"
    out_dir = REPO_ROOT / "docs" / "derived" / "structurizr"

    if not workspace.exists():
        _fail(f"Missing Structurizr workspace: {workspace.relative_to(REPO_ROOT)}")

    docker = shutil.which("docker")
    if not docker:
        _fail("Docker is required to run structurizr/cli (docker not found in PATH)")

    _clean_dir(out_dir)

    # Structurizr CLI exports text-based diagrams deterministically.
    # We export Mermaid diagrams only (no workspace JSON in derived).
    _run(
        [
            docker,
            "run",
            "--rm",
            "-v",
            f"{REPO_ROOT}:/workspace",
            "-w",
            "/workspace",
            "structurizr/cli:latest",
            "export",
            "-w",
            str(workspace.relative_to(REPO_ROOT)),
            "-f",
            "mermaid",
            "-o",
            str(out_dir.relative_to(REPO_ROOT)),
        ]
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
