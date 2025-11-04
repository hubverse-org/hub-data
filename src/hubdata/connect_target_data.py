from pathlib import Path

import pyarrow as pa
import pyarrow.dataset as ds
from pyarrow import fs

from hubdata.connect_hub import HubConnection, connect_hub
from hubdata.create_target_data_schema import TargetType, create_target_data_schema


class TargetDataConnection:
    """
    Returned by `connect_target_data()`, is the primary way of interacting with a hub's target data.

    Instance variables:
    - target_type: the TargetType passed to the constructor
    - hub_conn: a HubConnection for the passed `hub_path`
    - found_file_info: a fs.FileInfo that's the target data source as returned by `_validate_target_data()`
    - schema: the pa.Schema for `get_dataset()` as returned by `create_target_data_schema()`. note that it is None if
    the schema is to be inferred from data
    """


    def __init__(self, hub_path: str | Path, target_type: TargetType):
        """
        :param hub_path: str or Path pointing to a hub's root directory as passed to `connect_target_data()`
        """
        self.target_type = target_type

        # raises RuntimeError if hub_path is invalid:
        self.hub_conn = connect_hub(hub_path)

        # raises RuntimeError if hub has no target data:
        self.found_file_info = self._validate_target_data(self.hub_conn, self.target_type == TargetType.TIME_SERIES)

        self.schema = create_target_data_schema(self.hub_conn.hub_path, self.target_type)


    @staticmethod
    def _validate_target_data(hub_conn: HubConnection, is_time_series: bool) -> fs.FileInfo:
        """
        `__init()__` helper that validates target data (either time-series or oracle-output) by looking for the three
        supported cases:

        - a csv file (time-series.csv or oracle-output.csv)
        - a parquet file (time-series.parquet or oracle-output.parquet)
        - a partitioned directory (time-series/ or oracle-output/ )

        :param hub_conn: the hub's HubConnection
        :param is_time_series: True if output is for time-series target data, and False if for oracle-output target data
        :return: the fs.FileInfo of the single found target data file or dir
        :raise: RuntimeError if hub has no time-series target data file or dir
        """
        target_data_name = 'time-series' if is_time_series else 'oracle-output'
        file_infos: list[fs.FileInfo] = [
            hub_conn._filesystem.get_file_info(f'{hub_conn._filesystem_path}/{file_or_dir}')
            for file_or_dir in
            [f'target-data/{target_data_name}.csv', f'target-data/{target_data_name}.parquet',
             f'target-data/{target_data_name}/']]
        found_file_infos = [_ for _ in file_infos if _.type != fs.FileType.NotFound]
        if len(found_file_infos) == 0:  # none were found
            raise RuntimeError(
                f'did not find {target_data_name}.csv, {target_data_name}.parquet, or {target_data_name}/')

        if len(found_file_infos) > 1:  # more than one was found
            found_names = ', '.join([repr(_.base_name) for _ in found_file_infos])
            raise RuntimeError(f'found more than one {target_data_name}.csv, {target_data_name}.parquet, or '
                               f'{target_data_name}/ : {found_names}')

        return found_file_infos[0]


    def get_dataset(self):
        """
        Main entry point for getting a pyarrow dataset to work with.

        :return: a `ds.Dataset` for the passed `hub_path`. note that we return a dataset for the single file cases so
            that the user can control when data is materialized into memory. The returned Dataset's schema will be as
            returned by `create_target_data_schema()`, which returns None if `hub_path` has no
            `hub-config/target-data.json` file, causing the schema to be inferred from the data.
        """
        if self.found_file_info.is_file:  # it's `target-data/time-series.csv` or `target-data/time-series.parquet`
            file_format, partitioning = self.found_file_info.extension, None
        else:  # it's `target-data/time-series/`
            file_format, partitioning = 'parquet', 'hive'
        return ds.dataset(self.found_file_info.path, filesystem=self.hub_conn._filesystem, schema=self.schema,
                          format=file_format, partitioning=partitioning, )


    def to_table(self, *args, **kwargs) -> pa.Table:
        """
        A convenience function that simply passes args and kwargs to `pyarrow.dataset.Dataset.to_table()`, returning the
        `pyarrow.Table`.
        """
        return self.get_dataset().to_table(*args, **kwargs)


def connect_target_data(hub_path: str | Path, target_type: TargetType) -> TargetDataConnection:
    """
    Top-level function for accessing the time-series target data or oracle-output target data for the passed `hub_path`.
    Like `connect_hub.connect_hub()` returns a "connection" object (`TargetDataConnection` in this case) that is used to
    both access useful instance variables, but mainly to get a Dataset via `TargetDataConnection.get_dataset()`, similar
    to `HubConnection.get_dataset()`.

    :param hub_path: str (for local file system hubs or cloud based ones) or Path (local file systems only) pointing to
        a hub's root directory. It is passed to https://arrow.apache.org/docs/python/generated/pyarrow.fs.FileSystem.html#pyarrow.fs.FileSystem.from_uri
        From that page: Recognized URI schemes are “file”, “mock”, “s3fs”, “gs”, “gcs”, “hdfs” and “viewfs”. In
        addition, the argument can be a local path, either a pathlib.Path object or a str. NB: Passing a local path as a
        str requires an ABSOLUTE path, but passing the hub as a Path can be a relative path.
    :param target_type: a TargetType specifying the target data type

    :return a TargetDataConnection
    :raise: RuntimeError if `hub_path` is invalid
    :raise: RuntimeError if hub has no time-series target data or oracle-output target data, i.e., no
    `target-data/time-series.csv`, `target-data/time-series.parquet`, or `target-data/time-series/` files/dir (for
    the time-series case), or `target-data/oracle-output.csv`, `target-data/oracle-output.parquet`, or
    `target-data/oracle-output/` files/dir (for the oracle-output case)
    """
    return TargetDataConnection(hub_path, target_type)
