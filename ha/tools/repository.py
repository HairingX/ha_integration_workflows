"""What the workflows need to know about an integration's repository, read from its own files.

    repository.py integration ROOT   prints the integration's directory, relative to ROOT
    repository.py domain ROOT        prints the integration's domain
    repository.py zip ROOT           prints the name of the zip HACS installs, from hacs.json
    repository.py libraries ROOT     prints the libraries developed alongside the integration, in
                                     the order they are installed, one per line
    repository.py coverage ROOT      prints the coverage the tests must reach, in percent
"""

import json
import sys
import tomllib
from pathlib import Path
from typing import Any, cast

CONFIGURATION = "ha-integration-workflows"
"""The table in pyproject.toml, under [tool], that holds what cannot be read from elsewhere."""


def integration(root: Path) -> Path:
    """The one directory under custom_components/, the integration HACS installs."""
    found = [
        path
        for path in sorted((root / "custom_components").iterdir())
        if path.is_dir() and not path.name.startswith((".", "__"))
    ]
    if len(found) != 1:
        names = ", ".join(path.name for path in found) or "none"
        sys.exit(f"::error::custom_components/ must hold exactly one integration, found {names}")
    return found[0]


def domain(root: Path) -> str:
    """The integration's domain, which its manifest states and its directory is named after."""
    directory = integration(root)
    stated = cast(dict[str, Any], json.loads((directory / "manifest.json").read_text("utf-8")))
    if stated.get("domain") != directory.name:
        sys.exit(f"::error::the manifest's domain is {stated.get('domain')!r}, not {directory.name!r}")
    return directory.name


def zip_name(root: Path) -> str:
    """The name of the zip a release carries, which hacs.json tells HACS to install."""
    hacs = cast(dict[str, Any], json.loads((root / "hacs.json").read_text("utf-8")))
    if hacs.get("zip_release") is not True or not hacs.get("filename"):
        sys.exit("::error::hacs.json must set zip_release to true and name the zip in filename")
    return str(hacs["filename"])


def tool(root: Path, name: str) -> dict[str, Any]:
    """The table [tool.<name>] of the repository's pyproject.toml, empty without one."""
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return {}
    data = tomllib.loads(pyproject.read_text("utf-8"))
    tools = cast(dict[str, Any], data.get("tool", {}))
    return cast(dict[str, Any], tools.get(name, {}))


def transition(root: Path) -> str | None:
    """Why the repository is not yet held to the whole standard, None when it is."""
    reason = tool(root, CONFIGURATION).get("transition")
    if reason is not None and (not isinstance(reason, str) or not reason.strip()):
        sys.exit(f"::error::[tool.{CONFIGURATION}] transition must say why, as text")
    return reason


def coverage(root: Path) -> int:
    """The coverage the tests must reach: 100, lower only during a transition."""
    value = tool(root, CONFIGURATION).get("coverage", 100)
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100:
        sys.exit(f"::error::[tool.{CONFIGURATION}] coverage must be a whole percentage")
    if value < 100 and transition(root) is None:
        sys.exit(f"::error::[tool.{CONFIGURATION}] coverage below 100 needs a transition saying why")
    return value


def libraries(root: Path) -> list[str]:
    """The libraries developed alongside the integration, in the order they are installed."""
    names = tool(root, CONFIGURATION).get("libraries", [])
    if not isinstance(names, list) or not all(isinstance(name, str) for name in cast(list[Any], names)):
        sys.exit(f"::error::[tool.{CONFIGURATION}] libraries must be a list of names")
    return cast(list[str], names)


def main(arguments: list[str]) -> None:
    """Run the subcommand `arguments` names."""
    match arguments:
        case ["integration", root]:
            print(integration(Path(root)).relative_to(Path(root)).as_posix())
        case ["domain", root]:
            print(domain(Path(root)))
        case ["zip", root]:
            print(zip_name(Path(root)))
        case ["libraries", root]:
            for name in libraries(Path(root)):
                print(name)
        case ["coverage", root]:
            print(coverage(Path(root)))
        case _:
            sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
