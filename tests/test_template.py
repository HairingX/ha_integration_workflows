"""Tests of how a repository is kept in agreement with the template."""

from pathlib import Path

import pytest

from template import BEGIN, END, TEMPLATE, differences, files, shared_section, sync


@pytest.fixture
def template(tmp_path: Path) -> Path:
    root = tmp_path / "template"
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "tests.yml").write_text("name: Tests\n", "utf-8")
    (root / ".github" / "release.yml").write_text("changelog: {}\n", "utf-8")
    (root / "CLAUDE.md").write_text("## Shared\n\nThe rules.\n", "utf-8")
    return root


def _repository(root: Path) -> Path:
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "scripts").mkdir()
    (root / ".github" / "scripts" / "old.py").write_text("", "utf-8")
    (root / ".github" / "workflows" / "release-dev.yml").write_text("old\n", "utf-8")
    (root / ".github" / "workflows" / "tests.yml").write_text("name: Old\n", "utf-8")
    (root / "CLAUDE.md").write_text("# Conventions\n\nOur own.\n", "utf-8")
    return root


def test_the_section_is_not_one_of_the_copied_files(template: Path) -> None:
    assert files(template) == [".github/release.yml", ".github/workflows/tests.yml"]


def test_every_difference_is_reported(tmp_path: Path, template: Path) -> None:
    root = _repository(tmp_path / "repository")
    assert list(differences(root, template)) == [
        ".github/release.yml is missing; the template has it",
        ".github/workflows/tests.yml differs from the template's",
        ".github/workflows/release-dev.yml is no workflow of the template; workflows are shared, not added per repository",
        ".github/scripts must not exist; it comes from the template",
        f"CLAUDE.md lacks the shared section between {BEGIN!r} and {END!r}",
    ]


def test_sync_brings_the_repository_into_agreement(tmp_path: Path, template: Path) -> None:
    root = _repository(tmp_path / "repository")
    sync(root, template)
    assert list(differences(root, template)) == []
    assert not (root / ".github" / "workflows" / "release-dev.yml").exists()
    claude = (root / "CLAUDE.md").read_text("utf-8")
    assert claude == f"# Conventions\n\nOur own.\n\n{shared_section(template)}\n"


def test_sync_replaces_an_outdated_section_and_keeps_what_follows(tmp_path: Path, template: Path) -> None:
    root = _repository(tmp_path / "repository")
    (root / "CLAUDE.md").write_text(f"# Own\n\n{BEGIN}\nold\n{END}\n\nAfter.\n", "utf-8")
    assert "the shared section of CLAUDE.md differs from the template's" in list(differences(root, template))
    sync(root, template)
    assert (root / "CLAUDE.md").read_text("utf-8") == f"# Own\n\n{shared_section(template)}\n\nAfter.\n"


def test_the_shared_template_is_complete() -> None:
    assert (TEMPLATE / "CLAUDE.md").is_file()
    assert {path for path in files() if path.startswith(".github/workflows/")} == {
        ".github/workflows/close-inactive-issues.yml",
        ".github/workflows/library-released.yml",
        ".github/workflows/release-drafter.yml",
        ".github/workflows/release.yml",
        ".github/workflows/scorecards.yml",
        ".github/workflows/test-build-cleanup.yml",
        ".github/workflows/test-build.yml",
        ".github/workflows/tests.yml",
        ".github/workflows/validate.yml",
    }
