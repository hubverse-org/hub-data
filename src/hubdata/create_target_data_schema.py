import json
from pathlib import Path

import pyarrow as pa

from hubdata import HubConnection, connect_hub
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
    target_data = _target_data_json(hub_conn)  # try to open hub-config/target-data.json
    col_name_to_pa_type = _col_name_to_pa_type_for_target_data(hub_conn.schema, target_data, True)
    return pa.schema(col_name_to_pa_type)


def create_oracle_output_schema(hub_path: str | Path) -> pa.schema:
    """
    Top-level function for creating a oracle-output schema for the passed `hub_path`.

    :param hub_path: str (for local file system hubs or cloud based ones) or Path (local file systems only) pointing to
        a hub's root directory. it is passed to https://arrow.apache.org/docs/python/generated/pyarrow.fs.FileSystem.html#pyarrow.fs.FileSystem.from_uri
        From that page: Recognized URI schemes are “file”, “mock”, “s3fs”, “gs”, “gcs”, “hdfs” and “viewfs”. In
        addition, the argument can be a local path, either a pathlib.Path object or a str. NB: Passing a local path as a
        str requires an ABSOLUTE path, but passing the hub as a Path can be a relative path.
    :return: a `pyarrow.Schema` for the passed `hub_path`
    :raise: RuntimeError if `hub_path` has no `hub-config/target-data.json` file
    """
    hub_conn = connect_hub(hub_path)
    target_data = _target_data_json(hub_conn)  # try to open hub-config/target-data.json
    col_name_to_pa_type = _col_name_to_pa_type_for_target_data(hub_conn.schema, target_data, False)
    return pa.schema(col_name_to_pa_type)


def _target_data_json(hub_conn: HubConnection) -> dict:
    """
    Helper that returns the contents of `hub_connection`'s hub-config/target-data.json file.

    :param hub_conn: the hub's HubConnection
    :return: hub-config/target-data.json file as a dict
    :raise: RuntimeError if `hub_path` has no `hub-config/target-data.json` file
    """
    try:
        with (hub_conn._filesystem.open_input_file(f'{hub_conn._filesystem_path}/hub-config/target-data.json') as fp):
            return json.load(fp)
    except Exception as ex:
        raise RuntimeError(f'target-data.json not found. hubverse schema v6 is required: {ex}')


def _col_name_to_pa_type_for_target_data(hub_schema: pa.schema, target_data: dict,
                                         is_time_series: bool) -> dict[str, pa.DataType]:
    """
    Helper that returns a mapping of `hub-config/target-data.json` column names to pa.DataTypes.

    :param hub_schema: a hub schema as returned by `create_hub_schema()`
    :param target_data: as returned by `_target_data_json()`
    :param is_time_series: True if output is for time-series target data, and False if for oracle-output target data
    :return: col_name_to_pa_type
    """
    # process target-data.json sections, filling col_name_to_pa_type
    property_name = 'time-series' if is_time_series else 'oracle-output'
    col_name_to_pa_type: dict[str, pa.DataType] = {}

    # top-level property: `observable_unit` (required): task ID column names. get types from regular schema
    # (tasks.json). can be overridden by target-type specific configuration
    ts_observable_unit = target_data[property_name]['observable_unit'] \
        if (property_name in target_data) and ('observable_unit' in target_data[property_name]) \
        else target_data['observable_unit']
    for column_name in ts_observable_unit:
        col_name_to_pa_type[column_name] = hub_schema.field(column_name).type

    # top-level property: `date_col` (required): date column name. a Date. may or may not be in `observable_unit`
    date_col = target_data['date_col']
    if date_col not in col_name_to_pa_type:
        col_name_to_pa_type[date_col] = pa.date32()

    # top-level property: `versioned` (optional): whether all target type datasets are versioned using `as_of` dates.
    # defaults to False. can be overridden by target-type specific configuration
    ts_versioned = target_data[property_name]['versioned'] \
        if (property_name in target_data) and ('versioned' in target_data[property_name]) \
        else (target_data['versioned'] if 'versioned' in target_data else False)
    if ts_versioned:
        col_name_to_pa_type['as_of'] = pa.date32()

    if is_time_series:  # time-series specific
        # target-type specific configuration: `time-series` > `non_task_id_schema` (optional): additional
        # (column_name:r_data_type) key-value pairs
        non_task_id_schema = target_data[property_name]['non_task_id_schema'] \
            if (property_name in target_data) and ('non_task_id_schema' in target_data[property_name]) \
            else {}
        for column_name, hub_type in non_task_id_schema.items():
            col_name_to_pa_type[column_name] = _pa_type_for_hub_type(hub_type)

        # `observation` column: [implicit to time-series data]: same type as `value` from regular schema (tasks.json)
        col_name_to_pa_type['observation'] = hub_schema.field('value').type
    else:  # oracle-output specific
        # target-type specific configuration: `oracle-output` > `has_output_type_ids` (optional): Indicates whether the
        # oracle-output data have an `output_type` and `output_type_id` column.
        has_output_type_ids = target_data[property_name]['has_output_type_ids'] \
            if (property_name in target_data) and ('has_output_type_ids' in target_data[property_name]) \
            else False
        if has_output_type_ids:
            col_name_to_pa_type['output_type'] = hub_schema.field('output_type').type
            col_name_to_pa_type['output_type_id'] = hub_schema.field('output_type_id').type

        # `oracle_value` column: [implicit to oracle-output data]: same type as `value` from regular schema (tasks.json)
        col_name_to_pa_type['oracle_value'] = hub_schema.field('value').type

    # done
    return col_name_to_pa_type
