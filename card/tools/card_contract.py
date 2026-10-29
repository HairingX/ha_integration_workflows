"""What every card's repository promises.

    card_contract.py ROOT    checks the repository at ROOT and fails with one error per broken
                             promise

The promises: package.json and package-lock.json say 0.0.0, as the version lives in the release's
tag and in the bundle it carries; package.json has the scripts the tests run; hacs.json names the
card, its bundle and the oldest Home Assistant it supports, and lets HACS install the bundle from
the release; and the bundle is built, never committed.
"""

import json
import subprocess
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, cast

from packaging.version import InvalidVersion, Version

from bundle import DIST, filename_error

VERSION = "0.0.0"
SCRIPTS = ("lint", "typecheck", "test", "build")
"""The npm scripts the shared tests run, in that order."""


def _json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text("utf-8")))


def _version(text: str) -> bool:
    try:
        Version(text)
    except InvalidVersion:
        return False
    return True


def check_package(package: Mapping[str, Any]) -> Iterator[str]:
    """package.json says 0.0.0, and has every script the shared tests run."""
    if package.get("version") != VERSION:
        yield f"package.json says version {package.get('version')!r}; it must say {VERSION!r}"
    scripts = cast(dict[str, Any], package.get("scripts") or {})
    for script in SCRIPTS:
        if not isinstance(scripts.get(script), str) or not scripts[script].strip():
            yield f"package.json must have the script {script!r}, which the tests run"


def check_lock(lock: Mapping[str, Any] | None) -> Iterator[str]:
    """package-lock.json is committed, and says the version package.json does."""
    if lock is None:
        yield "package-lock.json is missing; npm ci installs exactly what it locks"
        return
    root = cast(dict[str, Any], cast(dict[str, Any], lock.get("packages") or {}).get("") or {})
    for found in (lock.get("version"), root.get("version")):
        if found is not None and found != VERSION:
            yield f"package-lock.json says version {found!r}; run npm install after setting package.json's"
            return


def check_hacs(hacs: Mapping[str, Any]) -> Iterator[str]:
    """HACS installs the bundle a release carries, on the Home Assistant the card names."""
    name = hacs.get("name")
    if not isinstance(name, str) or not name.strip():
        yield "hacs.json must give the card's name in name"
    error = filename_error(hacs.get("filename"))
    if error is not None:
        yield error
    minimum = hacs.get("homeassistant")
    if not isinstance(minimum, str) or not _version(minimum):
        yield "hacs.json must give the oldest Home Assistant the card supports in homeassistant, such as '2026.1.0'"
    if "zip_release" in hacs:
        yield "hacs.json must not set zip_release; HACS installs the bundle itself, not a zip"
    if hacs.get("content_in_root"):
        # HACS skips a release's assets when the content is in the root.
        yield "hacs.json must not set content_in_root; HACS would not install the bundle the release carries"


def check_untracked(tracked: list[str]) -> Iterator[str]:
    """Nothing under dist/ is committed: the bundle is built by the release, with its version."""
    for path in tracked:
        yield f"{path} is committed; dist/ is built, and must be in .gitignore"


def tracked(root: Path) -> list[str]:
    """The files git tracks under dist/ in the repository at `root`."""
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--", DIST],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def check(root: Path) -> list[str]:
    """Every broken promise of the repository at `root`."""
    lock = root / "package-lock.json"
    return [
        *check_package(_json(root / "package.json")),
        *check_lock(_json(lock) if lock.is_file() else None),
        *check_hacs(_json(root / "hacs.json")),
        *check_untracked(tracked(root)),
    ]


def main(arguments: list[str]) -> None:
    """Run the check `arguments` names."""
    match arguments:
        case [root]:
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
