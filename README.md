# hubdata

Python tools for accessing and working with hubverse Hub data

## running commands locally

All commands should be run from this repository's root, i.e., first do:

```bash
cd /<path_to_repos>/hub-data/
```

### app

Print a test hub's schema:

```bash
uv run hubdata schema test/hubs/example-complex-scenario-hub
```

### linter (ruff)

```bash
uv run ruff check
```

### tests (pytest)

```bash
uv run pytest
```

### coverage (coverage)

To generate a text report:

```bash
uv run --frozen coverage run -m pytest
uv run --frozen coverage report
rm .coverage
```

To generate a html report:

```bash
uv run --frozen coverage html
rm -rf htmlcov/index.html
```

### type checking (mypy)

```bash
uv tool run mypy . --ignore-missing-imports --disable-error-code=attr-defined
```

->

	src/hubdata/hub_schema.py:31: error: Argument 2 to "_columns_for_model_task" has incompatible type "tuple[tuple[str, Any]] | None"; expected "tuple[tuple[str, Any]]"  [arg-type]
	src/hubdata/hub_schema.py:41: error: Argument 1 to "_pa_type_for_hub_type" has incompatible type "str | None"; expected "str"  [arg-type]
	Found 2 errors in 1 file (checked 10 source files)
