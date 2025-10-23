from pathlib import Path

from pyarrow import dataset as ds
from pyarrow import fs

from hubdata import HubConnection, connect_hub
from hubdata.create_target_data_schema import create_oracle_output_schema, create_timeseries_schema


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
    :raise: RuntimeError if hub has no time-series target data, i.e., no `target-data/time-series.csv`,
        `target-data/time-series.parquet`, or `target-data/time-series/` files/dir
    """
    hub_conn = connect_hub(hub_path)  # raises RuntimeError if hub_path is invalid
    found_file_info = _validate_target_data(hub_conn, True)  # raises RuntimeError if hub has no target data
    return _create_dataset(hub_conn, found_file_info, True)


def connect_target_oracle_output(hub_path: str | Path) -> ds.dataset:
    """
    Top-level function for accessing the oracle-output data for the passed `hub_path`.

    :param hub_path: str (for local file system hubs or cloud based ones) or Path (local file systems only) pointing to
        a hub's root directory. it is passed to https://arrow.apache.org/docs/python/generated/pyarrow.fs.FileSystem.html#pyarrow.fs.FileSystem.from_uri
        From that page: Recognized URI schemes are “file”, “mock”, “s3fs”, “gs”, “gcs”, “hdfs” and “viewfs”. In
        addition, the argument can be a local path, either a pathlib.Path object or a str. NB: Passing a local path as a
        str requires an ABSOLUTE path, but passing the hub as a Path can be a relative path.
    :return: a `ds.dataset` for the passed `hub_path`. note that we return a dataset for the single file cases so that
        the user can control when data is materialized into memory
    :raise: RuntimeError if `hub_path` is invalid
    :raise: RuntimeError if hub has no `hub-config/target-data.json` file
    :raise: RuntimeError if hub has no oracle-output target data, i.e., no `target-data/oracle-output.csv`,
        `target-data/oracle-output.parquet`, or `target-data/oracle-output/` files/dir
    """
    hub_conn = connect_hub(hub_path)  # raises RuntimeError if hub_path is invalid
    found_file_info = _validate_target_data(hub_conn, False)  # raises RuntimeError if hub has no target data
    return _create_dataset(hub_conn, found_file_info, False)


def _validate_target_data(hub_conn: HubConnection, is_time_series: bool) -> fs.FileInfo:
    """
    Helper that validates target data (either time-series or oracle-output) by looking for the three supported cases:
    - a csv file (time-series.csv or oracle-output.csv)
    - a parquet file (time-series.parquet or oracle-output.parquet)
    - a partitioned directory (time-series/ or oracle-output/ )

    :param hub_conn: the hub's HubConnection
    :param is_time_series: True if output is for time-series target data, and False if for oracle-output target data
    :return: the fs.FileInfo of the single found target data file or dir
    :raise: RuntimeError if hub has no time-series target data file or dir
    """
    target_data_name = 'time-series' if is_time_series else 'oracle-output'
    file_infos: list[fs.FileInfo] = [hub_conn._filesystem.get_file_info(f'{hub_conn._filesystem_path}/{file_or_dir}')
                                     for file_or_dir in
                                     [f'target-data/{target_data_name}.csv', f'target-data/{target_data_name}.parquet',
                                      f'target-data/{target_data_name}/']]
    found_file_infos = [_ for _ in file_infos if _.type != fs.FileType.NotFound]
    if len(found_file_infos) == 0:  # none were found
        raise RuntimeError(f'did not find {target_data_name}.csv, {target_data_name}.parquet, or {target_data_name}/')

    if len(found_file_infos) > 1:  # more than one was found
        found_names = ', '.join([repr(_.base_name) for _ in found_file_infos])
        raise RuntimeError(f'found more than one {target_data_name}.csv, {target_data_name}.parquet, or '
                           f'{target_data_name}/ : {found_names}')

    return found_file_infos[0]


def _create_dataset(hub_conn: HubConnection, found_file_info: fs.FileInfo, is_time_series: bool) -> ds.dataset:
    """
    Helper that creates a Dataset for the time-series or oracle-output target data in hub_path, depending on
    `is_time_series`. It handles both cases of a file or a partitioned dir.

    :param hub_conn: the hub's HubConnection
    :param found_file_info: as returned by `_validate_target_data()`
    :param is_time_series: True if output is for time-series target data, and False if for oracle-output target data
    :return: a Dataset for the target data
    """
    if found_file_info.is_file:  # it's `target-data/time-series.csv` or `target-data/time-series.parquet`
        file_format, partitioning = found_file_info.extension, None
    else:  # it's `target-data/time-series/`
        file_format, partitioning = 'parquet', 'hive'
    ts_schema = create_timeseries_schema(hub_conn.hub_path) if is_time_series \
        else create_oracle_output_schema(hub_conn.hub_path)
    return ds.dataset(found_file_info.path, filesystem=hub_conn._filesystem, schema=ts_schema, format=file_format,
                      partitioning=partitioning, )
