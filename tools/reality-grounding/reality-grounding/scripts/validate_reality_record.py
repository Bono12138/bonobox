#!/usr/bin/env python3
"""Validate a reality record before strategy begins."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CLAIM_STATES = {
    "verified_fact", "direct_observation", "user_report", "formal_rule",
    "observed_practice", "supported_inference", "working_hypothesis", "unknown",
}
SOURCE_REQUIRED = {
    "verified_fact", "direct_observation", "user_report", "formal_rule",
    "observed_practice",
}
CONSTRAINT_TYPES = {
    "authority", "access", "time", "resource", "cooperation", "rule", "risk",
}
CONSTRAINT_STATES = {"verified", "reported", "unknown"}
GAP_IMPACTS = {"critical", "high", "medium", "low"}
GAP_STATES = {"open", "resolved", "deferred", "blocked"}
INQUIRY_KINDS = {
    "inspect-existing-evidence", "use-approved-tool", "observe-real-work",
    "run-reversible-probe", "ask-targeted-question", "proceed-with-assumption",
    "blocked-by-permission",
}
STOP_STATES = {"ready", "ask-user", "proceed-with-assumptions", "blocked"}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def duplicate_ids(items: list[dict[str, Any]]) -> set[str]:
    ids = [item.get("id") for item in items if nonempty(item.get("id"))]
    return {item_id for item_id in ids if ids.count(item_id) > 1}


def validate(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    decision = record.get("decision")
    if not isinstance(decision, dict):
        errors.append("decision must be an object")
    else:
        for field in ("question", "desired_outcome", "unacceptable_downside"):
            if not nonempty(decision.get(field)):
                errors.append(f"decision.{field} is required")

    claims = record.get("claims", [])
    if not isinstance(claims, list):
        errors.append("claims must be a list")
        claims = []
    claim_ids = {item.get("id") for item in claims if isinstance(item, dict)}
    for duplicate in sorted(duplicate_ids([x for x in claims if isinstance(x, dict)])):
        errors.append(f"duplicate claim id: {duplicate}")
    for index, claim in enumerate(claims):
        prefix = f"claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if not nonempty(claim.get("id")):
            errors.append(f"{prefix}.id is required")
        if not nonempty(claim.get("statement")):
            errors.append(f"{prefix}.statement is required")
        state = claim.get("status")
        if state not in CLAIM_STATES:
            errors.append(f"{prefix}.status is invalid")
        if state in SOURCE_REQUIRED:
            source = claim.get("source")
            if not isinstance(source, dict):
                errors.append(f"{prefix}.source is required for {state}")
            else:
                for field in ("type", "reference", "observed_at", "scope"):
                    if not nonempty(source.get(field)):
                        errors.append(f"{prefix}.source.{field} is required")
        if state in {"supported_inference", "working_hypothesis"}:
            supports = claim.get("supporting_claim_ids", [])
            if not isinstance(supports, list) or not supports:
                errors.append(f"{prefix}.supporting_claim_ids is required for {state}")
            else:
                for claim_id in supports:
                    if claim_id not in claim_ids:
                        errors.append(f"{prefix} references unknown claim id: {claim_id}")

    constraints = record.get("constraints", [])
    if not isinstance(constraints, list):
        errors.append("constraints must be a list")
        constraints = []
    unknown_constraint_ids: set[str] = set()
    for index, constraint in enumerate(constraints):
        prefix = f"constraints[{index}]"
        if not isinstance(constraint, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if not nonempty(constraint.get("id")):
            errors.append(f"{prefix}.id is required")
        if constraint.get("type") not in CONSTRAINT_TYPES:
            errors.append(f"{prefix}.type is invalid")
        if constraint.get("status") not in CONSTRAINT_STATES:
            errors.append(f"{prefix}.status is invalid")
        if not nonempty(constraint.get("description")):
            errors.append(f"{prefix}.description is required")
        if constraint.get("status") == "unknown" and nonempty(constraint.get("id")):
            unknown_constraint_ids.add(constraint["id"])

    gaps = record.get("gaps", [])
    if not isinstance(gaps, list):
        errors.append("gaps must be a list")
        gaps = []
    gap_ids = {item.get("id") for item in gaps if isinstance(item, dict)}
    tracked_constraint_ids: set[str] = set()
    for duplicate in sorted(duplicate_ids([x for x in gaps if isinstance(x, dict)])):
        errors.append(f"duplicate gap id: {duplicate}")
    for index, gap in enumerate(gaps):
        prefix = f"gaps[{index}]"
        if not isinstance(gap, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in ("id", "question", "decision_branch"):
            if not nonempty(gap.get(field)):
                errors.append(f"{prefix}.{field} is required")
        impact = gap.get("impact")
        state = gap.get("status")
        if impact not in GAP_IMPACTS:
            errors.append(f"{prefix}.impact is invalid")
        if state not in GAP_STATES:
            errors.append(f"{prefix}.status is invalid")
        if gap.get("changes_decision") is not True and impact in {"critical", "high"}:
            errors.append(f"{prefix} is material but does not declare decision change")
        branches = gap.get("answer_branches", [])
        if impact in {"critical", "high"} or gap.get("changes_decision") is True:
            if not isinstance(branches, list) or len(branches) < 2:
                errors.append(f"{prefix}.answer_branches needs at least two branches")
            else:
                for branch_index, branch in enumerate(branches):
                    if (
                        not isinstance(branch, dict)
                        or not nonempty(branch.get("if"))
                        or not nonempty(branch.get("then"))
                    ):
                        errors.append(
                            f"{prefix}.answer_branches[{branch_index}] needs if and then"
                        )
        action = gap.get("next_action")
        if state in {"open", "blocked"}:
            if not isinstance(action, dict):
                errors.append(f"{prefix}.next_action is required")
            else:
                if action.get("kind") not in INQUIRY_KINDS:
                    errors.append(f"{prefix}.next_action.kind is invalid")
                for field in ("target", "reason"):
                    if not nonempty(action.get(field)):
                        errors.append(f"{prefix}.next_action.{field} is required")
        constraint_ids = gap.get("constraint_ids", [])
        if isinstance(constraint_ids, list):
            tracked_constraint_ids.update(x for x in constraint_ids if isinstance(x, str))

    for constraint_id in sorted(unknown_constraint_ids - tracked_constraint_ids):
        errors.append(f"unknown material constraint is not tracked by a gap: {constraint_id}")

    actions = record.get("proposed_actions", [])
    if not isinstance(actions, list):
        errors.append("proposed_actions must be a list")
        actions = []
    for index, action in enumerate(actions):
        prefix = f"proposed_actions[{index}]"
        if not isinstance(action, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in ("action", "actor", "completion_state", "stop_condition", "fallback"):
            if not nonempty(action.get(field)):
                errors.append(f"{prefix}.{field} is required")
        conditions = action.get("required_conditions")
        if not isinstance(conditions, list) or not conditions:
            errors.append(f"{prefix}.required_conditions must be a non-empty list")
        evidence_ids = action.get("evidence_ids", [])
        resolved_gap_ids = action.get("resolved_gap_ids", [])
        if not evidence_ids and not resolved_gap_ids:
            errors.append(f"{prefix} needs evidence_ids or resolved_gap_ids")
        for claim_id in evidence_ids if isinstance(evidence_ids, list) else []:
            if claim_id not in claim_ids:
                errors.append(f"{prefix} references unknown claim id: {claim_id}")
        for gap_id in resolved_gap_ids if isinstance(resolved_gap_ids, list) else []:
            if gap_id not in gap_ids:
                errors.append(f"{prefix} references unknown gap id: {gap_id}")

    stop = record.get("stop")
    if not isinstance(stop, dict):
        errors.append("stop must be an object")
        return errors
    stop_state = stop.get("status")
    if stop_state not in STOP_STATES:
        errors.append("stop.status is invalid")
    if not nonempty(stop.get("reason")):
        errors.append("stop.reason is required")
    remaining = stop.get("remaining_material_gap_ids", [])
    if not isinstance(remaining, list):
        errors.append("stop.remaining_material_gap_ids must be a list")
        remaining = []
    for gap_id in remaining:
        if gap_id not in gap_ids:
            errors.append(f"stop references unknown gap id: {gap_id}")

    open_material = {
        gap.get("id")
        for gap in gaps
        if isinstance(gap, dict)
        and gap.get("impact") in {"critical", "high"}
        and gap.get("status") in {"open", "blocked"}
    }
    if stop_state == "ready" and open_material:
        errors.append("ready record still has open critical or high-impact gaps")
    if stop_state == "ask-user":
        asks = [
            gap for gap in gaps
            if isinstance(gap, dict)
            and gap.get("status") == "open"
            and isinstance(gap.get("next_action"), dict)
            and gap["next_action"].get("kind") == "ask-targeted-question"
        ]
        if not asks:
            errors.append("ask-user stop requires an open targeted question")
    if stop_state == "blocked":
        blocked = [
            gap for gap in gaps
            if isinstance(gap, dict)
            and gap.get("status") == "blocked"
            and isinstance(gap.get("next_action"), dict)
            and gap["next_action"].get("kind") == "blocked-by-permission"
        ]
        if not blocked:
            errors.append("blocked stop requires a permission-blocked gap")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.record.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    if not isinstance(payload, dict):
        print("INVALID: root must be an object", file=sys.stderr)
        return 1
    errors = validate(payload)
    if errors:
        for error in errors:
            print(f"INVALID: {error}", file=sys.stderr)
        return 1
    print("VALID: reality record is structurally ready for its declared stop state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
