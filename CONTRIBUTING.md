# Contributing to GraphMind

Thanks for your interest in improving GraphMind. This guide covers local setup, the
development workflow, and conventions for pull requests.

## Development setup

GraphMind requires **Python 3.11+** and **git**.

```bash
# Clone and install with dev dependencies
git clone https://github.com/askaresh/graphmind.git
cd graphmind
pip install -e ".[dev]"

# Copy the example env and fill in your Entra app details
cp .env.example .env       # macOS / Linux
copy .env.example .env     # Windows
```

See [docs/entra_setup.md](docs/entra_setup.md) for app registration and permissions.

## Running checks

Run these before opening a pull request — CI (`.github/workflows/test.yml`) runs the
same commands on every push and PR:

```bash
python -m compileall graphmind     # import / syntax sanity check
python -m pytest tests/ -v          # unit tests
```

Tests use fixtures under `tests/fixtures/` and do **not** require live Graph access or
Entra credentials.

## How the spec index works

GraphMind reads endpoint definitions from Microsoft's public
[msgraph-metadata](https://github.com/microsoftgraph/msgraph-metadata) repo, cloned to
`./msgraph-metadata` (gitignored). The daily refresh (`.github/workflows/refresh.yml`)
diffs the spec and commits the manifest, decommission log, and promotion log. See
[docs/spec_lifecycle.md](docs/spec_lifecycle.md) for the full lifecycle.

## Branch and pull request conventions

- Branch from `main` using a descriptive name (e.g. `fix-pagination-edge-case`,
  `feat-vscode-config`).
- Keep changes focused; one logical change per PR.
- Write clear commit messages: a short imperative summary line, optionally followed by
  a blank line and detail.
- Ensure `compileall` and `pytest` pass locally, and add tests for new behaviour.
- Fill in the pull request template so reviewers have context.

## Reporting issues

Use the [issue templates](.github/ISSUE_TEMPLATE) for bug reports and feature requests.
For security concerns, follow [SECURITY.md](SECURITY.md) instead of opening a public
issue.

## Code of conduct

By participating you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).
