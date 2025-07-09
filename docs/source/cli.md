# Command-line interface

The package provides a command-line interface (CLI) called `hubdata` which provides two subcommands:

This package is based on the [python version](https://arrow.apache.org/docs/python/index.html) of Apache's [Arrow library](https://arrow.apache.org/docs/index.html).

- `schema`: Print a hub's schema, i.e., the columns and datatypes that are inferred from the hub's [tasks.json](https://docs.hubverse.io/en/latest/user-guide/hub-config.html) file.
- `dataset`: Print summary information about the data in a hub's [model output directory](https://docs.hubverse.io/en/latest/user-guide/model-output.html). It also includes the same information as the `schema` subcommand. Note that this command can take some time to run as it must scan all data files in the hub.

## Getting help with the CLI

To see command-line help, you can run the `hubdata` command with the `--help` option, with or without a subcommand. For example:

> Note: All shell examples assume you're using [Bash](https://en.wikipedia.org/wiki/Bash_(Unix_shell)), and that you first `cd` into this repo's root directory, e.g., `cd /<path_to_repos>/hub-data/` .
>
> Note: The Python-based directions below use [uv](https://docs.astral.sh/uv/) for managing Python versions, virtual environments, and dependencies, but if you already have a preferred Python toolset, that should work too.

```bash
uv run hubdata --help
uv run hubdata schema --help
uv run hubdata dataset --help
```

## Show the schema of a test hub - the `schema` subcommand

Here's an example of running the `schema` subcommand on the **flu-metrocast** test hub included in this package. We use the `pwd` shell command to create the absolute path that the app requires.

```bash
uv run hubdata schema "$(pwd)/test/hubs/flu-metrocast"
╭─ schema ─────────────────────────────────────────────────────────╮
│                                                                  │
│  hub_path:                                                       │
│  - /<path_to_repos>/hub-data/test/hubs/flu-metrocast             │
│                                                                  │
│  schema:                                                         │
│  - horizon: int32                                                │
│  - location: string                                              │
│  - model_id: string                                              │
│  - output_type: string                                           │
│  - output_type_id: double                                        │
│  - reference_date: date32                                        │
│  - target: string                                                │
│  - target_end_date: date32                                       │
│  - value: double                                                 │
│                                                                  │
╰──────────────────────────────────────────────────────── hubdata ─╯
```

Output explanation:

- `hub_path`: argument passed to the app (here we show **/<path_to_repos>/**, but your output will show the actual directory location)
- `schema`: schema obtained via the API's `create_hub_schema()` function

## Show model output information of a test hub - the `dataset` subcommand

Here's the output from running the `dataset` subcommand on the same test hub:

```bash
uv run hubdata dataset "$(pwd)/test/hubs/flu-metrocast"
╭─ dataset ────────────────────────────────────────────────────────╮
│                                                                  │
│  hub_path:                                                       │
│  - /<path_to_repos>/hub-data/test/hubs/flu-metrocast             │
│                                                                  │
│  schema:                                                         │
│  - horizon: int32                                                │
│  - location: string                                              │
│  - model_id: string                                              │
│  - output_type: string                                           │
│  - output_type_id: double                                        │
│  - reference_date: date32                                        │
│  - target: string                                                │
│  - target_end_date: date32                                       │
│  - value: double                                                 │
│                                                                  │
│  dataset:                                                        │
│  - files: 31                                                     │
│  - types: csv (found) | csv (admin)                              │
│  - rows: 14,895                                                  │
│                                                                  │
╰──────────────────────────────────────────────────────── hubdata ─╯
```

Output explanation:

- `hub_path`: same as above example
- `schema`: same as above example
- `dataset`: information about files in the hub's model output directory:
    - `files`: number of files in the dataset
    - `types`: list of the file types a) actually found in the dataset (**found**), and b) ones specified in the hub's
      _admin.json_ file (**admin**)
    - `rows`: total number of dataset rows

## Show model output information of an S3-based hub

The CLI command also works with [S3 URIs](https://repost.aws/questions/QUFXlwQxxJQQyg9PMn2b6nTg/what-is-s3-uri-in-simple-storage-service):

> Note: An [S3 URI](https://repost.aws/questions/QUFXlwQxxJQQyg9PMn2b6nTg/what-is-s3-uri-in-simple-storage-service) (Uniform Resource Identifier) for Amazon S3 has the format **s3://\<bucket-name\>/\<key-name\>**. It uniquely identifies an object stored in an S3 bucket. For example, **s3://my-bucket/data.txt** refers to a file named **data.txt** within the bucket named **my-bucket**.

```bash
uv run hubdata dataset s3://example-complex-forecast-hub/
╭─ dataset ────────────────────────────────╮
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
