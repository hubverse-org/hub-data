# Command-line interface

The package provides a command-line interface (CLI) called `hubdata` which provides the following subcommands:

- `schema`: Print a hub's schema, i.e., the columns and datatypes that are inferred from the hub's [tasks.json](https://docs.hubverse.io/en/latest/user-guide/hub-config.html) file.
- `dataset`: Print summary information about the data in a hub's [model output directory](https://docs.hubverse.io/en/latest/user-guide/model-output.html). It also includes the same information as the `schema` subcommand. Note that this command can take some time to run as it must scan all data files in the hub.
- `time-series`: Print a hub's [time series target data](https://docs.hubverse.io/en/latest/user-guide/target-data.html#time-series) information, including its schema.
- `oracle-output`: Print a hub's [oracle output target data](https://docs.hubverse.io/en/latest/user-guide/target-data.html#oracle-output) information, including its schema.

> Note: This package is based on the [python version](https://arrow.apache.org/docs/python/index.html) of Apache's [Arrow library](https://arrow.apache.org/docs/index.html).

> Note: To see command-line help, you can run the `hubdata` command with the `--help` option, with or without a subcommand. For example, `hubdata --help` or `hubdata dataset --help`.

## Show the schema of a test hub (the `schema` subcommand)

> Note: All shell examples assume you're using [Bash](https://en.wikipedia.org/wiki/Bash_(Unix_shell)), and that you first `cd` into this repo's root directory, e.g., `cd /<path_to_repos>/hub-data/` .

Here's an example of running the `schema` subcommand on the [flu-metrocast test hub](https://github.com/hubverse-org/hub-data/tree/main/test/hubs/flu-metrocast) included in this package. We use the `pwd` shell command to create the absolute path that the app requires.

```bash
hubdata schema "$(pwd)/test/hubs/flu-metrocast"
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

- `hub_path`: argument passed to the app (here we show **/<path_to_repos>/
  **, but your output will show the actual directory location)
- `schema`: schema obtained via the API's `create_hub_schema()` function

## Show model output information of a test hub (the `dataset` subcommand)

Here's the output from running the `dataset` subcommand on the same test hub:

```bash
hubdata dataset "$(pwd)/test/hubs/flu-metrocast"
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

## Show model output information of an S3-based hub (the `dataset` subcommand)

The CLI command also works with [S3 URIs](https://repost.aws/questions/QUFXlwQxxJQQyg9PMn2b6nTg/what-is-s3-uri-in-simple-storage-service). Here we run it against the cloud-enabled [example-complex-forecast-hub](https://github.com/hubverse-org/example-complex-forecast-hub)'s S3 bucket:

> Note: An [S3 URI](https://repost.aws/questions/QUFXlwQxxJQQyg9PMn2b6nTg/what-is-s3-uri-in-simple-storage-service) (Uniform Resource Identifier) for Amazon S3 has the format
**s3://\<bucket-name\>/\<key-name\>**. It uniquely identifies an object stored in an S3 bucket. For example, **s3:
//my-bucket/data.txt** refers to a file named **data.txt** within the bucket named **my-bucket**.

```bash
hubdata dataset s3://example-complex-forecast-hub/
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
│                                          │
╰──────────────────────────────── hubdata ─╯
```

> Note: This package's performance with cloud-based hubs can be slow due to how pyarrow's dataset scanning works.

## Show time series target data for flu-metrocast (the `time-series` subcommand)

Here we look at the time series target data for a local clone of the [flu-metrocast](https://github.com/reichlab/flu-metrocast) hub:

```bash
hubdata time-series /<path_to_repos>/flu-metrocast
╭─ target data ─────────────────────────────────╮
│                                               │
│  hub_path:                                    │
│  - /<path_to_repos>/flu-metrocast             │
│                                               │
│  target type:                                 │
│  - time-series                                │
│                                               │
│  schema:                                      │
│  - None (inferred from data)                  │
│                                               │
│  dataset:                                     │
│  - location: time-series.csv (file)           │
│  - files: 1                                   │
│  - type: csv                                  │
│                                               │
╰───────────────────────────────────── hubdata ─╯
```

Output explanation:

- `hub_path`: same as above example
- `target type`: indicates what target data was obtained, either `time-series` or `oracle-output`
- `schema`: either column and type information as shown above examples, or (in this case) `None (inferred from data)` if no [target data configuration](https://docs.hubverse.io/en/latest/user-guide/target-data.html#target-data-configuration) (`target-data.json` file) was found.
- `dataset`: information about files in the hub's target data, either time series (in this case) or oracle output
    - `location`: where the target data is stored in the hub (see [File formats](https://docs.hubverse.io/en/latest/user-guide/target-data.html#file-formats) for details). shows the file or directory name followed by either an indication of the type, either `(file)` (in this case) or `(dir)`, respectively
    - `files`: number of files in the dataset
    - `type`: the file type found in the dataset

## Show oracle output target data for the v6_target_dir test hub (the `oracle-output` subcommand)

Here's an example of showing oracle-output target data from the [v6_target_dir](https://github.com/hubverse-org/hub-data/tree/main/test/hubs/v6_target_dir) included in this package.

```bash
hubdata oracle-output "$(pwd)/test/hubs/v6_target_dir"
╭─ target data ────────────────────────────────────────────────────╮
│                                                                  │
│  hub_path:                                                       │
│  - /<path_to_repos>/hub-data/test/hubs/v6_target_dir             │
│                                                                  │
│  target type:                                                    │
│  - oracle-output                                                 │
│                                                                  │
│  schema:                                                         │
│  - location: string                                              │
│  - oracle_value: double                                          │
│  - output_type: string                                           │
│  - output_type_id: string                                        │
│  - target: string                                                │
│  - target_end_date: date32                                       │
│                                                                  │
│  dataset:                                                        │
│  - location: oracle-output (dir)                                 │
│  - files: 5                                                      │
│  - type: parquet                                                 │
│                                                                  │
╰──────────────────────────────────────────────────────── hubdata ─╯
```

Output explanation:

- `hub_path`: same as above example
- `target type`: ""
- `schema`: column and type information (`target-data.json` file was found)
- `dataset`: information about files in the hub's target data (time series or oracle output):
    - `location`: same as above example, but `(dir)`, in this case
    - `files`: same as above example
    - `type`: ""
