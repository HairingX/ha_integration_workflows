"""Tests of the workflows, the actions and the templates of the callers."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

ROOT = Path(__file__).parents[1]
WORKFLOWS = sorted([*(ROOT / ".github/workflows").glob("*.yml"), *(ROOT / "ha/template/.github/workflows").glob("*.yml")])
ACTIONS = sorted((ROOT / "ha/actions").glob("*/action.yml"))
CALLERS = sorted((ROOT / "ha/template/.github/workflows").glob("*.yml"))
BRANCH_TEST_BUILDS = ROOT / "ha" / "tools" / "branch_test_builds.jq"
OWN = re.compile(r"uses: HairingX/workflows/([^@\s]+)@(\S+)")
MAJOR = "v2"
"""The major version the callers use, which Publish moves."""

OWN_WORKFLOWS = {"ci.yml", "publish.yml"}
"""This repository's own workflows, which no integration calls."""

BASH = "defaults:\n  run:\n    shell: bash\n"


def _ids(paths: list[Path]) -> list[str]:
    return [path.relative_to(ROOT).as_posix() for path in paths]


def test_the_workflows_and_actions_are_found() -> None:
    assert len(WORKFLOWS) > 10
    assert len(ACTIONS) == 2


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=_ids(WORKFLOWS))
def test_a_step_fails_when_a_command_piped_into_another_fails(workflow: Path) -> None:
    """GitHub runs a step as `bash -eo pipefail` only when the shell is given; without one it
    runs `bash -e`, where a failing command piped into another fails nothing."""
    assert BASH in workflow.read_text("utf-8")


@pytest.mark.parametrize("path", [*WORKFLOWS, *ACTIONS], ids=_ids([*WORKFLOWS, *ACTIONS]))
def test_no_step_pipes_into_a_command_that_stops_reading(path: Path) -> None:
    """With pipefail, the command before `head` fails when head stops reading its output."""
    assert "| head" not in path.read_text("utf-8")


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=_ids(WORKFLOWS))
def test_every_workflow_states_its_token_permissions(workflow: Path) -> None:
    assert "\npermissions:" in workflow.read_text("utf-8")


@pytest.mark.parametrize("action", ACTIONS, ids=_ids(ACTIONS))
def test_every_step_of_an_action_runs_bash_with_pipefail(action: Path) -> None:
    """A composite action's run step must name its shell, and bash runs it with pipefail."""
    steps = cast(list[dict[str, Any]], yaml.safe_load(action.read_text("utf-8"))["runs"]["steps"])
    for step in steps:
        if "run" in step:
            assert step.get("shell") == "bash", step.get("name")


@pytest.mark.parametrize("caller", CALLERS, ids=_ids(CALLERS))
def test_a_caller_uses_this_repository_at_its_major_version_and_only_what_exists(caller: Path) -> None:
    for path, ref in OWN.findall(caller.read_text("utf-8")):
        assert ref == MAJOR
        assert (ROOT / path).exists(), path


def test_the_reusable_workflows_are_called_by_their_callers() -> None:
    called = {path for caller in CALLERS for path, _ in OWN.findall(caller.read_text("utf-8"))}
    reusable = {
        workflow.relative_to(ROOT).as_posix()
        for workflow in (ROOT / ".github/workflows").glob("*.yml")
        if "workflow_call" in workflow.read_text("utf-8") and workflow.name not in OWN_WORKFLOWS
    }
    assert reusable <= called
    assert {f"ha/actions/{action.parent.name}" for action in ACTIONS} <= called


def test_the_shared_conventions_name_the_major_version_the_callers_use() -> None:
    assert f"at `@{MAJOR}`" in (ROOT / "ha/template/CLAUDE.md").read_text("utf-8")


@pytest.mark.parametrize("caller", CALLERS, ids=_ids(CALLERS))
def test_the_checks_a_ruleset_requires_keep_their_names(caller: Path) -> None:
    """The ruleset requires checks by name; a job called through a reusable workflow gets a
    prefixed name, so a required check is a job of the caller itself."""
    ruleset = json.loads((ROOT / "ha/template/.github/rulesets/main.json").read_text("utf-8"))
    rule = next(rule for rule in ruleset["rules"] if rule["type"] == "required_status_checks")
    required = {check["context"] for check in rule["parameters"]["required_status_checks"]}
    names = {
        str(job.get("name"))
        for caller_file in CALLERS
        for job in cast(dict[str, dict[str, Any]], yaml.safe_load(caller_file.read_text("utf-8"))["jobs"]).values()
        if "uses" not in job
    }
    assert required <= names


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq is not installed")
class TestBranchTestBuilds:
    RELEASES: list[dict[str, Any]] = [
        {"tag_name": "v0.2.9b1", "prerelease": True, "body": "notes\r\ntest-build-branch: fix/a\r\n"},
        {"tag_name": "v0.2.9b2", "prerelease": True, "body": "test-build-branch: fix/ab"},
        {"tag_name": "v0.2.9b3", "prerelease": True, "body": "test-build-branch: fix/a-2\n"},
        {"tag_name": "v0.2.9b4", "prerelease": True, "body": "x test-build-branch: fix/a"},
        {"tag_name": "v0.2.9", "prerelease": False, "body": "test-build-branch: fix/a"},
        {"tag_name": "v0.2.9b5", "prerelease": True, "body": None},
        {"tag_name": "v0.2.9b6", "prerelease": True, "body": "built\n\ntest-build-branch: fix/a"},
    ]

    def _select(self, branch: str, tag: str | None = None) -> list[str]:
        env = {key: value for key, value in os.environ.items() if key != "TAG"}
        env["BRANCH"] = branch
        if tag is not None:
            env["TAG"] = tag
        result = subprocess.run(
            ["jq", "-r", "-f", str(BRANCH_TEST_BUILDS)],
            input=json.dumps(self.RELEASES),
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        return result.stdout.split()

    def test_only_the_branchs_own_test_builds_are_selected(self) -> None:
        assert self._select("fix/a") == ["v0.2.9b1", "v0.2.9b6"]

    def test_the_test_build_being_published_is_not_selected(self) -> None:
        assert self._select("fix/a", tag="v0.2.9b6") == ["v0.2.9b1"]

    def test_a_branch_whose_name_starts_another_does_not_select_it(self) -> None:
        assert self._select("fix/ab") == ["v0.2.9b2"]
        assert self._select("fix/") == []


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck is not installed")
@pytest.mark.parametrize("action", ACTIONS, ids=_ids(ACTIONS))
def test_every_script_of_an_action_passes_shellcheck(action: Path, tmp_path: Path) -> None:
    """actionlint checks the scripts of workflows, not those of actions."""
    steps = cast(list[dict[str, Any]], yaml.safe_load(action.read_text("utf-8"))["runs"]["steps"])
    for number, step in enumerate(steps):
        if "run" not in step:
            continue
        assert "${{" not in step["run"], "values reach a script through env, never expanded into it"
        script = tmp_path / f"step{number}.sh"
        script.write_text(f"#!/bin/bash\nset -eo pipefail\n{step['run']}", "utf-8")
        result = subprocess.run(["shellcheck", str(script)], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout
