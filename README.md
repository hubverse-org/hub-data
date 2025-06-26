# hubdata

Python tools for accessing and working with hubverse Hub data

## Basic usage

> Note: This package is based on the [python version](https://arrow.apache.org/docs/python/index.html) of Apache's [Arrow library](https://arrow.apache.org/docs/index.html).

1. Use `connect_hub()` to get a `HubConnection` object for a local hub directory. (NB: Currently we only support connecting to local hub directories and not S3 hubs. We anticipate adding support for the latter shortly.)
2. Call `HubConnection.get_dataset()` to get a pyarrow [Dataset](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Dataset.html) for the hub's model output directory.
3. Work with the data by either calling functions directly on the dataset (not as common) or calling [Dataset.to_table()](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Dataset.html#pyarrow.dataset.Dataset.to_table) to read the data into a [pyarrow Table](https://arrow.apache.org/docs/python/generated/pyarrow.Table.html) . You can use pyarrow's [compute functions](https://arrow.apache.org/docs/python/compute.html) or convert the table to another format, such as [Polars](https://docs.pola.rs/api/python/dev/reference/api/polars.from_arrow.html) or [pandas](https://arrow.apache.org/docs/python/generated/pyarrow.Table.html#pyarrow.Table.to_pandas).

For example, here is code using native pyarrow commands to count the number of rows total in the `test/hubs/flu-metrocast` test hub, and then to get the unique locations in the dataset as a python list.

First, start a python interpreter with the required libraries:

```bash
cd /<path_to_repos>/hub-data/
uv run python3
```

Then run the following Python code. (Note that we've included Python output in comments.)

```python
from pathlib import Path
from hubdata import connect_hub
import pyarrow.compute as pc


hub_connection = connect_hub(Path('test/hubs/flu-metrocast'))
hub_ds = hub_connection.get_dataset()
hub_ds.count_rows()
# 14895

pa_table = hub_ds.to_table()  # load all hub data into memory as a pyarrow Table
pc.unique(pa_table['location']).to_pylist()
# ['Bronx', 'Brooklyn', 'Manhattan', 'NYC', 'Queens', 'Staten Island', 'Austin', 'Dallas', 'El Paso', 'Houston', 'San Antonio']

pc.unique(pa_table['target']).to_pylist()
# ['ILI ED visits', 'Flu ED visits pct']
```

## Memory considerations for large datasets

As mentioned above, we use the pyarrow [Dataset.to_table()](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Dataset.html#pyarrow.dataset.Dataset.to_table) function to load a dataset into a [pyarrow Table](https://arrow.apache.org/docs/python/generated/pyarrow.Table.html) . For example, continuing the above Python session:

```python
# naive approach to getting a table: load entire dataset into memory
pa_table = hub_ds.to_table()

print(pa_table.column_names)
# ['reference_date', 'target', 'horizon', 'location', 'target_end_date', 'output_type', 'output_type_id', 'value', 'model_id']

print(pa_table.shape)
# (14895, 9)
```

However, that function reads the entire dataset into memory, which could be unnecessary or fail for large hubs. A more parsimonious approach is to use the [Dataset.to_table()](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Dataset.html#pyarrow.dataset.Dataset.to_table) `columns` and `filter` arguments to select and filter only the information of interest and limit what data is pulled into memory:

```python
# more parsimonious approach: load a subset of the data into memory (select only `target_end_date` and `value`
# associated with `Bronx` as location)
pa_table = hub_ds.to_table(columns=['target_end_date', 'value'],
                           filter=pc.field('location') == 'Bronx')

print(pa_table.shape)
# (1350, 2)
```

## `HubConnection.to_table()` helper function

If you just want the pyarrow Table and don't need the pyarrow Dataset returned by `HubConnection.get_dataset()` then you can use the `HubConnection.to_table()` helper function, which calls `HubConnection.get_dataset()` for you and then passes its args through to `Dataset.to_table()`. So the above example in full would be:

```python
from pathlib import Path
from hubdata import connect_hub
import pyarrow.compute as pc


hub_connection = connect_hub(Path('test/hubs/flu-metrocast'))
pa_table = hub_connection.to_table(columns=['target_end_date', 'value'],
                                   filter=pc.field('location') == 'Bronx')
print(pa_table.shape)
# (1350, 2)
```

## Working with a cloud-based hub

This package supports connecting to cloud-based hubs (primarily AWS S3 for the hubverse) via pyarrow's [abstract filesystem interface](https://arrow.apache.org/docs/python/filesystems.html), which works with both local file systems and those on the cloud. Here's an example of accessing the hubverse bucket **example-complex-forecast-hub** (arn:aws:s3:::example-complex-forecast-hub) via the S3 URI **s3://example-complex-forecast-hub/**. For example, continuing the above Python session:

```python
hub_connection = connect_hub('s3://example-complex-forecast-hub/')
print(hub_connection.to_table().shape)
# (553264, 9)
```

The cli tool also works with S3 URIs:

```bash
uv run hubdata dataset s3://example-complex-forecast-hub/
╭─ s3://example-complex-forecast-hub/ ─────╮
│                                          │
│  hub_path:                               │
│  - s3://example-complex-forecast-hub/    │
│                                          │
│  schema:                                 │
│  - horizon: int32                        │
│  - location: string                      │
│  - model_id: string                      │
│  - output_type: string                   │
│  - output_type_id: string                │
│  - reference_date: date32                │
│  - target: string                        │
│  - target_end_date: date32               │
│  - value: double                         │
│                                          │
│  dataset:                                │
│  - files: 12                             │
│  - types: parquet (found) | csv (admin)  │
│  - rows: 553,264                         │
│                                          │
╰──────────────────────────────── hubdata ─╯
```

> Note: This package's performance with cloud-based hubs can be slow due to how pyarrow's dataset scanning works.

## Working with data outside pyarrow: A Polars example

As mentioned above, once you have a [pyarrow Table](https://arrow.apache.org/docs/python/generated/pyarrow.Table.html) you can convert it to work with dataframe packages like [pandas](https://pandas.pydata.org/) and [Polars](https://docs.pola.rs/). Here we give an example of using the flu-metrocast test hub.

First start a python session, installing the Polars package on the fly using `uv run`'s [--with argument](https://docs.astral.sh/uv/concepts/projects/run/#requesting-additional-dependencies):

```bash
uv run --with polars python3
```

Then run the following Python commands to see Polars integration in action:

```python
from pathlib import Path

import polars as pl
import pyarrow.compute as pc
from hubdata import connect_hub


# connect to the hub and then get a pyarrow Table, limiting the columns and rows loaded into memory as described above 
hub_connection = connect_hub(Path('test/hubs/flu-metrocast'))
pa_table = hub_connection.to_table(
    columns=['target_end_date', 'value', 'output_type', 'output_type_id', 'reference_date'],
    filter=(pc.field('location') == 'Bronx') & (pc.field('target') == 'ILI ED visits'))

pa_table.shape
# (1350, 5)

# convert to polars DataFrame
pl_df = pl.from_arrow(pa_table)
pl_df
# shape: (1_350, 5)
# ┌─────────────────┬─────────────┬─────────────┬────────────────┬────────────────┐
# │ target_end_date ┆ value       ┆ output_type ┆ output_type_id ┆ reference_date │
# │ ---             ┆ ---         ┆ ---         ┆ ---            ┆ ---            │
# │ date            ┆ f64         ┆ str         ┆ f64            ┆ date           │
# ╞═════════════════╪═════════════╪═════════════╪════════════════╪════════════════╡
# │ 2025-01-25      ┆ 1375.608634 ┆ quantile    ┆ 0.025          ┆ 2025-01-25     │
# │ 2025-01-25      ┆ 1503.974675 ┆ quantile    ┆ 0.05           ┆ 2025-01-25     │
# │ 2025-01-25      ┆ 1580.89009  ┆ quantile    ┆ 0.1            ┆ 2025-01-25     │
# │ 2025-01-25      ┆ 1630.75     ┆ quantile    ┆ 0.25           ┆ 2025-01-25     │
# │ 2025-01-25      ┆ 1664.0      ┆ quantile    ┆ 0.5            ┆ 2025-01-25     │
# │ …               ┆ …           ┆ …           ┆ …              ┆ …              │
# │ 2025-06-14      ┆ 386.850998  ┆ quantile    ┆ 0.5            ┆ 2025-05-24     │
# │ 2025-06-14      ┆ 454.018488  ┆ quantile    ┆ 0.75           ┆ 2025-05-24     │
# │ 2025-06-14      ┆ 538.585477  ┆ quantile    ┆ 0.9            ┆ 2025-05-24     │
# │ 2025-06-14      ┆ 600.680743  ┆ quantile    ┆ 0.95           ┆ 2025-05-24     │
# │ 2025-06-14      ┆ 658.922076  ┆ quantile    ┆ 0.975          ┆ 2025-05-24     │
# └─────────────────┴─────────────┴─────────────┴────────────────┴────────────────┘

# it's also possible to convert to a polars DataFrame and do some operations
pl_df = (
    pl.from_arrow(pa_table)
    .group_by(pl.col('target_end_date'))
    .agg(pl.col('value').count())
    .sort('target_end_date')
)
pl_df
# shape: (22, 2)
# ┌─────────────────┬───────┐
# │ target_end_date ┆ value │
# │ ---             ┆ ---   │
# │ date            ┆ u32   │
# ╞═════════════════╪═══════╡
# │ 2025-01-25      ┆ 9     │
# │ 2025-02-01      ┆ 18    │
# │ 2025-02-08      ┆ 27    │
# │ 2025-02-15      ┆ 36    │
# │ 2025-02-22      ┆ 45    │
# │ …               ┆ …     │
# │ 2025-05-24      ┆ 81    │
# │ 2025-05-31      ┆ 63    │
# │ 2025-06-07      ┆ 45    │
# │ 2025-06-14      ┆ 27    │
# │ 2025-06-21      ┆ 9     │
# └─────────────────┴───────┘
```

## Run commands locally

Following are some useful local commands for testing and trying out the package's features. The package follows the [Hubverse Python package standard](https://docs.hubverse.io/en/latest/developer/python.html), and in particular uses [uv](https://docs.astral.sh/uv/) for managing Python versions, virtual environments, and dependencies.

Note that all commands should be run from this repository's root, i.e., first do:

```bash
cd /<path_to_repos>/hub-data/
```

### app (hubdata)

The package provides a CLI called `hubdata` (defined in `pyproject.toml`'s "project.scripts" table). Here's an example of running the command to print a test hub's schema and its dataset info:

```bash
uv run hubdata schema test/hubs/flu-metrocast
╭─ flu-metrocast ─────────────╮
│                             │
│  hub_path:                  │
│  - test/hubs/flu-metrocast  │
│                             │
│  schema:                    │
│  - horizon: int32           │
│  - location: string         │
│  - model_id: string         │
│  - output_type: string      │
│  - output_type_id: double   │
│  - reference_date: date32   │
│  - target: string           │
│  - target_end_date: date32  │
│  - value: double            │
│                             │
╰─────────────────── hubdata ─╯

uv run hubdata dataset test/hubs/flu-metrocast
╭─ flu-metrocast ─────────────╮
│                             │
│  hub_path:                  │
│  - test/hubs/flu-metrocast  │
│                             │
│  schema:                    │
│  - horizon: int32           │
│  - location: string         │
│  - model_id: string         │
│  - output_type: string      │
│  - output_type_id: double   │
│  - reference_date: date32   │
│  - target: string           │
│  - target_end_date: date32  │
│  - value: double            │
│                             │
│  dataset:                   │
│  - files: 31                │
│  - rows: 14,895             │
│                             │
╰─────────────────── hubdata ─╯
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
