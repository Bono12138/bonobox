#!/usr/bin/env python3
"""Build a deterministic public ZIP for the standalone Skill."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
VERSION = "0.2.0"
FILES = (
    "README.md",
    "QUICKSTART.md",
    "PROMPT-CARD.md",
    "LICENSE",
    "install.py",
    "verify.py",
    "docs/TEST-REPORT.md",
    "docs/reality-grounding-share-card.png",
    "reality-grounding/SKILL.md",
    "reality-grounding/agents/openai.yaml",
    "reality-grounding/references/active-inquiry.md",
    "reality-grounding/references/evaluation-cases.md",
    "reality-grounding/references/reality-record-contract.md",
    "reality-grounding/scripts/validate_reality_record.py",
)


def main() -> int:
    DIST.mkdir(exist_ok=True)
    output = DIST / f"bonobox-reality-grounding-v{VERSION}.zip"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in FILES:
            path = ROOT / relative
            if not path.is_file():
                raise FileNotFoundError(relative)
            info = zipfile.ZipInfo(f"reality-grounding-v{VERSION}/{relative}")
            info.date_time = (2026, 9, 1, 0, 0, 0)
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    checksum = output.with_suffix(output.suffix + ".sha256")
    checksum.write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(output)
    print(checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
