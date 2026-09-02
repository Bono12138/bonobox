#!/usr/bin/env python3
"""Build a deterministic public ZIP for the paired reality Skills."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
VERSION = "0.5.0"
FILES = (
    "README.md",
    "QUICKSTART.md",
    "PROMPT-CARD.md",
    "LICENSE",
    "install.py",
    "verify.py",
    "docs/TEST-REPORT.md",
    "docs/evaluations/20260902-v0.5.0-blind-tests.md",
    "docs/reality-grounding-share-card.png",
    "reality-grounding/SKILL.md",
    "reality-grounding/agents/openai.yaml",
    "reality-grounding/references/active-inquiry.md",
    "reality-grounding/references/evaluation-cases.md",
    "reality-grounding/references/reality-record-contract.md",
    "reality-grounding/scripts/validate_reality_record.py",
    "reality-strategy/SKILL.md",
    "reality-strategy/agents/openai.yaml",
    "reality-strategy/references/evaluation-cases.md",
    "reality-strategy/references/political-strategy-patterns.md",
    "reality-strategy/references/power-shifting-moves.md",
    "reality-strategy/references/stakeholder-map.md",
    "reality-strategy/references/strategy-case-contract.md",
    "reality-strategy/references/streetwise-patterns.md",
)


def main() -> int:
    DIST.mkdir(exist_ok=True)
    output = DIST / f"bonobox-reality-skills-v{VERSION}.zip"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in FILES:
            path = ROOT / relative
            if not path.is_file():
                raise FileNotFoundError(relative)
            info = zipfile.ZipInfo(f"reality-skills-v{VERSION}/{relative}")
            info.date_time = (2026, 9, 2, 0, 0, 0)
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
