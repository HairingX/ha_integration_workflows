"""What a repository says about itself under [tool.hairingx-workflows] in its pyproject.toml.

    settings.py libraries ROOT    prints the libraries developed alongside the repository, in
                                  the order they are installed, one per line
    settings.py coverage ROOT     prints the coverage the tests must reach, in percent
"""

import sys
import tomllib
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, cast

CONFIGURATION = "hairingx-workflows"
"""The table in pyproject.toml, under [tool], that holds what cannot be read from elsewhere."""
PREVIOUS_CONFIGURATION = "ha-integration-workflows"
"""The table's former name, read where the repository has no table of the current name."""


def tool(root: Path, name: str) -> dict[str, Any]:
    """The table [tool.<name>] of the repository's pyproject.toml, empty without one."""
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return {}
    data = tomllib.loads(pyproject.read_text("utf-8"))
    tools = cast(dict[str, Any], data.get("tool", {}))
    return cast(dict[str, Any], tools.get(name, {}))


def settings(root: Path) -> dict[str, Any]:
    """The repository's settings for these workflows, empty without any."""
    return tool(root, CONFIGURATION) or tool(root, PREVIOUS_CONFIGURATION)


def transition(root: Path) -> str | None:
    """Why the repository is not yet held to the whole standard, None when it is."""
    reason = settings(root).get("transition")
    if reason is not None and (not isinstance(reason, str) or not reason.strip()):
        sys.exit(f"::error::[tool.{CONFIGURATION}] transition must say why, as text")
    return reason


def coverage(root: Path) -> int:
    """The coverage the tests must reach: 100, lower only during a transition."""
    value = settings(root).get("coverage", 100)
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100:
        sys.exit(f"::error::[tool.{CONFIGURATION}] coverage must be a whole percentage")
    if value < 100 and transition(root) is None:
        sys.exit(f"::error::[tool.{CONFIGURATION}] coverage below 100 needs a transition saying why")
    return value


def libraries(root: Path) -> list[str]:
    """The libraries developed alongside the repository, in the order they are installed."""
    names = settings(root).get("libraries", [])
    if not isinstance(names, list) or not all(isinstance(name, str) for name in cast(list[Any], names)):
        sys.exit(f"::error::[tool.{CONFIGURATION}] libraries must be a list of names")
    return cast(list[str], names)


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


def main(arguments: list[str]) -> None:
    """Run the subcommand `arguments` names."""
    match arguments:
        case ["libraries", root]:
            for name in libraries(Path(root)):
                print(name)
        case ["coverage", root]:
            print(coverage(Path(root)))
        case _:
            sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
