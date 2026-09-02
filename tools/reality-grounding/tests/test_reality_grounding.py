from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


installer = load("rg_installer", ROOT / "install.py")
verifier = load("rg_verifier", ROOT / "verify.py")
validator = load(
    "rg_validator",
    ROOT / "reality-grounding" / "scripts" / "validate_reality_record.py",
)


class RealityGroundingPublicTests(unittest.TestCase):
    def test_source_package_verifies(self) -> None:
        self.assertEqual([], verifier.verify(ROOT / "reality-grounding"))
        self.assertEqual([], verifier.verify_strategy(ROOT / "reality-strategy"))

    def test_installer_copies_and_verifies_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destinations = installer.install_all(Path(tmp))
            self.assertEqual([], verifier.verify(destinations[0]))
            self.assertEqual([], verifier.verify_strategy(destinations[1]))
            self.assertEqual(destinations, installer.install_all(Path(tmp)))

    def test_installer_refuses_to_overwrite_changed_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = installer.install(Path(tmp), "reality-grounding")
            (destination / "SKILL.md").write_text("changed", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                installer.install(Path(tmp), "reality-grounding")

    def test_valid_record_passes(self) -> None:
        self.assertEqual([], validator.validate(verifier.valid_record()))

    def test_unknown_constraint_is_rejected(self) -> None:
        record = verifier.valid_record()
        record["constraints"][0]["status"] = "unknown"
        self.assertIn(
            "unknown material constraint is not tracked by a gap: K1",
            validator.validate(record),
        )

    def test_ready_state_rejects_open_high_gap(self) -> None:
        record = verifier.valid_record()
        gap = record["gaps"][0]
        gap["status"] = "open"
        gap["next_action"] = {
            "kind": "inspect-existing-evidence",
            "target": "available period",
            "reason": "The answer changes the source choice.",
        }
        self.assertIn(
            "ready record still has open critical or high-impact gaps",
            validator.validate(record),
        )

    def test_skill_requires_inquiry_before_premature_advice(self) -> None:
        skill = (ROOT / "reality-grounding" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        inquiry = (
            ROOT / "reality-grounding" / "references" / "active-inquiry.md"
        ).read_text(encoding="utf-8")
        cases = (
            ROOT / "reality-grounding" / "references" / "evaluation-cases.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Standalone version: `0.3.0`", skill)
        self.assertIn("ask first", skill)
        self.assertIn("ordinary observation", skill)
        self.assertIn("Find the blocked transition", skill)
        self.assertIn("Giving advice is not completion", skill)
        self.assertIn("outspoken people", inquiry)
        self.assertIn("My office manager's feet smell", cases)
        self.assertIn("staged peer conversation", cases)

    def test_strategy_searches_for_streetwise_routes(self) -> None:
        skill = (ROOT / "reality-strategy" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        patterns = (
            ROOT / "reality-strategy" / "references" / "streetwise-patterns.md"
        ).read_text(encoding="utf-8")
        cases = (
            ROOT / "reality-strategy" / "references" / "evaluation-cases.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Capability version: `0.3.0`", skill)
        self.assertIn("Find the transition that is actually blocked", skill)
        self.assertIn("Inventory the means already at hand", skill)
        self.assertIn("non-obvious but still plausible", skill)
        self.assertIn("current arrangement gives", skill)
        self.assertIn("Borrow independent content", patterns)
        self.assertIn("Overhearing is lossy", patterns)
        self.assertIn("neighbour noise", cases)
        self.assertIn("information carrier fails", cases)


if __name__ == "__main__":
    unittest.main()
