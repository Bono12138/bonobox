from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


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
build_release = load("rg_build_release", ROOT / "scripts" / "build_release.py")


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

    def test_paired_install_preflights_both_destinations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            strategy = root / "reality-strategy"
            strategy.mkdir()
            (strategy / "SKILL.md").write_text("different", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                installer.install_all(root)
            self.assertFalse((root / "reality-grounding").exists())

    def test_release_zip_matches_current_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp)
            with patch.object(build_release, "DIST", output_root):
                self.assertEqual(0, build_release.main())
            archive_path = output_root / "bonobox-reality-skills-v0.5.0.zip"
            with zipfile.ZipFile(archive_path) as archive:
                for relative in build_release.FILES:
                    archived = archive.read(
                        f"reality-skills-v0.5.0/{relative}"
                    )
                    self.assertEqual((ROOT / relative).read_bytes(), archived)

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

        self.assertIn("Capability version: `0.4.0`", skill)
        self.assertIn("ask first", skill)
        self.assertIn("ordinary observation", skill)
        self.assertIn("Find the blocked transition", skill)
        self.assertIn("Giving advice is not completion", skill)
        self.assertIn("A — original result", skill)
        self.assertIn("stated scale, resources already available", skill)
        self.assertIn("outspoken people", inquiry)
        self.assertIn("My office manager's feet smell", cases)
        self.assertIn("staged peer conversation", cases)
        self.assertIn("Case 10: The proposed route may not be the original problem", cases)

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

        self.assertIn("Capability version: `1.2.0`", skill)
        self.assertIn("Keep the goal and value judgment with the user", skill)
        self.assertIn("Reconstruct the object and relationship chain first", skill)
        self.assertIn("Actual object and relationship chain", skill)
        self.assertIn("Write the attack-defence conversion", skill)
        self.assertIn("If the other actor does nothing", skill)
        self.assertIn("Borrow independent content", patterns)
        self.assertIn("Overhearing is lossy", patterns)
        self.assertIn("RS-09: the confused training relocation", cases)
        self.assertIn("reconstruct participants, locations, resources", cases)
        self.assertIn("published plan from the actual", cases)
        self.assertIn("missing condition", cases)


if __name__ == "__main__":
    unittest.main()
