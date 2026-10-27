"""Tests of what the workflows read from a library's repository."""

from pathlib import Path

import pytest

from package import import_name, name


def _repository(root: Path, *, pyproject: str = '[project]\nname = "demo-lib"\n', packages: tuple[str, ...] = ("demo_lib",)) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(pyproject, "utf-8")
    for package in packages:
        (root / "src" / package).mkdir(parents=True)
        (root / "src" / package / "__init__.py").write_text("", "utf-8")
    return root


def test_the_name_is_the_one_pyproject_states(tmp_path: Path) -> None:
    assert name(_repository(tmp_path)) == "demo-lib"


def test_the_import_name_is_the_one_package_under_src(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    (root / "src" / "demo_lib.egg-info").mkdir()
    assert import_name(root) == "demo_lib"


def test_two_packages_are_refused(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="exactly one package, found a, b"):
        import_name(_repository(tmp_path, packages=("a", "b")))


def test_a_repository_without_src_is_refused(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="found none"):
        import_name(_repository(tmp_path, packages=()))


@pytest.mark.parametrize("pyproject", ["[tool.x]\n", "[project]\nname = 1\n"])
def test_a_project_without_a_name_is_refused(tmp_path: Path, pyproject: str) -> None:
    with pytest.raises(SystemExit):
        name(_repository(tmp_path, pyproject=pyproject))
