# hubdata

Python tools for accessing and working with hubverse Hub data

## Run commands locally

Following are some useful local commands for testing and trying out the package's features. The pacakge follows the [Hubverse Python package standard](https://docs.hubverse.io/en/latest/developer/python.html), and in particular uses [uv](https://docs.astral.sh/uv/) for managing Python versions, virtual environments, and dependencies.

Note that all commands should be run from this repository's root, i.e., first do:

```bash
cd /<path_to_repos>/hub-data/
```

### app (hubdata)

The package provides a CLI called `hubdata` (defined in `pyproject.toml`'s "project.scripts" table). Here's an example of running the command to print a test hub's schema:

```bash
uv run hubdata schema test/hubs/example-complex-scenario-hub
```

### tests (pytest)

Use this command to run tests via [pytest](https://docs.pytest.org/en/stable/):

```bash
uv run pytest
```

### linter (ruff)

Run this command to invoke the [ruff](https://github.com/astral-sh/ruff) code formatter.

```bash
uv run ruff check
```

### coverage (coverage)

Run this command to generate a _text_ [coverage](https://coverage.readthedocs.io/en/7.8.2/) report:

```bash
uv run --frozen coverage run -m pytest
uv run --frozen coverage report
rm .coverage
```

This command generates an _html_ report:

```bash
uv run --frozen coverage html
rm -rf htmlcov/index.html
```

### type checking (mypy)

Use this command to do some optional static type checking using [mypy](https://mypy-lang.org/):

```bash
uv tool run mypy . --ignore-missing-imports --disable-error-code=attr-defined
```
