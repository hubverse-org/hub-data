import json
from pathlib import Path

import pyarrow as pa
import pytest

from hubdata import connect_hub, create_hub_schema
from hubdata.create_hub_schema import _pa_type_for_req_and_opt_vals, _pa_type_simplest_for_pa_types


@pytest.mark.parametrize('required,optional,exp_pa_type',
                         [(None, ['2024-11-16', '2024-11-23'], pa.date32()),
                          (['2024-11-16', '2024-11-23'], None, pa.date32()),
                          (None, ['wk inc covid hosp'], pa.string()),
                          (None, [-1, 0, 1, 2, 3], pa.int32()),
                          ([0.01, 0.025], None, pa.float64()),
                          ([0.25, 1], None, pa.float64()),
                          (None, ['NA'], None)])
def tests__pa_type_for_req_and_opt_vals(required, optional, exp_pa_type):
    assert _pa_type_for_req_and_opt_vals(required, optional) == exp_pa_type


@pytest.mark.parametrize('pa_types,exp_pa_type',
                         [([pa.float64(), pa.string()], pa.string()),  # string overrides float -> string
                          ([pa.float64(), pa.string(), None], pa.string()),  # "", None no influence -> string
                          ([pa.float64(), pa.date32()], pa.string()),  # mixed non-string -> string
                          ([pa.float64(), pa.date32(), None], pa.string()),  # "", None no influence -> string
                          ([pa.float64(), None], pa.float64()),  # float, None no influence -> float
                          ([None], pa.string()),  # all Nones -> string
                          ([None, None], pa.string()),  # ""
                          ([pa.float64(), pa.float64()], pa.float64()),  # two floats -> float
                          ([pa.int32(), pa.int32()], pa.int32()),  # two ints -> int
                          ([pa.int32(), pa.float64()], pa.float64()),  # float overrides int
                          ([], pa.string())])  # no types -> string
def test__pa_type_simplest_for_pa_types(pa_types, exp_pa_type):
    assert _pa_type_simplest_for_pa_types(pa_types) == exp_pa_type


def test_covid19_forecast_hub():
    hub_connection = connect_hub(Path('test/hubs/covid19-forecast-hub'))
    act_schema = create_hub_schema(hub_connection.tasks)
    exp_schema = pa.schema([('reference_date', pa.date32()),
                            ('target', pa.string()),
                            ('horizon', pa.int32()),
                            ('location', pa.string()),
                            ('target_end_date', pa.date32()),
                            ('output_type', pa.string()),
                            ('output_type_id', pa.string()),
                            ('value', pa.float64()),
                            ('model_id', pa.string())])
    assert isinstance(act_schema, pa.lib.Schema)
    assert act_schema.names == exp_schema.names
    assert act_schema == exp_schema


def test_ecfh():
    hub_connection = connect_hub(Path('test/hubs/example-complex-forecast-hub'))
    act_schema = create_hub_schema(hub_connection.tasks)
    exp_schema = pa.schema([('reference_date', pa.date32()),
                            ('target', pa.string()),
                            ('horizon', pa.int32()),
                            ('location', pa.string()),
                            ('target_end_date', pa.date32()),
                            ('output_type', pa.string()),
                            ('output_type_id', pa.string()),
                            ('value', pa.float64()),
                            ('model_id', pa.string())])
    assert act_schema == exp_schema


def test_ecsh():
    hub_connection = connect_hub(Path('test/hubs/example-complex-scenario-hub'))
    act_schema = create_hub_schema(hub_connection.tasks)
    exp_schema = pa.schema([('origin_date', pa.date32()),
                            ('scenario_id', pa.string()),
                            ('location', pa.string()),
                            ('target', pa.string()),
                            ('horizon', pa.int32()),
                            ('output_type', pa.string()),
                            ('value', pa.float64()),
                            ('output_type_id', pa.float64()),
                            ('model_id', pa.string()),
                            ('age_group', pa.string()),
                            ('target_date', pa.date32())])
    assert act_schema == exp_schema


def test_flu_metrocast():
    # this hub uses v5.0 schema where "output_type_id" only has "required" and not "optional"
    hub_connection = connect_hub(Path('test/hubs/flu-metrocast'))
    act_schema = create_hub_schema(hub_connection.tasks)
    exp_schema = pa.schema([('reference_date', pa.date32()),
                            ('target', pa.string()),
                            ('horizon', pa.int32()),
                            ('location', pa.string()),
                            ('target_end_date', pa.date32()),
                            ('output_type', pa.string()),
                            ('output_type_id', pa.float64()),
                            ('value', pa.float64()),
                            ('model_id', pa.string())])
    assert act_schema == exp_schema


def test_flusight_forecast_hub():
    hub_connection = connect_hub(Path('test/hubs/FluSight-forecast-hub'))
    act_schema = create_hub_schema(hub_connection.tasks)
    exp_schema = pa.schema([('reference_date', pa.date32()),
                            ('target', pa.string()),
                            ('horizon', pa.int32()),
                            ('location', pa.string()),
                            ('target_end_date', pa.date32()),
                            ('output_type', pa.string()),
                            ('output_type_id', pa.string()),
                            ('value', pa.float64()),
                            ('model_id', pa.string())])
    assert act_schema == exp_schema


def test_simple():
    hub_connection = connect_hub(Path('test/hubs/simple'))
    act_schema = create_hub_schema(hub_connection.tasks)
    exp_schema = pa.schema([('origin_date', pa.date32()),
                            ('target', pa.string()),
                            ('horizon', pa.int32()),
                            ('location', pa.string()),
                            ('output_type', pa.string()),
                            ('value', pa.int32()),
                            ('output_type_id', pa.float64()),
                            ('model_id', pa.string()),
                            ('age_group', pa.string())])
    assert act_schema == exp_schema


def test_variant_nowcast_hub():
    hub_connection = connect_hub(Path('test/hubs/variant-nowcast-hub'))
    act_schema = create_hub_schema(hub_connection.tasks)
    exp_schema = pa.schema([('nowcast_date', pa.date32()),
                            ('target_date', pa.date32()),
                            ('location', pa.string()),
                            ('clade', pa.string()),
                            ('output_type', pa.string()),
                            ('value', pa.float64()),
                            ('output_type_id', pa.string()),
                            ('model_id', pa.string())])
    assert act_schema == exp_schema


@pytest.mark.parametrize('output_type_id_datatype,is_valid',
                         [('from_config', True), ('auto', True), ('character', True), ('double', True),
                          ('integer', True), ('logical', True), ('Date', True), ('bad_type', False)])
def test_output_type_id_datatype_choices(output_type_id_datatype, is_valid):
    hub_connection = connect_hub(Path('test/hubs/flu-metrocast'))
    if is_valid:
        create_hub_schema(hub_connection.tasks, output_type_id_datatype=output_type_id_datatype)
    else:
        with pytest.raises(ValueError):
            create_hub_schema(hub_connection.tasks, output_type_id_datatype=output_type_id_datatype)


@pytest.mark.parametrize('hub_datatype,exp_pa_type',
                         [('from_config', pa.float64()), ('auto', pa.float64()), ('character', pa.string()),
                          ('double', pa.float64()), ('integer', pa.int32()), ('logical', pa.bool_()),
                          ('Date', pa.date32())])
def test_output_type_id_datatype(hub_datatype, exp_pa_type):
    # tests the behavior documented at https://hubverse.io/en/latest/quickstart-hub-admin/tasks-config.html#step-9-optional-set-up-output-type-id-datatype
    # NB: flu-metrocast is the only test hub that sets optional `output_type_id_datatype` property (to "auto"):
    hub_connection = connect_hub(Path('test/hubs/flu-metrocast'))
    if hub_datatype != 'from_config':
        hub_connection.tasks['output_type_id_datatype'] = hub_datatype
    act_schema = create_hub_schema(hub_connection.tasks, output_type_id_datatype=hub_datatype)
    assert act_schema.field('output_type_id').type == exp_pa_type


# test_that("create_hub_schema works correctly", { .. }) from hubData/tests/testthat/test-create_hub_schema.R
def test_r_test_1():
    hub_connection = connect_hub(Path('test/hubs/simple'))

    # case: default options
    # exp_schema from R: "origin_date: date32[day]\ntarget: string\nhorizon: int32\nlocation: string\nage_group: string\noutput_type: string\noutput_type_id: double\nvalue: int32\nmodel_id: string"
    act_schema = create_hub_schema(hub_connection.tasks)
    exp_schema = pa.schema([('origin_date', pa.date32()),
                            ('target', pa.string()),
                            ('horizon', pa.int32()),
                            ('location', pa.string()),
                            ('output_type', pa.string()),
                            ('value', pa.int32()),
                            ('output_type_id', pa.float64()),
                            ('model_id', pa.string()),
                            ('age_group', pa.string())])
    assert act_schema == exp_schema

    # case: output_type_id_datatype param
    # exp_schema from R: "origin_date: date32[day]\ntarget: string\nhorizon: int32\nlocation: string\nage_group: string\noutput_type: string\noutput_type_id: string\nvalue: int32\nmodel_id: string"
    act_schema = create_hub_schema(hub_connection.tasks, output_type_id_datatype='character')
    exp_schema = pa.schema([('origin_date', pa.date32()),
                            ('target', pa.string()),
                            ('horizon', pa.int32()),
                            ('location', pa.string()),
                            ('output_type', pa.string()),
                            ('value', pa.int32()),
                            ('output_type_id', pa.string()),  # overrides default
                            ('model_id', pa.string()),
                            ('age_group', pa.string())])
    assert act_schema == exp_schema

    # case: partitions param
    # exp_schema from R: "origin_date: date32[day]\ntarget: string\nhorizon: int32\nlocation: string\nage_group: string\noutput_type: string\noutput_type_id: double\nvalue: int32\nteam_abbr: string\nmodel_abbr: string"
    act_schema = create_hub_schema(hub_connection.tasks, partitions=(('team_abbr', pa.string()),
                                                                     ('model_abbr', pa.string())))
    exp_schema = pa.schema([('origin_date', pa.date32()),
                            ('target', pa.string()),
                            ('horizon', pa.int32()),
                            ('location', pa.string()),
                            ('output_type', pa.string()),
                            ('value', pa.int32()),
                            ('output_type_id', pa.float64()),
                            ('team_abbr', pa.string()),
                            ('model_abbr', pa.string()),
                            ('age_group', pa.string())])
    assert act_schema == exp_schema

    # case: partitions None
    # exp_schema from R: "origin_date: date32[day]\ntarget: string\nhorizon: int32\nlocation: string\nage_group: string\noutput_type: string\noutput_type_id: string\nvalue: int32"
    act_schema = create_hub_schema(hub_connection.tasks, partitions=None, output_type_id_datatype='character')
    exp_schema = pa.schema([('origin_date', pa.date32()),
                            ('target', pa.string()),
                            ('horizon', pa.int32()),
                            ('location', pa.string()),
                            ('output_type', pa.string()),
                            ('value', pa.int32()),
                            ('output_type_id', pa.string()),
                            ('age_group', pa.string())])
    assert act_schema == exp_schema


# test_that("create_hub_schema works with sample output types", { .. }) from hubData/tests/testthat/test-create_hub_schema.R
def test_r_test_2():
    # case: tasks-samples-pass.json
    # exp_schema from R: "forecast_date: date32[day]\ntarget: string\nhorizon: int32\nlocation: string\noutput_type: string\noutput_type_id: string\nvalue: double\nmodel_id: string"
    with open('test/configs/tasks-samples-pass.json') as fp:
        tasks = json.load(fp)
    act_schema = create_hub_schema(tasks)
    exp_schema = pa.schema([('forecast_date', pa.date32()),
                            ('target', pa.string()),
                            ('horizon', pa.int32()),
                            ('location', pa.string()),
                            ('output_type', pa.string()),
                            ('output_type_id', pa.string()),
                            ('value', pa.float64()),
                            ('model_id', pa.string())])
    assert act_schema == exp_schema

    # case: tasks-samples-tid-from-sample.json
    # exp_schema from R: "forecast_date: date32[day]\ntarget: string\nhorizon: int32\nlocation: string\noutput_type: string\noutput_type_id: int32\nvalue: double\nmodel_id: string"
    with open('test/configs/tasks-samples-tid-from-sample.json') as fp:
        tasks = json.load(fp)
    act_schema = create_hub_schema(tasks)
    exp_schema = pa.schema([('forecast_date', pa.date32()),
                            ('target', pa.string()),
                            ('horizon', pa.int32()),
                            ('location', pa.string()),
                            ('output_type', pa.string()),
                            ('output_type_id', pa.int32()),
                            ('value', pa.float64()),
                            ('model_id', pa.string()),
                            ('age_group', pa.string())])
    assert act_schema == exp_schema
