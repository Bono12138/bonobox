from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".ps1", ".txt", ".yaml", ".yml", ".json", ".svg"}
SKIP_PARTS = {".git", ".local", "__pycache__"}
ALLOWED_HOSTS = {
    "example.invalid", "github.com", "localhost", "requests.readthedocs.io",
    "superset.apache.org", "www.w3.org",
}
PATTERNS = {
    "email address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "private IPv4 address": re.compile(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"),
    "local user path": re.compile(
        r"(?:/" + "Users/" + r"[^/\s]+|[A-Z]:\\" + "Users\\" + r"[^\\\s]+)",
        re.I,
    ),
    "embedded credential assignment": re.compile(r"(?im)^\s*(?:password|passwd|token|secret|api_key)\s*[:=]\s*['\"][^'\"]{4,}['\"]\s*$"),
}
URL_PATTERN = re.compile(r"https?://[^\s)\]>'\"]+", re.I)


def candidates() -> list[Path]:
    return [
        path for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in TEXT_SUFFIXES
        and not (set(path.parts) & SKIP_PARTS)
    ]


def local_rules() -> list[re.Pattern[str]]:
    rules_path = os.environ.get("BONOBOX_PUBLIC_AUDIT_RULES", "").strip()
    if not rules_path:
        return []
    target = Path(rules_path).expanduser().resolve()
    if target == ROOT or ROOT in target.parents:
        raise RuntimeError("Local audit rules must stay outside the public repository.")
    return [
        re.compile(re.escape(line.strip()), re.I)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    failures: list[str] = []
    rules = local_rules()
    paths = candidates()
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                failures.append(f"{path.relative_to(ROOT)}:{line}: {label}")
        for match in URL_PATTERN.finditer(text):
            host = (urlparse(match.group(0)).hostname or "").casefold()
            if host not in ALLOWED_HOSTS and not host.endswith(".github.com"):
                line = text.count("\n", 0, match.start()) + 1
                failures.append(f"{path.relative_to(ROOT)}:{line}: non-public URL host")
        for rule in rules:
            for match in rule.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                failures.append(f"{path.relative_to(ROOT)}:{line}: local denylist match")

    runtime_names = {".env", "credential.dpapi", "manifest.json", "profile.json", "query.sql", "result.csv", "session.dpapi"}
    for path in ROOT.rglob("*"):
        if path.is_file() and not (set(path.parts) & SKIP_PARTS) and path.name.casefold() in runtime_names:
            failures.append(f"{path.relative_to(ROOT)}: tracked or packaged runtime data")

    if failures:
        print("PUBLIC AUDIT FAILED")
        print("\n".join(failures))
        return 1
    print(f"PUBLIC AUDIT PASS files={len(paths)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
