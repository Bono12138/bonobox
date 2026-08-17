from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0-beta.2"
RELEASE_NAME = f"bonobox-superset-query-v{VERSION}"
DIST = ROOT / "dist"
STAGE = DIST / RELEASE_NAME

ALLOWLIST = (
    "README.md",
    "README.en.md",
    "QUICKSTART.md",
    "COMPATIBILITY.md",
    "THIRD_PARTY_NOTICES.md",
    "LICENSE",
    "requirements.txt",
    "install.ps1",
    "verify.ps1",
    "docs/superset-query-hero.svg",
    "docs/TEST-REPORT.md",
    "query-superset/SKILL.md",
    "query-superset/agents/openai.yaml",
    "query-superset/references/capabilities.md",
    "query-superset/scripts/superset_query.py",
    "query-superset/scripts/test_superset_query.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build() -> Path:
    if DIST.exists():
        backup = ROOT / ".local" / "old-dist"
        backup.mkdir(parents=True, exist_ok=True)
        target = backup / f"{RELEASE_NAME}-{len(list(backup.iterdir())) + 1}"
        shutil.move(str(DIST), str(target))

    STAGE.mkdir(parents=True, exist_ok=True)
    for relative in ALLOWLIST:
        source = ROOT / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        destination = STAGE / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    zip_path = DIST / f"{RELEASE_NAME}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(STAGE.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(DIST))

    checksum = DIST / f"{zip_path.name}.sha256"
    checksum.write_text(f"{sha256(zip_path)}  {zip_path.name}\n", encoding="utf-8")
    print(zip_path)
    print(checksum)
    return zip_path


if __name__ == "__main__":
    build()
