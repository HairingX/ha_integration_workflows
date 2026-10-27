# Conventions for this repository

The workflows, actions and release tools every repository of the owner shares - the Home
Assistant integrations, and the Python libraries they use - and the templates of the files each
of them keeps a copy of. How and why it is built as it is: `docs/design.md`.

## What lives here

- `common/`: what every kind of repository shares. `common/tools/release_version.py` holds the
  version rules, `common/release-drafter.yml` Release Drafter's configuration, and
  `common/template/` the files every repository keeps word for word: the release-notes
  categories and the branch-names ruleset.
- `ha/`: the Home Assistant integrations'.
  - `ha/actions/tests`, `ha/actions/libraries-released`: composite actions, used by the
    integrations' workflows at `@v2` and by the reusable workflows from their own commit.
  - `ha/tools/`: the scripts the workflows run. They read what differs between integrations
    from the integration's own files - the domain from `custom_components/`, the zip from
    `hacs.json`, the libraries from `[tool.ha-integration-workflows]` in `pyproject.toml` - and
    never name one.
  - `ha/template/`: the files every integration keeps word for word besides the common ones:
    its workflows, which only call the reusable ones, its Dependabot and main-branch ruleset,
    and `ha/template/CLAUDE.md`, the shared section of its CLAUDE.md. The integrations' tests
    check their copies with `ha/tools/template.py check`; `ha/tools/template.py sync
    <repository>` brings one back.
- `.github/workflows/`: the reusable workflows, prefixed by the kind they serve -
  `ha-release.yml`, `ha-test-build.yml`, `ha-test-build-cleanup.yml` - and `release-drafter.yml`,
  shared by every kind. GitHub finds a reusable workflow only directly in that directory. Each
  checks out this repository at its own commit (`job.workflow_repository`, `job.workflow_sha`)
  for its tools. `ci.yml` and `publish.yml` are this repository's own.
- `tests/`: `tests/common/`, `tests/ha/`, and `tests/test_workflows.py` for every workflow and
  action.

## Changing anything

1. Change it here, with its test, through a pull request. CI runs the tests, pyright strict, and
   actionlint with shellcheck on every workflow and every action's script.
2. Publish it: run **Publish** on `main` with the next version. It tags the checked commit and
   moves the major tag to it, so every repository uses it from its next run. There is one
   version for every kind.
3. A change to a template turns the tests of every repository that keeps it red until its
   copies are synced: open a pull request in each with the template's `sync`. A change the
   copies must follow at the same moment - an input added to a reusable workflow, or a path
   moved - is a new major version, published while the repositories stay at the major before
   until each is synced.

The comments, docstrings, tests and branch conventions are the integrations' own, in
`ha/template/CLAUDE.md`. Python 3.14; pyright strict reports 0 errors, with no `# type: ignore`.
