#!/usr/bin/env python3
"""Install the bundled reality Skills without overwriting local work."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SKILLS = ("reality-grounding", "reality-strategy")


def tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(p for p in path.rglob("*") if p.is_file()):
        if "__pycache__" in item.parts or item.suffix == ".pyc":
            continue
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def target_root(name: str) -> Path:
    home = Path.home()
    if name == "agents":
        return home / ".agents" / "skills"
    if name == "codex":
        codex_home = Path(os.environ.get("CODEX_HOME", home / ".codex"))
        return codex_home / "skills"
    if name == "claude":
        return home / ".claude" / "skills"
    raise ValueError(name)


def install(root: Path, skill_name: str) -> Path:
    if skill_name not in SKILLS:
        raise ValueError(f"unknown Skill: {skill_name}")
    source = ROOT / skill_name
    destination = root.expanduser().resolve() / skill_name
    if not source.is_dir():
        raise RuntimeError(f"bundled Skill not found: {source}")
    if destination.exists():
        if destination.is_dir() and tree_digest(destination) == tree_digest(source):
            print(f"PASS already_installed={destination}")
            return destination
        raise FileExistsError(
            f"target already exists and differs: {destination}; compare it before replacing"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    if tree_digest(destination) != tree_digest(source):
        raise RuntimeError("installed Skill does not match the bundled source")
    print(f"PASS installed={destination}")
    return destination


def install_all(root: Path) -> list[Path]:
    installed: list[Path] = []
    for skill_name in SKILLS:
        installed.append(install(root, skill_name))
    return installed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target", choices=("agents", "codex", "claude"), default="agents"
    )
    parser.add_argument(
        "--path", type=Path, help="custom Skill root; both Skills are created inside it"
    )
    parser.add_argument(
        "--skill", choices=SKILLS, help="install only one Skill instead of the pair"
    )
    args = parser.parse_args()
    root = args.path if args.path else target_root(args.target)
    try:
        if args.skill:
            install(root, args.skill)
        else:
            install_all(root)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
