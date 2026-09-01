#!/usr/bin/env python3
"""Scan public text files for local paths, internal coupling and secret-like values."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", "dist", "__pycache__"}
TEXT_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".txt", ".toml", ".json"}
PATTERNS = {
    "mac_home_path": re.compile(r"/Users/[^/\s]+/"),
    "windows_home_path": re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+\\\\"),
    "internal_workspace": re.compile(r"bono-workbench|Bono Insight|usage_id|\$reality-strategy", re.I),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
}


def main() -> int:
    findings: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP for part in path.parts):
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{name}: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"FAIL {finding}", file=sys.stderr)
        return 1
    print("PASS public_audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
