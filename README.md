# workflows

The workflows, actions and release tools shared by the owner's repositories, and the templates
of the files each of them keeps a copy of.

- `common/`: the version rules, Release Drafter's configuration, and the files every repository
  keeps: the release-notes categories and the branch-names ruleset.
- `python/`: for the Python libraries, published on PyPI: Release works out the version, tests
  the exact commit, tags it, builds and checks the package, then publishes to PyPI and GitHub.
- `ha/`: for the Home Assistant integrations, distributed through HACS.
  - Release: works out the version from the tags and the draft release, tests and validates the
    exact commit, builds the zip with the version set only in it, checks it, tags the commit
    and publishes the release. The manifest in the repository always says `0.0.0`.
  - Test build: publishes a development branch as a pre-release for HACS beta users.
  - Release Drafter, Libraries released, Tests and type check, the repository's contract, and
    the check that an integration's shared files agree with the template.

How an integration uses it, and the rules it follows: `ha/template/CLAUDE.md`. How it is built
and why: `docs/design.md`.

## Adding an integration

1. Run `python common/tools/template.py sync ha <path to the integration's repository>`.
2. List the libraries developed alongside it, in the order they install, in its `pyproject.toml`:

   ```toml
   [tool.hairingx-workflows]
   libraries = ["its_library"]
   ```

3. Import `ha/template/.github/rulesets/main.json` and
   `common/template/.github/rulesets/branch-names.json` as rulesets in the repository's
   settings.

## Adding a library

1. Run `python common/tools/template.py sync python <path to the library's repository>`, and
   move the library's own conventions above the shared section of its CLAUDE.md.
2. Pin `pyright`, `pytest` and `pytest-cov` with `==` in its `requirements-test.txt`, and list
   any library it is developed alongside in its `pyproject.toml`:

   ```toml
   [tool.hairingx-workflows]
   libraries = ["its_library"]
   ```

3. Import `python/template/.github/rulesets/main.json` and
   `common/template/.github/rulesets/branch-names.json` as rulesets in the repository's
   settings. PyPI's trusted publisher stays as it is: the workflow `release.yml` and the
   environment `pypi`.
