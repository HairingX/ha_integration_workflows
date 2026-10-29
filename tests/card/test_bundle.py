"""Tests of the bundle a card's release carries."""

import json
from pathlib import Path

import pytest

from bundle import check, filename, filename_error, main


def _card(root: Path, *, name: object = "demo-card.js", bundle: str | None = 'const v="1.2.3";') -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "hacs.json").write_text(json.dumps({"name": "Demo", "filename": name}), "utf-8")
    if bundle is not None:
        (root / "dist").mkdir()
        (root / "dist" / "demo-card.js").write_text(bundle, "utf-8")
    return root


def test_the_bundle_is_the_file_hacs_json_names(tmp_path: Path) -> None:
    assert filename(_card(tmp_path)) == "demo-card.js"


@pytest.mark.parametrize("name", [None, "", 3, "dist/demo-card.js", "demo-card.ts", ".js", "a\\b.js"])
def test_a_name_hacs_cannot_find_as_a_module_is_refused(name: object) -> None:
    assert filename_error(name) is not None


def test_a_hacs_json_without_a_bundle_is_refused(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="must name the bundle"):
        filename(_card(tmp_path, name=None))


@pytest.mark.parametrize("bundle", ['x="1.2.3"', "x='1.2.3'", "x=`1.2.3`", 'console.info("%c CARD %c 1.2.3 ")'])
def test_a_bundle_holding_the_version_is_accepted(tmp_path: Path, bundle: str) -> None:
    assert check(_card(tmp_path, bundle=bundle), "1.2.3") == Path("dist/demo-card.js")


def test_a_bundle_holding_another_version_is_refused(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="does not hold the version '1.2.3'"):
        check(_card(tmp_path, bundle='x="0.0.0";y=11.2.3;z="1.2.3rc1";w=1.2.3.4'), "1.2.3")


@pytest.mark.parametrize("bundle", [None, ""])
def test_a_build_that_wrote_no_bundle_is_refused(tmp_path: Path, bundle: str | None) -> None:
    root = _card(tmp_path, bundle=bundle)
    if bundle is None:
        (root / "dist").mkdir()
    with pytest.raises(SystemExit, match="wrote no dist/demo-card.js"):
        check(root, "1.2.3")


def test_the_command_line_prints_the_name_and_the_checked_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _card(tmp_path)
    main(["filename", str(root)])
    main(["check", str(root), "1.2.3"])
    assert capsys.readouterr().out == "demo-card.js\ndist/demo-card.js\n"
    with pytest.raises(SystemExit):
        main([])
