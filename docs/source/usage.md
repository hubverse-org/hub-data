# Using the API

This page contains information about using the hubdata API.

## Basic usage

> Note: This package is based on the [python version](https://arrow.apache.org/docs/python/index.html) of Apache's [Arrow library](https://arrow.apache.org/docs/index.html).

1. Use `connect_hub()` to get a `HubConnection` object for a hub directory.
2. Call `HubConnection.get_dataset()` to get a pyarrow [Dataset](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Dataset.html) extracted from the hub's model output directory.
3. Work with the data by either calling functions directly on the dataset (not as common) or calling [Dataset.to_table()](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Dataset.html#pyarrow.dataset.Dataset.to_table) to read the data into a [pyarrow Table](https://arrow.apache.org/docs/python/generated/pyarrow.Table.html) . You can use pyarrow's [compute functions](https://arrow.apache.org/docs/python/compute.html) or convert the table to another format, such as [Polars](https://docs.pola.rs/api/python/dev/reference/api/polars.from_arrow.html) or [pandas](https://arrow.apache.org/docs/python/generated/pyarrow.Table.html#pyarrow.Table.to_pandas).

For example, here is code using native pyarrow commands to count the number of rows total in the `test/hubs/flu-metrocast` test hub, and then to get the unique locations in the dataset as a python list.

First, start a python interpreter with the required libraries:

> Note: All shell examples assume you're using [Bash](https://en.wikipedia.org/wiki/Bash_(Unix_shell)), and that you first `cd` into this repo's root directory, e.g., `cd /<path_to_repos>/hub-data/` .
>
> Note: The Python-based directions below use [uv](https://docs.astral.sh/uv/) for managing Python versions, virtual environments, and dependencies, but if you already have a preferred Python toolset, that should work too.

```bash
uv run python3
```

Then run the following Python code. (We've included Python output in comments.)

```python
from pathlib import Path
from hubdata import connect_hub
import pyarrow.compute as pc


hub_connection = connect_hub(Path('test/hubs/flu-metrocast'))  # relative Path is OK, but str would need to be absolute
hub_ds = hub_connection.get_dataset()
hub_ds.count_rows()
# 14895

pa_table = hub_ds.to_table()  # load all hub data into memory as a pyarrow Table
pc.unique(pa_table['location']).to_pylist()
# ['Bronx', 'Brooklyn', 'Manhattan', 'NYC', 'Queens', 'Staten Island', 'Austin', 'Dallas', 'El Paso', 'Houston', 'San Antonio']

pc.unique(pa_table['target']).to_pylist()
# ['ILI ED visits', 'Flu ED visits pct']
```

> Note: For a hub located in a local file system, `connect_hub()` accepts either a Python [Path](https://docs.python.org/3/library/pathlib.html) or [str](https://docs.python.org/3/library/stdtypes.html) object. A `Path` can be a relative file system path, but a `str` must be an
**absolute
** one. For the [CLI app](cli.md), the path must always be absolute because it's handled as a `str` internally.

## Compute functions

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

## HubConnection.to_table() helper function

If you just want the pyarrow Table and don't need the pyarrow `Dataset` returned by `HubConnection.get_dataset()` then you can use the `HubConnection.to_table()` helper function, which calls `HubConnection.get_dataset()` for you and then passes its args through to the returned `Dataset.to_table()`. So the above example in full would be:

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

This package supports connecting to cloud-based hubs (primarily AWS S3 for the hubverse) via pyarrow's [abstract filesystem interface](https://arrow.apache.org/docs/python/filesystems.html), which works with both local file systems and those on the cloud. Here's an example of accessing the hubverse bucket
**example-complex-forecast-hub** (arn:aws:s3:::example-complex-forecast-hub) via the S3 URI **s3:
//example-complex-forecast-hub/**. For example, continuing the above Python session:

> Note: An [S3 URI](https://repost.aws/questions/QUFXlwQxxJQQyg9PMn2b6nTg/what-is-s3-uri-in-simple-storage-service) (Uniform Resource Identifier) for Amazon S3 has the format
**s3://\<bucket-name\>/\<key-name\>**. It uniquely identifies an object stored in an S3 bucket. For example, **s3:
//my-bucket/data.txt** refers to a file named **data.txt** within the bucket named **my-bucket**.

```python
hub_connection = connect_hub('s3://example-complex-forecast-hub/')
print(hub_connection.to_table().shape)
# (553264, 9)
```

> Note: This package's performance with cloud-based hubs can be slow due to how pyarrow's dataset scanning works.

## Working with data outside pyarrow: A Polars example

As mentioned above, once you have a [pyarrow Table](https://arrow.apache.org/docs/python/generated/pyarrow.Table.html) you can convert it to work with dataframe packages like [pandas](https://pandas.pydata.org/) and [Polars](https://docs.pola.rs/). Here we give an example of using the
**flu-metrocast** test hub.

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
