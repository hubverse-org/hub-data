# Development commands

Following are some useful local commands for testing and trying out the package's features. The package follows the [Hubverse Python package standard](https://docs.hubverse.io/en/latest/developer/python.html), and in particular uses [uv](https://docs.astral.sh/uv/) for managing Python versions, virtual environments, and dependencies.

> Note: All shell examples assume you're using [Bash](https://en.wikipedia.org/wiki/Bash_(Unix_shell)), and that you first `cd` into this repo's root directory (e.g., `cd /<path_to_repos>/hub-data/`).
>
> Note: The Python-based directions below use [uv](https://docs.astral.sh/uv/) for managing Python versions, virtual environments, and dependencies, but if you already have a preferred Python toolset, that should work too.

## Run unit tests (pytest)

Use this command to run tests via [pytest](https://docs.pytest.org/en/stable/):

```bash
uv run pytest
```

## Run a linter (ruff)

Run this command to invoke the [ruff](https://github.com/astral-sh/ruff) code formatter.

```bash
uv run ruff check
```

## Run a static type checker (mypy)

Use this command to do some optional static type checking using [mypy](https://mypy-lang.org/):

```bash
uv tool run mypy . --ignore-missing-imports --disable-error-code=attr-defined
```

## Measure code coverage (coverage)

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

## Build documentation

Run the following command to build documentation:

```bash
uv run --group docs sphinx-build docs/source docs/_build/html
```

To do the same and then serve documentation locally for debugging:

```bash
uv run --group docs sphinx-autobuild docs/source docs/_build/html
```

## Build the package and publish to test.pypi.org

First set and export the `UV_PUBLISH_TOKEN` environment variable to a token obtained via your test.pypi.org account and then run:

```bash
uv build
uv publish --index testpypi
```
