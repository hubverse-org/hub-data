from pathlib import Path

import pyarrow.dataset as ds
from pyarrow import fs

from hubdata import connect_hub
from hubdata.create_timeseries_schema import create_timeseries_schema


def connect_target_timeseries(hub_path: str | Path) -> ds.dataset:
    """
    Top-level function for accessing the time-series data for the passed `hub_path`.

    :param hub_path: str (for local file system hubs or cloud based ones) or Path (local file systems only) pointing to
        a hub's root directory. it is passed to https://arrow.apache.org/docs/python/generated/pyarrow.fs.FileSystem.html#pyarrow.fs.FileSystem.from_uri
        From that page: Recognized URI schemes are “file”, “mock”, “s3fs”, “gs”, “gcs”, “hdfs” and “viewfs”. In
        addition, the argument can be a local path, either a pathlib.Path object or a str. NB: Passing a local path as a
        str requires an ABSOLUTE path, but passing the hub as a Path can be a relative path.
    :return: a `ds.dataset` for the passed `hub_path`. note that we return a dataset for the single file cases so that
        the user can control when data is materialized into memory
    :raise: RuntimeError if `hub_path` is invalid
    :raise: RuntimeError if hub has no `hub-config/target-data.json` file
    :raise: RuntimeError if hub has no target-data, i.e., no `target-data/time-series.csv`,
        `target-data/time-series.parquet`, or `target-data/time-series/` files/dir
    """
    hub_conn = connect_hub(hub_path)  # raises RuntimeError if hub_path is invalid

    # validate time-series data by looking for the three supported cases: time-series.csv, time-series.parquet, or a
    # time-series/ directory
    file_infos: list[fs.FileInfo] = [
        hub_conn._filesystem.get_file_info(f'{hub_conn._filesystem_path}/{file_or_dir}') for file_or_dir in
        ['target-data/time-series.csv', 'target-data/time-series.parquet', 'target-data/time-series/']
    ]
    found_file_infos = [_ for _ in file_infos if _.type != fs.FileType.NotFound]
    if len(found_file_infos) == 0:  # none were found
        raise RuntimeError('did not find time-series.csv, time-series.parquet, or time-series/')

    if len(found_file_infos) > 1:  # more than one was found
        raise RuntimeError(f'found more than one time-series.csv, time-series.parquet, or time-series/ : '
                           f'{', '.join([repr(_.base_name) for _ in found_file_infos])}')

    # create a Dataset for the time-series data in hub_path, depending on whether it's a file or a partitioned dir
    found_file_info = found_file_infos[0]
    if found_file_info.is_file:  # it's `target-data/time-series.csv` or `target-data/time-series.parquet`
        file_format, partitioning = found_file_info.extension, None
    else:  # it's `target-data/time-series/`
        file_format, partitioning = 'parquet', 'hive'
    ts_schema = create_timeseries_schema(hub_path)
    return ds.dataset(found_file_info.path, filesystem=hub_conn._filesystem, schema=ts_schema, format=file_format,
                      partitioning=partitioning, )
