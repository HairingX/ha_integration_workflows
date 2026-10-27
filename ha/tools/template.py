"""The files every integration's repository shares, word for word, with the templates.

    template.py check ROOT   fails with one error per file of the repository at ROOT that
                             differs from the template
    template.py sync ROOT    makes the repository at ROOT agree with the template

Every file under common/template/ and ha/template/ is copied as it is, except ha/template/CLAUDE.md:
the repository's CLAUDE.md holds it between two marker lines, after the repository's own
conventions. The repository's workflows are exactly the template's, and it keeps no workflow
scripts, actions or Release Drafter configuration of its own: they all come from this repository.
"""

import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

TEMPLATE = Path(__file__).parents[1] / "template"
COMMON = Path(__file__).parents[2] / "common" / "template"
"""The files every repository of the owner shares, whatever its kind."""
SECTION = "CLAUDE.md"
BEGIN = "<!-- BEGIN HairingX/workflows: shared by every integration; edit it there -->"
END = "<!-- END HairingX/workflows -->"
PREVIOUS_MARKERS = (
    ("<!-- BEGIN ha_integration_workflows: shared by every integration; edit it there -->", BEGIN),
    ("<!-- END ha_integration_workflows -->", END),
)
"""The markers of the repository's former name, which sync replaces."""
NOT_OWN = (".github/scripts", ".github/actions", ".github/release-drafter.yml")
"""What the repository must not have: it comes from this repository, where Release Drafter's
configuration is read from too."""


def sources(template: Path = TEMPLATE, common: Path = COMMON) -> dict[str, Path]:
    """Each file the repository keeps, by its path in the repository, and where it comes from."""
    found: dict[str, Path] = {}
    for root in (common, template):
        for path in root.rglob("*"):
            name = path.relative_to(root).as_posix()
            if path.is_file() and not (root == template and name == SECTION):
                if name in found:
                    sys.exit(f"::error::{name} is in both {common} and {template}")
                found[name] = path
    return dict(sorted(found.items()))


def files(template: Path = TEMPLATE, common: Path = COMMON) -> list[str]:
    """The files the repository keeps, as paths relative to it, but for the CLAUDE.md section."""
    return list(sources(template, common))


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


def differences(root: Path, template: Path = TEMPLATE, common: Path = COMMON) -> Iterator[str]:
    """Every way the repository at `root` differs from the template."""
    shared = sources(template, common)
    for name, source in shared.items():
        own = root / name
        if not own.is_file():
            yield f"{name} is missing; the template has it"
        elif own.read_bytes() != source.read_bytes():
            yield f"{name} differs from the template's"
    workflows = {f".github/workflows/{path.name}" for path in (root / ".github/workflows").glob("*")}
    for name in sorted(workflows - set(shared)):
        yield f"{name} is no workflow of the template; workflows are shared, not added per repository"
    for name in NOT_OWN:
        if (root / name).exists():
            yield f"{name} must not exist; it comes from HairingX/workflows"
    claude = root / SECTION
    found = section(claude.read_text("utf-8")) if claude.is_file() else None
    if found is None:
        yield f"{SECTION} lacks the shared section between {BEGIN!r} and {END!r}"
    elif found != shared_section(template):
        yield f"the shared section of {SECTION} differs from the template's"


def sync(root: Path, template: Path = TEMPLATE, common: Path = COMMON) -> None:
    """Make the repository at `root` agree with the template."""
    shared = sources(template, common)
    names = list(shared)
    for name, source in shared.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for path in (root / ".github/workflows").glob("*"):
        if f".github/workflows/{path.name}" not in names:
            path.unlink()
    for name in NOT_OWN:
        path = root / name
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    claude = root / SECTION
    text = claude.read_text("utf-8") if claude.is_file() else ""
    for previous, current in PREVIOUS_MARKERS:
        text = text.replace(previous, current)
    found = section(text)
    shared = shared_section(template)
    if found is None and (BEGIN in text or END in text):
        sys.exit(f"::error::{SECTION} has only one of the markers {BEGIN!r} and {END!r}; fix it by hand")
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
                print("Run ha/tools/template.py sync from HairingX/workflows to bring it back.")
                sys.exit(1)
            print("The repository agrees with the template.")
        case ["sync", root]:
            sync(Path(root))
        case _:
            sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
