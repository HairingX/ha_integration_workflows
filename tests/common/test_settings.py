"""Tests of what a repository says about itself under [tool.hairingx-workflows]."""

from pathlib import Path

import pytest

from settings import check_standard, coverage, libraries, transition


def _repository(root: Path, *, pyproject: str | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    if pyproject is not None:
        (root / "pyproject.toml").write_text(pyproject, "utf-8")
    return root


def test_the_libraries_are_listed_in_pyproject_in_their_order(tmp_path: Path) -> None:
    root = _repository(
        tmp_path,
        pyproject='[tool.hairingx-workflows]\nlibraries = ["base_lib", "device_lib"]\n',
    )
    assert libraries(root) == ["base_lib", "device_lib"]


@pytest.mark.parametrize("pyproject", [None, "[tool.pytest.ini_options]\n"])
def test_without_a_list_there_are_no_libraries(tmp_path: Path, pyproject: str | None) -> None:
    assert libraries(_repository(tmp_path, pyproject=pyproject)) == []


def test_a_list_of_anything_but_names_is_refused(tmp_path: Path) -> None:
    root = _repository(tmp_path, pyproject="[tool.hairingx-workflows]\nlibraries = [1]\n")
    with pytest.raises(SystemExit, match="must be a list of names"):
        libraries(root)


def test_the_tests_cover_every_line_unless_told_otherwise(tmp_path: Path) -> None:
    assert coverage(_repository(tmp_path)) == 100
    assert transition(_repository(tmp_path / "other")) is None


def test_a_transition_allows_a_lower_coverage_and_says_why(tmp_path: Path) -> None:
    root = _repository(
        tmp_path,
        pyproject='[tool.hairingx-workflows]\ncoverage = 29\ntransition = "Typed and tested module by module."\n',
    )
    assert coverage(root) == 29
    assert transition(root) == "Typed and tested module by module."


def test_a_lower_coverage_without_a_transition_is_refused(tmp_path: Path) -> None:
    root = _repository(tmp_path, pyproject="[tool.hairingx-workflows]\ncoverage = 90\n")
    with pytest.raises(SystemExit, match="needs a transition saying why"):
        coverage(root)


@pytest.mark.parametrize("setting", ["coverage = 101", 'coverage = "100"', "coverage = true"])
def test_a_coverage_that_is_no_percentage_is_refused(tmp_path: Path, setting: str) -> None:
    root = _repository(tmp_path, pyproject=f'[tool.hairingx-workflows]\n{setting}\ntransition = "x"\n')
    with pytest.raises(SystemExit, match="must be a whole percentage"):
        coverage(root)


def test_a_transition_that_says_nothing_is_refused(tmp_path: Path) -> None:
    root = _repository(tmp_path, pyproject='[tool.hairingx-workflows]\ntransition = " "\n')
    with pytest.raises(SystemExit, match="must say why"):
        transition(root)


def test_the_former_name_of_the_table_is_read_without_one_of_the_current_name(tmp_path: Path) -> None:
    root = _repository(tmp_path, pyproject='[tool.ha-integration-workflows]\nlibraries = ["base_lib"]\n')
    assert libraries(root) == ["base_lib"]


def test_the_table_of_the_current_name_wins(tmp_path: Path) -> None:
    root = _repository(
        tmp_path,
        pyproject='[tool.ha-integration-workflows]\nlibraries = ["old"]\n\n[tool.hairingx-workflows]\nlibraries = ["new"]\n',
    )
    assert libraries(root) == ["new"]


def test_the_whole_standard_holds_without_a_transition() -> None:
    assert list(check_standard({"typeCheckingMode": "strict"}, 100, None)) == []
    assert list(check_standard({"typeCheckingMode": "standard"}, 90, None)) == [
        'pyproject.toml must set [tool.pyright] typeCheckingMode to "strict"',
        "the tests must cover every line, not 90%",
    ]


def test_no_file_is_left_unchecked_without_a_transition() -> None:
    assert list(check_standard({"typeCheckingMode": "strict", "ignore": ["a.py"]}, 100, None)) == [
        "pyproject.toml must leave no file unchecked in [tool.pyright] ignore"
    ]


def test_a_transition_relaxes_the_standard() -> None:
    assert list(check_standard({"typeCheckingMode": "standard"}, 29, "Typed module by module.")) == []
