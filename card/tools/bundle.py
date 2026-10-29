"""The card's bundle: the one ES module HACS installs, built to dist/ under hacs.json's filename.

    bundle.py filename ROOT          prints the bundle's name, hacs.json's filename
    bundle.py check ROOT VERSION     refuses dist/<filename> unless it holds VERSION, as a whole
                                     word, and prints its path relative to ROOT
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, cast

DIST = "dist"


def filename_error(value: object) -> str | None:
    """Why `value` cannot name the bundle, None when it can.

    HACS looks the name up among a release's assets and at the top of dist/, so it is a bare
    file name; a dashboard loads it as a JavaScript module.
    """
    if not isinstance(value, str) or not value:
        return "hacs.json must name the bundle in filename"
    if "/" in value or "\\" in value or not value.endswith(".js") or value.startswith("."):
        return f"hacs.json names the bundle {value!r}; it must be a file name ending in .js, without a directory"
    return None


def filename(root: Path) -> str:
    """The bundle's name, which hacs.json tells HACS to install."""
    hacs = cast(dict[str, Any], json.loads((root / "hacs.json").read_text("utf-8")))
    error = filename_error(hacs.get("filename"))
    if error is not None:
        sys.exit(f"::error::{error}")
    return str(hacs["filename"])


def check(root: Path, version: str) -> Path:
    """The bundle built in `root`, refused unless it holds `version` as a whole word.

    A minifier may fold the version into a longer string, such as a banner, so it is not looked
    for in quotes; 1.2.3 is not found in 11.2.3 or 1.2.3rc1.
    """
    path = Path(DIST) / filename(root)
    built = root / path
    if not built.is_file() or built.stat().st_size == 0:
        sys.exit(f"::error::the build wrote no {path.as_posix()}; hacs.json names it as the bundle")
    text = built.read_text("utf-8")
    if re.search(rf"(?<![\w.+-]){re.escape(version)}(?![\w.+-])", text) is None:
        sys.exit(
            f"::error::{path.as_posix()} does not hold the version {version!r}; the build must embed "
            f"the version CARD_VERSION gives it"
        )
    return path


def main(arguments: list[str]) -> None:
    """Run the subcommand `arguments` names."""
    match arguments:
        case ["filename", root]:
            print(filename(Path(root)))
        case ["check", root, version]:
            print(check(Path(root), version).as_posix())
        case _:
            sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
