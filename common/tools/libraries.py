"""The libraries a development branch is tested and test-built with.

A library developed alongside the integration is taken from its branch of the same name, where
it has one, pinned to that branch's current commit; otherwise from the release the integration
pins.

    libraries.py branch ROOT OWNER BRANCH    prints a requirement for each library that has
                                             BRANCH, one per line, in the order they are
                                             installed
    libraries.py requirements FILE [REQUIREMENT ...]
                                             replaces each library's line in the requirements
                                             FILE with the requirement given
    libraries.py manifest FILE [REQUIREMENT ...]
                                             replaces each library's requirement in the manifest
                                             FILE with the requirement given
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from settings import libraries


def _name(line: str) -> str | None:
    """The canonical name of the package a requirements line installs, None for no package."""
    text = line.split("#", 1)[0].strip()
    if not text or text.startswith("-"):
        return None
    try:
        return canonicalize_name(Requirement(text).name)
    except InvalidRequirement:
        return None


def head(repository: str, branch: str) -> str | None:
    """The commit `branch` points to in `repository`, None if it has no such branch."""
    out = subprocess.run(
        ["git", "ls-remote", repository, f"refs/heads/{branch}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return out[0] if out else None


def branch_requirements(root: Path, owner: str, branch: str) -> list[str]:
    """A requirement for each library that has `branch`, pinned to its current commit.

    Dependabot's branches are left out: it names a branch after the update, so two repositories
    it updates alike share a branch name without being developed together.
    """
    found: list[str] = []
    if branch.startswith("dependabot/"):
        return found
    for library in libraries(root):
        repository = f"https://github.com/{owner}/{library}"
        commit = head(repository, branch)
        if commit is not None:
            # An archive of the commit needs no git where it is installed.
            found.append(f"{library} @ {repository}/archive/{commit}.tar.gz")
    return found


def replace_requirements(lines: list[str], requirements: list[str]) -> list[str]:
    """`lines` with each library's line replaced by its requirement in `requirements`."""
    given = {canonicalize_name(Requirement(r).name): r for r in requirements}
    kept = [line for line in lines if _name(line) not in given]
    return [*kept, *requirements]


def replace_manifest(text: str, requirements: list[str]) -> str:
    """The manifest `text` with each library's requirement replaced by the one given."""
    if not requirements:
        return text
    data = cast(dict[str, Any], json.loads(text))
    given = {canonicalize_name(Requirement(r).name) for r in requirements}
    kept = [r for r in cast(list[str], data["requirements"]) if _name(r) not in given]
    data["requirements"] = [*requirements, *kept]
    indent = re.search(r'^( +)"', text, re.MULTILINE)
    return json.dumps(data, indent=len(indent.group(1)) if indent else 2, ensure_ascii=False) + "\n"


def main(arguments: list[str]) -> None:
    """Run the subcommand `arguments` names."""
    match arguments:
        case ["branch", root, owner, branch]:
            for requirement in branch_requirements(Path(root), owner, branch):
                print(requirement)
        case ["requirements", path, *requirements]:
            file = Path(path)
            lines = file.read_text("utf-8").splitlines()
            file.write_text("\n".join(replace_requirements(lines, requirements)) + "\n", "utf-8")
        case ["manifest", path, *requirements]:
            file = Path(path)
            file.write_text(replace_manifest(file.read_text("utf-8"), requirements), "utf-8")
        case _:
            sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
