"""What the workflows need to know about an integration's repository, read from its own files.

    repository.py integration ROOT   prints the integration's directory, relative to ROOT
    repository.py domain ROOT        prints the integration's domain
    repository.py zip ROOT           prints the name of the zip HACS installs, from hacs.json
"""

import json
import sys
from pathlib import Path
from typing import Any, cast


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


def main(arguments: list[str]) -> None:
    """Run the subcommand `arguments` names."""
    match arguments:
        case ["integration", root]:
            print(integration(Path(root)).relative_to(Path(root)).as_posix())
        case ["domain", root]:
            print(domain(Path(root)))
        case ["zip", root]:
            print(zip_name(Path(root)))
        case _:
            sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
