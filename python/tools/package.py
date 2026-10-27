"""What the workflows need to know about a library's repository, read from its own files.

    package.py name ROOT      prints the distribution's name, as pyproject.toml states it
    package.py import ROOT    prints the name the package is imported by: the one package
                              under src/
"""

import sys
import tomllib
from pathlib import Path
from typing import Any, cast


def project(root: Path) -> dict[str, Any]:
    """The [project] table of the repository's pyproject.toml."""
    data = tomllib.loads((root / "pyproject.toml").read_text("utf-8"))
    found = data.get("project")
    if not isinstance(found, dict):
        sys.exit("::error::pyproject.toml must have a [project] table")
    return cast(dict[str, Any], found)


def name(root: Path) -> str:
    """The distribution's name, under which the package index lists it."""
    found = project(root).get("name")
    if not isinstance(found, str) or not found:
        sys.exit("::error::pyproject.toml must name the project in [project] name")
    return found


def import_name(root: Path) -> str:
    """The name the package is imported by: the one package under src/."""
    source = root / "src"
    candidates: list[Path] = list(source.iterdir()) if source.is_dir() else []
    found = sorted(path.name for path in candidates if (path / "__init__.py").is_file())
    if len(found) != 1:
        names = ", ".join(found) or "none"
        sys.exit(f"::error::src/ must hold exactly one package, found {names}")
    return found[0]


def main(arguments: list[str]) -> None:
    """Run the subcommand `arguments` names."""
    match arguments:
        case ["name", root]:
            print(name(Path(root)))
        case ["import", root]:
            print(import_name(Path(root)))
        case _:
            sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
