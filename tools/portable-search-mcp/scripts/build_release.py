"""Create a deterministic, allowlisted, security-checked release ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

from search_mcp import __version__


class ReleaseValidationError(RuntimeError):
    """Raised when a release file is missing, unsafe, or outside the project."""


PACKAGE_FILES = [
    "README.md",
    "QUICKSTART.md",
    "THIRD_PARTY_NOTICES.md",
    "ddgs-mcp-server.py",
    "install.ps1",
    "requirements.lock.txt",
    "run-server.cmd",
    "smoke_test.py",
    "verify.ps1",
    "docs/SECURITY.md",
    "docs/TEST-REPORT.md",
    "docs/TROUBLESHOOTING.md",
    "docs/benchmark-2026-08-05.json",
    "scripts/benchmark_search.py",
    "search_mcp/__init__.py",
    "search_mcp/search.py",
    "search_mcp/server.py",
]


_CHECKS = [
    (re.compile(r"(?i)(?:api[_-]?token|access[_-]?token|password|secret)\s*[:=]\s*[^\s]+"), "credential-like assignment"),
    (re.compile(r"(?i)\b(?:gho|ghp|github_pat|sk)-[A-Za-z0-9_-]+|\b(?:gho|ghp)_[A-Za-z0-9_]+"), "token-like value"),
    (re.compile(r"(?i)[A-Za-z]:\\Users\\[^\\\s]+|/Users/[^/\s]+"), "local user path"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key"),
    (re.compile(r"(?i)https?://[^/\s:@]+:[^/\s@]+@"), "credentialed URL"),
]

def validate_text(text: str) -> list[str]:
    reasons = [reason for pattern, reason in _CHECKS if pattern.search(text)]
    return sorted(set(reasons))


def build_release(
    project_root: Path,
    output_path: Path,
    *,
    package_files: list[str] = PACKAGE_FILES,
    version: str = __version__,
) -> str:
    project_root = project_root.resolve()
    entries: list[tuple[str, bytes]] = []
    for relative_name in sorted(package_files):
        relative = PurePosixPath(relative_name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ReleaseValidationError(f"Unsafe release entry: {relative_name}")
        source = (project_root / Path(*relative.parts)).resolve()
        try:
            source.relative_to(project_root)
        except ValueError as exc:
            raise ReleaseValidationError(f"Release entry is outside project: {relative_name}") from exc
        if not source.is_file():
            raise ReleaseValidationError(f"Missing release file: {relative_name}")
        data = source.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ReleaseValidationError(f"Non-UTF-8 release file: {relative_name}") from exc
        reasons = validate_text(text)
        if reasons:
            raise ReleaseValidationError(
                f"Unsafe release file {relative_name}: {', '.join(reasons)}"
            )
        entries.append((relative.as_posix(), data))

    manifest = {
        "name": "portable-search-mcp",
        "version": version,
        "files": [
            {
                "path": name,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for name, data in entries
        ],
    }
    manifest_data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        _write_deterministic(archive, "MANIFEST.json", manifest_data)
        for name, data in entries:
            _write_deterministic(archive, name, data)

    return hashlib.sha256(output_path.read_bytes()).hexdigest()


def _write_deterministic(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[1]
    output = args.output or project_root / "dist" / f"portable-search-mcp-v{__version__}.zip"
    sha256 = build_release(project_root, output)
    print(f"PASS release={output}")
    print(f"SHA256={sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
