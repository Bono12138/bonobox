import hashlib
import json
import zipfile

import pytest

from scripts.build_release import ReleaseValidationError, build_release, validate_text


def test_validate_text_rejects_secret_and_local_path_patterns():
    cases = [
        ("API_TOKEN=example", "credential-like assignment"),
        (r"C:\Users\someone\project", "local user path"),
        ("-----BEGIN PRIVATE KEY-----", "private key"),
        ("https://user:password@example.com", "credentialed URL"),
    ]

    for text, expected_reason in cases:
        assert expected_reason in validate_text(text)


def test_validate_text_allows_documented_no_key_statement_and_placeholders():
    text = "No API key is required. Use C:\\path\\to\\portable-search and YOUR_VALUE."

    assert validate_text(text) == []


def test_build_release_contains_only_allowlisted_files_and_manifest(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("Safe guide", encoding="utf-8")
    (project / "run.py").write_text("print('safe')", encoding="utf-8")
    (project / "ignored.env").write_text("TOKEN=secret", encoding="utf-8")
    output = tmp_path / "release.zip"

    build_release(project, output, package_files=["README.md", "run.py"], version="2.0.0")

    with zipfile.ZipFile(output) as archive:
        assert archive.namelist() == ["MANIFEST.json", "README.md", "run.py"]
        manifest = json.loads(archive.read("MANIFEST.json"))
        assert manifest["version"] == "2.0.0"
        assert [item["path"] for item in manifest["files"]] == ["README.md", "run.py"]
        assert manifest["files"][0]["sha256"] == hashlib.sha256(b"Safe guide").hexdigest()


def test_build_release_is_reproducible(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("Same content", encoding="utf-8")
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    build_release(project, first, package_files=["README.md"], version="2.0.0")
    build_release(project, second, package_files=["README.md"], version="2.0.0")

    assert first.read_bytes() == second.read_bytes()


def test_build_release_rejects_unsafe_allowlisted_file(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text(r"C:\Users\someone\secret", encoding="utf-8")

    with pytest.raises(ReleaseValidationError, match="README.md"):
        build_release(
            project,
            tmp_path / "release.zip",
            package_files=["README.md"],
            version="2.0.0",
        )


def test_build_release_rejects_missing_or_parent_relative_entries(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(ReleaseValidationError):
        build_release(
            project,
            tmp_path / "release.zip",
            package_files=["../outside.txt"],
            version="2.0.0",
        )
