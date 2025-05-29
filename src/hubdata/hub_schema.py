import json
from collections import defaultdict
from datetime import date

import pyarrow as pa


def create_hub_schema(tasks: dict, output_type_id_datatype: str = 'from_config',
                      partitions: tuple[tuple[str, pa.DataType]] | None = (('model_id', pa.string()),)) -> pa.schema:
    """
    Top-level function for creating a schema for the passed `HubConfig`.

    :param tasks: a hub's `tasks.json` contents from which to create a schema - see `HubConfig.tasks`
    :param output_type_id_datatype: a string that's one of `"from_config"`, `"auto"`, `"character"`, `"double"`,
        `"integer"`, `"logical"`, `"Date"`. Defaults to `"from_config"` which uses the setting in the
        `output_type_id_datatype` property in the `tasks.json` config file if available. If the property is not set in
        the config, the argument falls back to `"auto"` which determines the `output_type_id` data type automatically
        from the `tasks.json` config file as the simplest data type required to represent all output type ID values
        across all output types in the hub. When only point estimate output types (where `output_type_id`s are `NA`)
        are being collected by a hub, the `output_type_id` column is assigned a `character` data type when
        auto-determined.
    :param partitions: a list of 2-tuples (column_name, data_type) specifying the arrow data types
        of any partitioning column. pass None if no partitions
    :return: a `pyarrow.Schema` for the passed `HubConfig`
    """
    # build col_name_to_pa_types, which maps each found column_name to a list of pa.DataTypes that were found for it.
    # afterward we merge the data types to get the "simplest" one
    col_name_to_pa_types: dict[str, list[pa.DataType]] = defaultdict(list)
    for the_round in tasks['rounds']:
        for model_task in the_round['model_tasks']:
            for column_name, column_type in _columns_for_model_task(model_task, partitions):
                col_name_to_pa_types[column_name].append(column_type)

    # merge col_name_to_pa_types values (types) to get the "simplest" one for each column
    col_name_to_pa_type: dict[str, pa.DataType] = {col_name: _pa_type_simplest_for_pa_types(pa_types)
                                                   for col_name, pa_types in col_name_to_pa_types.items()}

    # validate `output_type_id`
    if output_type_id_datatype not in ['from_config', 'auto']:  # "character", "double", "integer", "logical", "Date"
        try:
            _pa_type_for_hub_type(output_type_id_datatype)
        except ValueError:
            raise ValueError(f'invalid {output_type_id_datatype=}')

    # override the `output_type_id` column if necessary (its value to this point is essentially "auto")
    if ((output_type_id_datatype == 'from_config')
            and ('output_type_id_datatype' in tasks)
            and (tasks['output_type_id_datatype'] != 'auto')):
        col_name_to_pa_type['output_type_id'] = _pa_type_for_hub_type(tasks['output_type_id_datatype'])
    elif (output_type_id_datatype
          and (output_type_id_datatype != 'auto')
          and (output_type_id_datatype != 'from_config')):
        col_name_to_pa_type['output_type_id'] = _pa_type_for_hub_type(output_type_id_datatype)

    # handle the case of no 'output_type_id', which happens when there are only point estimate output types (mean,
    # median)
    if 'output_type_id' not in col_name_to_pa_type:
        col_name_to_pa_type['output_type_id'] = pa.string()

    # done
    return pa.schema(col_name_to_pa_type)


def _columns_for_model_task(model_task: dict, partitions: tuple[tuple[str, pa.DataType]] | None) \
        -> list[tuple[str, pa.DataType]]:
    # columns is a list of two-tuples: model_task key (column name) and inferred pa.DataType for it. the list possibly
    # contains duplicates when there are multiple rounds and/or model_tasks
    columns: list[tuple[str, pa.DataType]] = []

    # collect columns from task_ids
    for task_id_key, task_id_value in model_task['task_ids'].items():
        # ex: ('reference_date', pa.date32())
        columns.append((task_id_key, _pa_type_for_req_and_opt_vals(task_id_value['required'],
                                                                   task_id_value['optional'])))

    # add output_type column
    columns.append(('output_type', pa.string()))

    # collect columns from output_type section ('output_type_id', 'value')
    for output_type_key, output_type_value in model_task['output_type'].items():
        if output_type_key == 'sample':
            columns.append(('output_type_id',
                            _pa_type_for_hub_type(output_type_value['output_type_id_params']['type'])))
        else:
            pa_type = _pa_type_for_req_and_opt_vals(
                output_type_value['output_type_id']['required'] if 'required' in output_type_value[
                    'output_type_id'] else [],
                output_type_value['output_type_id']['optional'] if 'optional' in output_type_value[
                    'output_type_id'] else [])
            if pa_type:  # none if NA
                columns.append(('output_type_id', pa_type))
        columns.append(('value', _pa_type_for_hub_type(output_type_value['value']['type'])))

    # add columns from partitions
    if partitions:
        for column_name, column_type in partitions:
            columns.append((column_name, column_type))

    return columns


def _pa_type_for_hub_type(hub_type: str) -> pa.DataType:
    """
    :param: hub_type: a hub data type as defined at https://hubverse.io/en/latest/quickstart-hub-admin/tasks-config.html#step-9-optional-set-up-output-type-id-datatype
    :return: the pa.DataType corresponding to the hub one `hub_type`
    :raise: ValueError if `hub_type` is invalid
    """
    try:
        return {
            'character': pa.string(),
            'double': pa.float64(),
            'integer': pa.int32(),
            'logical': pa.bool_(),  # is logical used in any hubs? only applies to `output_type_id_datatype`?
            'Date': pa.date32(),
        }[hub_type]
    except KeyError:
        raise ValueError(f'invalid hub_type={hub_type}')


def _pa_type_for_req_and_opt_vals(required: list | None, optional: list | None) -> pa.DataType | None:
    """
    Given a list of required and optional values from a tasks.json file, return the most "specific" pa.DataType found,
    or None if no values passed or only "NA" passed. Note that a non-string data type is returned only if the merger of
    `required` and `optional` contains items all the same type.

    :param required: from the "required" field of a rounds.model_tasks.task_ids value
    :param optional: "" "optional" ""
    :return: a pa.DataType or None
    """


    def is_number(value, is_float):
        if type(value) is (float if is_float else int):
            return True
        try:
            return json.loads(value) is (float if is_float else int)
        except Exception:
            return False


    def is_date(value):
        try:
            return date.fromisoformat(value)  # non-False
        except Exception:
            return False


    req_and_opt_vals = (required if required else []) + (optional if optional else [])
    pa_types = []
    for value in req_and_opt_vals:
        # try parsing in this order: NA, pa.date32, pa.float64, pa.int32
        pa_type = pa.string()
        if value == 'NA':
            continue  # special case: NA should not influence returned type
        elif is_date(value):  # date
            pa_type = pa.date32()
        elif is_number(value, True):  # float
            pa_type = pa.float64()
        elif is_number(value, False):  # int
            pa_type = pa.int32()
        pa_types.append(pa_type)

    return _pa_type_simplest_for_pa_types(pa_types) if pa_types else None


def _pa_type_simplest_for_pa_types(pa_types: list[pa.DataType]) -> pa.DataType:
    """
    Given a list of pa.DataTypes, return the "simplest" one based on the below logic.
    """
    if pa.string() in pa_types:  # any string present overrides all other types
        return pa.string()

    pa_types_set = set(pa_types)
    if len(pa_types_set) == 1:  # all the same type -> use that type
        return pa_types[0]  # arbitrary

    if pa_types_set == {pa.int32(), pa.float64()}:  # float wins if all numbers. the only acceptable type mix case
        return pa.float64()

    # types didn't agree or no types, so default to string
    return pa.string()
