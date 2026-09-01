#!/usr/bin/env python3
"""Verify a reality-grounding Skill installation and its record validator."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED = (
    "SKILL.md",
    "agents/openai.yaml",
    "references/active-inquiry.md",
    "references/evaluation-cases.md",
    "references/reality-record-contract.md",
    "scripts/validate_reality_record.py",
)
FORBIDDEN_INTERNAL = (
    "$reality" + "-strategy",
    "usage" + "_id",
    "Bono" + " Insight",
)


def valid_record() -> dict:
    return {
        "decision": {
            "question": "Can the user act with the current access?",
            "desired_outcome": "Choose an executable next step.",
            "unacceptable_downside": "Do not assume unavailable access.",
        },
        "claims": [
            {
                "id": "C1",
                "statement": "The current source opened read-only.",
                "status": "direct_observation",
                "source": {
                    "type": "local check",
                    "reference": "current source status",
                    "observed_at": "2026-09-01",
                    "scope": "current test fixture",
                },
            }
        ],
        "constraints": [
            {
                "id": "K1",
                "type": "access",
                "status": "verified",
                "description": "Current access is read-only.",
            }
        ],
        "gaps": [
            {
                "id": "G1",
                "question": "Does the source cover the required period?",
                "decision_branch": "Use this source or choose another.",
                "impact": "high",
                "changes_decision": True,
                "status": "resolved",
                "answer_branches": [
                    {"if": "covered", "then": "use the source"},
                    {"if": "not covered", "then": "choose another source"},
                ],
                "constraint_ids": [],
            }
        ],
        "proposed_actions": [
            {
                "action": "Use the checked read-only source.",
                "actor": "user",
                "required_conditions": ["read-only access remains active"],
                "evidence_ids": ["C1"],
                "resolved_gap_ids": ["G1"],
                "completion_state": "The required period is available.",
                "stop_condition": "Stop if access changes.",
                "fallback": "Choose another authorised source.",
            }
        ],
        "stop": {
            "status": "ready",
            "reason": "Access and coverage were checked.",
            "remaining_material_gap_ids": [],
        },
    }


def load_validator(skill: Path):
    path = skill / "scripts" / "validate_reality_record.py"
    spec = importlib.util.spec_from_file_location("reality_record_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load record validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(skill: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (skill / relative).is_file():
            errors.append(f"missing file: {relative}")
    if errors:
        return errors
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\n") or "name: reality-grounding" not in text:
        errors.append("SKILL.md frontmatter is invalid")
    refs = set(re.findall(r"`((?:references|scripts)/[^`]+)`", text))
    for relative in sorted(refs):
        if not (skill / relative).is_file():
            errors.append(f"broken local reference: {relative}")
    for path in skill.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".py", ".yaml", ".yml"}:
            body = path.read_text(encoding="utf-8")
            for term in FORBIDDEN_INTERNAL:
                if term in body:
                    errors.append(f"internal dependency remains in {path.relative_to(skill)}")
    if errors:
        return errors
    validator = load_validator(skill)
    good = valid_record()
    if validator.validate(good):
        errors.append("record validator rejected the valid fixture")
    bad = json.loads(json.dumps(good))
    bad["constraints"][0]["status"] = "unknown"
    bad_errors = validator.validate(bad)
    if "unknown material constraint is not tracked by a gap: K1" not in bad_errors:
        errors.append("record validator failed to reject an untracked unknown constraint")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill-path", type=Path, default=ROOT / "reality-grounding"
    )
    args = parser.parse_args()
    skill = args.skill_path.expanduser().resolve()
    errors = verify(skill)
    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1
    print("PASS skill_files")
    print("PASS local_references")
    print("PASS standalone_boundary")
    print("PASS record_validator")
    print("PASS reality-grounding verification complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
