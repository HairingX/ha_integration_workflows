"""Tests of what every card's repository promises."""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from card_contract import SCRIPTS, check, check_hacs, check_lock, check_package, main

PACKAGE: dict[str, Any] = {
    "name": "demo-card",
    "version": "0.0.0",
    "private": True,
    "type": "module",
    "scripts": {
        "lint": "eslint . && prettier --check .",
        "typecheck": "tsc --noEmit",
        "test": "vitest run --coverage",
        "build": "vite build",
    },
}
LOCK: dict[str, Any] = {"name": "demo-card", "version": "0.0.0", "lockfileVersion": 3, "packages": {"": {"version": "0.0.0"}}}
HACS: dict[str, Any] = {"name": "Demo card", "filename": "demo-card.js", "homeassistant": "2026.1.0"}


def _card(root: Path, *, package: dict[str, Any] = PACKAGE, lock: dict[str, Any] | None = LOCK, hacs: dict[str, Any] = HACS) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "package.json").write_text(json.dumps(package), "utf-8")
    if lock is not None:
        (root / "package-lock.json").write_text(json.dumps(lock), "utf-8")
    (root / "hacs.json").write_text(json.dumps(hacs), "utf-8")
    (root / ".gitignore").write_text("node_modules/\ndist/\n", "utf-8")
    (root / "dist").mkdir()
    (root / "dist" / "demo-card.js").write_text("built", "utf-8")
    return root


def test_a_card_to_the_standard_breaks_no_promise(tmp_path: Path) -> None:
    assert check(_card(tmp_path)) == []


def test_package_json_says_0_0_0_and_has_every_script_the_tests_run() -> None:
    assert list(check_package({"version": "1.2.3", "scripts": {"lint": "eslint .", "test": " "}})) == [
        "package.json says version '1.2.3'; it must say '0.0.0'",
        "package.json must have the script 'typecheck', which the tests run",
        "package.json must have the script 'test', which the tests run",
        "package.json must have the script 'build', which the tests run",
    ]
    assert SCRIPTS == ("lint", "typecheck", "test", "build")


def test_package_json_without_scripts_is_told_every_one() -> None:
    assert len(list(check_package({"version": "0.0.0"}))) == len(SCRIPTS)


@pytest.mark.parametrize(
    ("lock", "errors"),
    [
        (None, ["package-lock.json is missing; npm ci installs exactly what it locks"]),
        ({"lockfileVersion": 3}, []),
        ({"version": "1.0.0", "packages": {"": {"version": "1.0.0"}}}, ["package-lock.json says version '1.0.0'; run npm install after setting package.json's"]),
        ({"version": "0.0.0", "packages": {"": {"version": "0.1.0"}}}, ["package-lock.json says version '0.1.0'; run npm install after setting package.json's"]),
    ],
)
def test_the_lock_is_committed_and_says_0_0_0(lock: dict[str, Any] | None, errors: list[str]) -> None:
    assert list(check_lock(lock)) == errors


def test_every_way_hacs_json_can_be_wrong_is_reported() -> None:
    assert list(check_hacs({"name": " ", "filename": "dist/x.js", "homeassistant": "soon", "zip_release": False, "content_in_root": True})) == [
        "hacs.json must give the card's name in name",
        "hacs.json names the bundle 'dist/x.js'; it must be a file name ending in .js, without a directory",
        "hacs.json must give the oldest Home Assistant the card supports in homeassistant, such as '2026.1.0'",
        "hacs.json must not set zip_release; HACS installs the bundle itself, not a zip",
        "hacs.json must not set content_in_root; HACS would not install the bundle the release carries",
    ]


@pytest.mark.parametrize("minimum", [None, 2026])
def test_the_oldest_home_assistant_is_given_as_a_version_string(minimum: object) -> None:
    hacs = {**HACS, "homeassistant": minimum}
    assert len(list(check_hacs(hacs))) == 1


def test_a_committed_bundle_is_refused(tmp_path: Path) -> None:
    root = _card(tmp_path)
    subprocess.run(["git", "-C", str(root), "add", "-f", "dist/demo-card.js"], check=True)
    assert check(root) == ["dist/demo-card.js is committed; dist/ is built, and must be in .gitignore"]


def test_the_command_line_reports_every_broken_promise(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main([str(_card(tmp_path / "bad", package={**PACKAGE, "version": "1.0.0"}))])
    assert "::error::package.json says version '1.0.0'" in capsys.readouterr().out
    main([str(_card(tmp_path / "good"))])
    assert "Every promise of the repository holds." in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main([])
