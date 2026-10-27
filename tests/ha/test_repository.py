"""Tests of what the workflows read from an integration's repository."""

import json
from pathlib import Path

import pytest

from repository import domain, integration, zip_name


def _repository(root: Path) -> Path:
    (root / "custom_components" / "demo").mkdir(parents=True)
    (root / "custom_components" / "__pycache__").mkdir()
    (root / "custom_components" / "demo" / "manifest.json").write_text(
        json.dumps({"domain": "demo", "version": "0.0.0"}), "utf-8"
    )
    (root / "hacs.json").write_text(
        json.dumps({"name": "Demo", "zip_release": True, "filename": "demo.zip"}), "utf-8"
    )
    return root


def test_the_integration_is_the_one_directory_under_custom_components(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    assert integration(root) == root / "custom_components" / "demo"
    assert domain(root) == "demo"


def test_two_integrations_are_refused(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    (root / "custom_components" / "other").mkdir()
    with pytest.raises(SystemExit, match="exactly one integration, found demo, other"):
        integration(root)


def test_a_manifest_naming_another_domain_is_refused(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    (root / "custom_components" / "demo" / "manifest.json").write_text('{"domain": "x"}', "utf-8")
    with pytest.raises(SystemExit, match="domain is 'x', not 'demo'"):
        domain(root)


def test_the_zip_is_the_one_hacs_installs(tmp_path: Path) -> None:
    assert zip_name(_repository(tmp_path)) == "demo.zip"


def test_a_repository_hacs_installs_from_a_branch_is_refused(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    (root / "hacs.json").write_text('{"name": "Demo"}', "utf-8")
    with pytest.raises(SystemExit, match="zip_release"):
        zip_name(root)
