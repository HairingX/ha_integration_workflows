"""Tests of what every integration's repository promises."""

import json
from pathlib import Path

from packaging.specifiers import SpecifierSet

import pytest

import contract
from contract import (
    QUALITY_SCALE_RULES,
    check,
    check_hacs,
    check_manifest,
    check_quality_scale,
    check_requirements,
    check_translations,
    HomeAssistant,
    home_assistant,
    released,
)


def test_a_library_built_from_a_branch_is_not_a_release() -> None:
    assert released("0.2.0")
    assert released("0.2.0rc1")
    assert not released("0.2.1.dev3+g1c7097c")
    assert not released("0.2.1+local")
    assert not released("not a version")


def test_the_manifest_says_0_0_0() -> None:
    assert list(check_manifest({"version": "0.0.0"})) == []
    assert list(check_manifest({"version": "0.2.8"})) == [
        "manifest.json says version '0.2.8'; it must say '0.0.0'"
    ]


def test_hacs_installs_the_domains_zip_on_the_home_assistant_tested() -> None:
    hacs = {"zip_release": True, "filename": "demo.zip", "homeassistant": "2026.10.4"}
    assert list(check_hacs(hacs, "demo", "2026.10.4")) == []


def test_every_way_hacs_json_can_be_wrong_is_reported() -> None:
    hacs = {"filename": "other.zip", "homeassistant": "2026.3.0"}
    assert list(check_hacs(hacs, "demo", "2026.10.4")) == [
        "hacs.json must set zip_release to true",
        "hacs.json names the zip 'other.zip'; it must be 'demo.zip'",
        "hacs.json requires Home Assistant '2026.3.0', but the tests run '2026.10.4'",
    ]


def test_a_requirement_pinned_installed_and_pinned_for_the_tests_holds() -> None:
    assert list(check_requirements(["Device_Lib==1.2.0"], ["Device_Lib==1.2.0"], {"device-lib": "1.2.0"}, HomeAssistant())) == []


def test_a_requirement_must_be_pinned_exactly() -> None:
    assert list(check_requirements(["lxml>=5.0.0"], [], {"lxml": "5.3.0"}, HomeAssistant())) == [
        "the manifest's requirement 'lxml>=5.0.0' must pin one version with =="
    ]


def test_the_tests_must_run_the_version_pinned() -> None:
    assert list(check_requirements(["lib==1.2.0"], ["lib==1.2.0"], {"lib": "1.3.0"}, HomeAssistant())) == [
        "the manifest pins 'lib==1.2.0', but the tests run lib 1.3.0"
    ]


def test_requirements_test_txt_must_pin_what_the_manifest_does() -> None:
    assert list(check_requirements(["lib==1.2.0"], ["# lib==1.2.0", "other==1"], {"lib": "1.2.0"}, HomeAssistant())) == [
        "requirements-test.txt must pin 'lib==1.2.0', as the manifest does"
    ]


def test_a_library_from_a_branch_is_not_held_to_its_pin() -> None:
    assert list(check_requirements(["lib==1.2.0"], ["lib==1.2.0"], {"lib": "1.2.1.dev3+gabc"}, HomeAssistant())) == []


def test_a_requirement_not_installed_is_reported() -> None:
    assert list(check_requirements(["lib==1.2.0"], ["lib==1.2.0"], {"lib": None}, HomeAssistant())) == [
        "lib is required by the manifest but not installed"
    ]


def _all_done() -> dict[str, object]:
    return {rule: "done" for rule in QUALITY_SCALE_RULES}


def test_a_quality_scale_stating_every_rule_holds() -> None:
    rules = _all_done()
    rules["discovery"] = {"status": "exempt", "comment": "The device cannot be discovered."}
    assert list(check_quality_scale(rules)) == []


def test_a_rule_missing_or_unknown_is_reported() -> None:
    rules = _all_done()
    del rules["brands"]
    rules["made-up"] = "done"
    assert list(check_quality_scale(rules)) == [
        "quality_scale.yaml does not state the rule brands",
        "quality_scale.yaml states made-up, which is no rule of the quality scale",
    ]


def test_a_rule_not_done_needs_a_reason() -> None:
    rules = _all_done()
    rules["discovery"] = {"status": "todo"}
    rules["brands"] = {"status": "maybe", "comment": "?"}
    rules["devices"] = "todo"
    assert list(check_quality_scale(rules)) == [
        "quality_scale.yaml: brands has status 'maybe'",
        "quality_scale.yaml: devices must be done, or have a status and a comment",
        "quality_scale.yaml: discovery is todo without a comment saying why",
    ]


def test_the_rules_are_those_hassfest_lists() -> None:
    assert len(QUALITY_SCALE_RULES) == 54


def test_every_translation_holds_the_keys_english_has() -> None:
    english = {"config": {"step": {"user": {"title": "Set up"}}}, "entity": {}}
    danish = {"config": {"step": {"user": {"title": "Opsæt", "extra": "x"}}}}
    assert list(check_translations({"en": english, "da": danish})) == [
        "translations/da.json lacks entity",
        "translations/da.json has config.step.user.extra, which English does not",
    ]


def test_english_must_be_there() -> None:
    assert list(check_translations({"da": {}})) == ["translations/en.json is missing"]


def _repository(root: Path) -> Path:
    integration = root / "custom_components" / "demo"
    (integration / "translations").mkdir(parents=True)
    (integration / "manifest.json").write_text(
        json.dumps({"domain": "demo", "version": "0.0.0", "requirements": ["lib==1.2.0"]}), "utf-8"
    )
    (integration / "translations" / "en.json").write_text('{"title": "Demo"}', "utf-8")
    (integration / "translations" / "da.json").write_text('{"title": "Demo"}', "utf-8")
    rules = "\n".join(f"  {rule}: done" for rule in sorted(QUALITY_SCALE_RULES))
    (integration / "quality_scale.yaml").write_text(f"rules:\n{rules}\n", "utf-8")
    (root / "hacs.json").write_text(
        json.dumps({"zip_release": True, "filename": "demo.zip", "homeassistant": "2026.10.4"}), "utf-8"
    )
    (root / "requirements-test.txt").write_text("lib==1.2.0\n", "utf-8")
    (root / "pyproject.toml").write_text('[tool.pyright]\ntypeCheckingMode = "strict"\n', "utf-8")
    return root


def test_a_repository_keeping_every_promise_has_no_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    versions = {"lib": "1.2.0", "homeassistant": "2026.10.4"}
    monkeypatch.setattr(contract, "_installed", versions.get)
    assert check(_repository(tmp_path)) == []


def test_a_repository_without_a_quality_scale_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    versions = {"lib": "1.2.0", "homeassistant": "2026.10.4"}
    monkeypatch.setattr(contract, "_installed", versions.get)
    root = _repository(tmp_path)
    (root / "custom_components" / "demo" / "quality_scale.yaml").unlink()
    errors = check(root)
    assert errors[0] == "demo/quality_scale.yaml is missing"
    assert len(errors) == 1 + len(QUALITY_SCALE_RULES)


def test_a_pin_with_a_comment_is_read_without_it() -> None:
    pinned = ["lib==1.2.0  # the manifest's", "other @ https://example.invalid/x.tar.gz"]
    assert list(check_requirements(["lib==1.2.0"], pinned, {"lib": "1.2.0"}, HomeAssistant())) == []


def test_home_assistants_requirements_are_read_from_its_package(tmp_path: Path) -> None:
    for name, requirements in {"scrape": ["beautifulsoup4==4.13.3", "lxml==6.1.2"], "other": ["lxml>=5"]}.items():
        (tmp_path / "components" / name).mkdir(parents=True)
        (tmp_path / "components" / name / "manifest.json").write_text(json.dumps({"requirements": requirements}), "utf-8")
    (tmp_path / "package_constraints.txt").write_text("# Constraints\npymodbus==3.11.2\n", "utf-8")
    core = home_assistant(tmp_path, ["requests==2.34.2", "colorlog==6.9; extra == 'dev'"])
    assert core.dependencies == {"requests"}
    assert core.pins == {"beautifulsoup4": {"4.13.3"}, "lxml": {"6.1.2"}}
    assert {name: str(spec) for name, spec in core.constraints.items()} == {"pymodbus": "==3.11.2"}


SCRAPE = HomeAssistant(
    dependencies=frozenset({"requests"}),
    pins={"beautifulsoup4": frozenset({"4.13.3"}), "lxml": frozenset({"6.1.2"})},
)


def test_a_package_home_assistant_installs_is_not_listed() -> None:
    assert list(check_requirements(["requests>=2"], [], {"requests": "2.34.2"}, SCRAPE)) == [
        "requests is a dependency of Home Assistant itself; the manifest must not list it"
    ]


def test_a_package_home_assistants_integrations_pin_is_required_at_a_minimum() -> None:
    assert list(check_requirements(["lxml==6.1.2"], ["lxml==6.1.2"], {"lxml": "6.1.2"}, SCRAPE)) == [
        "the manifest pins 'lxml==6.1.2', a package Home Assistant's own integrations use (6.1.2); "
        "require a minimum version instead, such as 'lxml>=6.1.2'"
    ]


def test_a_minimum_that_admits_home_assistants_version_holds() -> None:
    pinned = ["beautifulsoup4==4.13.3", "lxml==6.1.2"]
    installed = {"beautifulsoup4": "4.13.3", "lxml": "6.1.2"}
    assert list(check_requirements(["beautifulsoup4>=4.12.0", "lxml>=5.0.0"], pinned, installed, SCRAPE)) == []


def test_a_minimum_above_home_assistants_version_is_refused() -> None:
    assert list(check_requirements(["lxml>=6.2"], ["lxml==6.1.2"], {"lxml": "6.1.2"}, SCRAPE)) == [
        "the manifest's 'lxml>=6.2' excludes lxml 6.1.2, which Home Assistant's own integrations pin"
    ]


def test_the_tests_run_home_assistants_version_of_a_shared_package() -> None:
    assert list(check_requirements(["lxml>=5"], ["lxml==6.1.3"], {"lxml": "6.1.3"}, SCRAPE)) == [
        "requirements-test.txt must pin lxml to the version Home Assistant's own integrations pin (6.1.2)"
    ]
    assert list(check_requirements(["lxml>=5"], ["lxml==6.1.2"], {"lxml": "6.1.3"}, SCRAPE)) == [
        "the tests run lxml 6.1.3, not the version Home Assistant's own integrations pin"
    ]


def test_a_pin_home_assistants_constraints_exclude_is_refused() -> None:
    core = HomeAssistant(constraints={"pymodbus": SpecifierSet("==3.11.2")})
    assert list(check_requirements(["pymodbus==3.9.0"], ["pymodbus==3.9.0"], {"pymodbus": "3.9.0"}, core)) == [
        "the manifest pins 'pymodbus==3.9.0', which Home Assistant's package constraints (pymodbus==3.11.2) exclude"
    ]
