import json
from pathlib import Path

import pyarrow as pa

from hubdata import connect_hub
from hubdata.create_hub_schema import _pa_type_for_hub_type


def create_timeseries_schema(hub_path: str | Path) -> pa.schema:
    """
    Top-level function for creating a time-series schema for the passed `hub_path`.

    :param hub_path: str (for local file system hubs or cloud based ones) or Path (local file systems only) pointing to
        a hub's root directory. it is passed to https://arrow.apache.org/docs/python/generated/pyarrow.fs.FileSystem.html#pyarrow.fs.FileSystem.from_uri
        From that page: Recognized URI schemes are “file”, “mock”, “s3fs”, “gs”, “gcs”, “hdfs” and “viewfs”. In
        addition, the argument can be a local path, either a pathlib.Path object or a str. NB: Passing a local path as a
        str requires an ABSOLUTE path, but passing the hub as a Path can be a relative path.
    :return: a `pyarrow.Schema` for the passed `hub_path`
    :raise: RuntimeError if `hub_path` has no `hub-config/target-data.json` file
    """
    hub_conn = connect_hub(hub_path)

    # try to open hub-config/target-data.json
    try:
        with (hub_conn._filesystem.open_input_file(f'{hub_conn._filesystem_path}/hub-config/target-data.json') as fp):
            target_data = json.load(fp)
    except Exception as ex:
        raise RuntimeError(f'target-data.json not found. hubverse schema v6 is required: {ex}')

    # process target-data.json sections, filling col_name_to_pa_type
    col_name_to_pa_type: dict[str, pa.DataType] = {}

    # top-level property: `observable_unit` (required): task ID column names. get types from regular schema
    # (tasks.json). can be overridden by target-type specific configuration
    ts_observable_unit = target_data['time-series']['observable_unit'] \
        if ('time-series' in target_data) and ('observable_unit' in target_data['time-series']) \
        else target_data['observable_unit']
    for column_name in ts_observable_unit:
        col_name_to_pa_type[column_name] = hub_conn.schema.field(column_name).type

    # top-level property: `date_col` (required): date column name. a Date. may or may not be in `observable_unit`
    date_col = target_data['date_col']
    if date_col not in col_name_to_pa_type:
        col_name_to_pa_type[date_col] = pa.date32()

    # top-level property: `versioned` (optional): whether all target type datasets are versioned using `as_of` dates.
    # defaults to False. can be overridden by target-type specific configuration
    ts_versioned = target_data['time-series']['versioned'] \
        if ('time-series' in target_data) and ('versioned' in target_data['time-series']) \
        else target_data['versioned']
    if ts_versioned:
        col_name_to_pa_type['as_of'] = pa.date32()

    # target-type specific configuration: `time-series` > `non_task_id_schema` (optional): additional
    # (column_name:r_data_type) key-value pairs
    non_task_id_schema = target_data['time-series']['non_task_id_schema'] \
        if ('time-series' in target_data) and ('non_task_id_schema' in target_data['time-series']) \
        else {}
    for column_name, hub_type in non_task_id_schema.items():
        col_name_to_pa_type[column_name] = _pa_type_for_hub_type(hub_type)

    # `observation` column: [implicit to time-series data]: same type as `value` from regular schema (tasks.json)
    col_name_to_pa_type['observation'] = hub_conn.schema.field('value').type

    # done
    return pa.schema(col_name_to_pa_type)
