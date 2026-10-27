"""The files every integration's repository shares, word for word, with this template.

    template.py check ROOT   fails with one error per file of the repository at ROOT that
                             differs from the template
    template.py sync ROOT    makes the repository at ROOT agree with the template

Every file under template/ is copied as it is, except CLAUDE.md: the repository's CLAUDE.md holds
it between two marker lines, after the repository's own conventions. The repository's workflows
are exactly the template's, and it keeps no workflow scripts or actions of its own: they all come
from this repository.
"""

import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

TEMPLATE = Path(__file__).parents[1] / "template"
SECTION = "CLAUDE.md"
BEGIN = "<!-- BEGIN ha_integration_workflows: shared by every integration; edit it there -->"
END = "<!-- END ha_integration_workflows -->"
OWN = (".github/scripts", ".github/actions")
"""Directories the repository must not have: what they held comes from this repository."""


def files(template: Path = TEMPLATE) -> list[str]:
    """The template's files, as paths relative to it, but for the CLAUDE.md section."""
    return sorted(
        path.relative_to(template).as_posix()
        for path in template.rglob("*")
        if path.is_file() and path.relative_to(template).as_posix() != SECTION
    )


def section(text: str) -> str | None:
    """The shared section of the CLAUDE.md `text`, markers included, None without one."""
    start = text.find(BEGIN)
    end = text.find(END)
    if start < 0 or end < start:
        return None
    return text[start : end + len(END)]


def shared_section(template: Path = TEMPLATE) -> str:
    """The shared section as the template has it, between its markers."""
    return f"{BEGIN}\n{(template / SECTION).read_text('utf-8').strip()}\n{END}"


def differences(root: Path, template: Path = TEMPLATE) -> Iterator[str]:
    """Every way the repository at `root` differs from the template."""
    for name in files(template):
        own = root / name
        if not own.is_file():
            yield f"{name} is missing; the template has it"
        elif own.read_bytes() != (template / name).read_bytes():
            yield f"{name} differs from the template's"
    workflows = {f".github/workflows/{path.name}" for path in (root / ".github/workflows").glob("*")}
    for name in sorted(workflows - set(files(template))):
        yield f"{name} is no workflow of the template; workflows are shared, not added per repository"
    for name in OWN:
        if (root / name).exists():
            yield f"{name} must not exist; it comes from the template"
    claude = root / SECTION
    found = section(claude.read_text("utf-8")) if claude.is_file() else None
    if found is None:
        yield f"{SECTION} lacks the shared section between {BEGIN!r} and {END!r}"
    elif found != shared_section(template):
        yield f"the shared section of {SECTION} differs from the template's"


def sync(root: Path, template: Path = TEMPLATE) -> None:
    """Make the repository at `root` agree with the template."""
    names = files(template)
    for name in names:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template / name, target)
    for path in (root / ".github/workflows").glob("*"):
        if f".github/workflows/{path.name}" not in names:
            path.unlink()
    for name in OWN:
        if (root / name).exists():
            shutil.rmtree(root / name)
    claude = root / SECTION
    text = claude.read_text("utf-8") if claude.is_file() else ""
    found = section(text)
    shared = shared_section(template)
    if found is None:
        text = f"{text.rstrip()}\n\n{shared}\n" if text.strip() else f"{shared}\n"
    else:
        text = text.replace(found, shared)
    claude.write_text(text, "utf-8")


def main(arguments: list[str]) -> None:
    """Run the subcommand `arguments` names."""
    match arguments:
        case ["check", root]:
            found = list(differences(Path(root)))
            for difference in found:
                print(f"::error::{difference}")
            if found:
                print("Run tools/template.py sync from ha_integration_workflows to bring it back.")
                sys.exit(1)
            print("The repository agrees with the template.")
        case ["sync", root]:
            sync(Path(root))
        case _:
            sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
