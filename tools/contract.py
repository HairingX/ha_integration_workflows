"""What every integration's repository promises, checked against the installed environment.

    contract.py ROOT     checks the repository at ROOT, with the tests' packages installed, and
                         fails with one error per broken promise

The promises: the manifest says 0.0.0, as the version lives in the release's tag and zip; HACS
installs a zip named after the domain and requires the Home Assistant the tests run; every
requirement is pinned, the tests run that version and requirements-test.txt pins it, and a package
Home Assistant's own integrations pin is pinned to their version; the quality scale states every
rule; and every translation holds the same keys.
"""

import importlib.metadata
import importlib.util
import json
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, cast

import yaml
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from repository import coverage, domain, integration, tool, transition

QUALITY_SCALE_RULES = frozenset({
    # Bronze
    "action-setup", "appropriate-polling", "brands", "common-modules",
    "config-flow-test-coverage", "config-flow", "dependency-transparency", "docs-actions",
    "docs-conditions", "docs-high-level-description", "docs-installation-instructions",
    "docs-removal-instructions", "docs-triggers", "entity-event-setup", "entity-unique-id",
    "has-entity-name", "runtime-data", "test-before-configure", "test-before-setup",
    "unique-config-entry",
    # Silver
    "action-exceptions", "config-entry-unloading", "docs-configuration-parameters",
    "docs-installation-parameters", "entity-unavailable", "integration-owner",
    "log-when-unavailable", "parallel-updates", "reauthentication-flow", "test-coverage",
    # Gold
    "devices", "diagnostics", "discovery-update-info", "discovery", "docs-data-update",
    "docs-examples", "docs-known-limitations", "docs-supported-devices",
    "docs-supported-functions", "docs-troubleshooting", "docs-use-cases", "dynamic-devices",
    "entity-category", "entity-device-class", "entity-disabled-by-default",
    "entity-translations", "exception-translations", "icon-translations",
    "reconfiguration-flow", "repair-issues", "stale-devices",
    # Platinum
    "async-dependency", "inject-websession", "strict-typing",
})
"""The rules of Home Assistant's Integration Quality Scale, as hassfest's ALL_RULES lists them.
hassfest does not check this file for a custom integration, so this does."""


def _json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text("utf-8")))


def _installed(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _core_pins() -> dict[str, set[str]]:
    spec = importlib.util.find_spec("homeassistant")
    if spec is None or spec.origin is None:
        return {}
    return core_pins(Path(spec.origin).parent / "components")


def released(version: str) -> bool:
    """Whether `version` is a release, not a build of a branch."""
    try:
        parsed = Version(version)
    except InvalidVersion:
        return False
    return parsed.local is None and parsed.dev is None


def check_manifest(manifest: Mapping[str, Any]) -> Iterator[str]:
    """The manifest says 0.0.0: releases set the version in their zip only."""
    if manifest.get("version") != "0.0.0":
        yield f"manifest.json says version {manifest.get('version')!r}; it must say '0.0.0'"


def check_hacs(hacs: Mapping[str, Any], name: str, home_assistant: str | None) -> Iterator[str]:
    """HACS installs the release's zip, named after the domain, on the Home Assistant tested."""
    if hacs.get("zip_release") is not True:
        yield "hacs.json must set zip_release to true"
    if hacs.get("filename") != f"{name}.zip":
        yield f"hacs.json names the zip {hacs.get('filename')!r}; it must be '{name}.zip'"
    if hacs.get("homeassistant") != home_assistant:
        yield (
            f"hacs.json requires Home Assistant {hacs.get('homeassistant')!r}, "
            f"but the tests run {home_assistant!r}"
        )


def check_requirements(
    requirements: list[str], pinned: list[str], installed: Mapping[str, str | None]
) -> Iterator[str]:
    """Every requirement is pinned exactly, installed at that version, and pinned for the tests.

    A library installed from a branch is no release, so its pin is not checked.
    """
    texts = [line.split("#", 1)[0].strip() for line in pinned]
    pins = {
        canonicalize_name(Requirement(text).name): text
        for text in texts
        if text and not text.startswith("-") and "@" not in text
    }
    for text in requirements:
        requirement = Requirement(text)
        name = canonicalize_name(requirement.name)
        specifiers = list(requirement.specifier)
        if len(specifiers) != 1 or specifiers[0].operator != "==":
            yield f"the manifest's requirement {text!r} must pin one version with =="
            continue
        version = installed.get(name)
        if version is None:
            yield f"{requirement.name} is required by the manifest but not installed"
            continue
        if not released(version):
            continue
        if version != specifiers[0].version:
            yield f"the manifest pins {text!r}, but the tests run {requirement.name} {version}"
        if pins.get(name) != text:
            yield f"requirements-test.txt must pin {text!r}, as the manifest does"


def core_pins(components: Path) -> dict[str, set[str]]:
    """The versions Home Assistant's own integrations pin, by canonical package name."""
    pins: dict[str, set[str]] = {}
    for manifest in sorted(components.glob("*/manifest.json")):
        for text in cast(list[str], _json(manifest).get("requirements", [])):
            try:
                requirement = Requirement(text)
            except InvalidRequirement:
                continue
            for specifier in requirement.specifier:
                if specifier.operator == "==":
                    pins.setdefault(canonicalize_name(requirement.name), set()).add(specifier.version)
    return pins


def check_core_pins(requirements: list[str], core: Mapping[str, set[str]]) -> Iterator[str]:
    """A requirement Home Assistant's own integrations also pin is pinned to their version.

    Home Assistant installs every loaded integration's requirements; two integrations pinning one
    package to different versions make it reinstall one over the other.
    """
    for text in requirements:
        requirement = Requirement(text)
        theirs = core.get(canonicalize_name(requirement.name))
        if not theirs:
            continue
        ours = {s.version for s in requirement.specifier if s.operator == "=="}
        if not ours & theirs:
            yield (
                f"the manifest pins {text!r}, but Home Assistant's own integrations pin "
                f"{requirement.name} {', '.join(sorted(theirs))}"
            )


def check_quality_scale(rules: Mapping[str, Any]) -> Iterator[str]:
    """The quality scale states every rule, and a reason for each one not done."""
    for rule in sorted(QUALITY_SCALE_RULES - set(rules)):
        yield f"quality_scale.yaml does not state the rule {rule}"
    for rule in sorted(set(rules) - QUALITY_SCALE_RULES):
        yield f"quality_scale.yaml states {rule}, which is no rule of the quality scale"
    for rule, state in sorted(rules.items()):
        if state == "done":
            continue
        if not isinstance(state, dict):
            yield f"quality_scale.yaml: {rule} must be done, or have a status and a comment"
            continue
        entry = cast(dict[str, Any], state)
        if entry.get("status") not in ("done", "exempt", "todo"):
            yield f"quality_scale.yaml: {rule} has status {entry.get('status')!r}"
        elif entry["status"] != "done" and not entry.get("comment"):
            yield f"quality_scale.yaml: {rule} is {entry['status']} without a comment saying why"


def keys(tree: Mapping[str, Any], prefix: str = "") -> set[str]:
    """Every key of the nested `tree`, as a dotted path."""
    found: set[str] = set()
    for key, value in tree.items():
        path = f"{prefix}{key}"
        found.add(path)
        if isinstance(value, Mapping):
            found |= keys(cast(Mapping[str, Any], value), f"{path}.")
    return found


def check_translations(translations: Mapping[str, Mapping[str, Any]]) -> Iterator[str]:
    """English is there, and every translation holds the same keys as English."""
    if "en" not in translations:
        yield "translations/en.json is missing"
        return
    english = keys(translations["en"])
    for language, tree in sorted(translations.items()):
        if language == "en":
            continue
        other = keys(tree)
        for key in sorted(english - other):
            yield f"translations/{language}.json lacks {key}"
        for key in sorted(other - english):
            yield f"translations/{language}.json has {key}, which English does not"


def check_standard(pyright: Mapping[str, Any], percent: int, reason: str | None) -> Iterator[str]:
    """pyright is strict and the tests cover every line, unless a transition says why not yet."""
    if reason is not None:
        return
    if pyright.get("typeCheckingMode") != "strict":
        yield "pyproject.toml must set [tool.pyright] typeCheckingMode to \"strict\""
    if pyright.get("ignore"):
        yield "pyproject.toml must leave no file unchecked in [tool.pyright] ignore"
    if percent != 100:
        yield f"the tests must cover every line, not {percent}%"


def check(root: Path) -> list[str]:
    """Every broken promise of the repository at `root`."""
    directory = integration(root)
    name = domain(root)
    manifest = _json(directory / "manifest.json")
    requirements = cast(list[str], manifest.get("requirements", []))
    pinned = (root / "requirements-test.txt").read_text("utf-8").splitlines()
    installed: dict[str, str | None] = {
        canonicalize_name(Requirement(r).name): _installed(Requirement(r).name) for r in requirements
    }
    quality_scale = directory / "quality_scale.yaml"
    rules: dict[str, Any] = {}
    errors: list[str] = []
    if quality_scale.exists():
        rules = cast(dict[str, Any], yaml.safe_load(quality_scale.read_text("utf-8"))["rules"])
    else:
        errors.append(f"{directory.name}/quality_scale.yaml is missing")
    translations = {
        path.stem: _json(path) for path in sorted((directory / "translations").glob("*.json"))
    }
    errors += [
        *check_standard(tool(root, "pyright"), coverage(root), transition(root)),
        *check_manifest(manifest),
        *check_hacs(_json(root / "hacs.json"), name, _installed("homeassistant")),
        *check_requirements(requirements, pinned, installed),
        *check_core_pins(requirements, _core_pins()),
        *check_quality_scale(rules),
        *check_translations(translations),
    ]
    return errors


def main(arguments: list[str]) -> None:
    """Run the check `arguments` names."""
    match arguments:
        case [root]:
            reason = transition(Path(root))
            if reason is not None:
                print(f"::warning::Not yet held to the whole standard: {reason}")
            errors = check(Path(root))
            for error in errors:
                print(f"::error::{error}")
            if errors:
                sys.exit(1)
            print("Every promise of the repository holds.")
        case _:
            sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
