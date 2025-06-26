import datetime
import json
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pytest

from hubdata import connect_hub, create_hub_schema


def test_hub_path_existence():
    # note: we don't directly check for hub_path existence because it might not be in local file system. instead we pick
    # up a problem when we try to open either admin.json or tasks.json
    with pytest.raises(RuntimeError, match='admin.json or tasks.json not found'):
        connect_hub(Path('test/hubs/example-complex-forecast-hub') / 'nonexistent-dir')


def test_hub_fields():
    hub_path = Path('test/hubs/example-complex-scenario-hub')
    hub_connection = connect_hub(hub_path)  # default schema

    # check hub_path
    assert hub_connection.hub_path == hub_path

    # spot-check admin
    assert list(hub_connection.admin.keys()) == ['schema_version', 'name', 'maintainer', 'contact', 'repository',
                                                 'file_format', 'timezone', 'model_output_dir']

    # spot-check tasks
    assert list(hub_connection.tasks.keys()) == ['schema_version', 'rounds']
    assert len(hub_connection.tasks['rounds']) == 4

    # check schema
    assert connect_hub(hub_path).schema == create_hub_schema(hub_connection.tasks)

    # spot-check model_output_dir
    hub_connection = connect_hub(Path('test/hubs/simple'))
    assert isinstance(hub_connection.model_output_dir, str)
    assert sorted([f.name for f in Path(hub_connection.model_output_dir).iterdir()
                   if not f.name.startswith('.')]) == ['hub-baseline', 'team1-goodmodel']


def test_admin_model_output_dir(tmp_path):
    # case: specified in admin.json, but using standard name
    hub_path = Path('test/hubs/example-complex-scenario-hub')  # "model_output_dir": "model-output"
    hub_connection = connect_hub(hub_path)
    assert hub_connection.model_output_dir == str((hub_path / 'model-output').absolute())

    # case: no "model_output_dir" key in admin.json. note: covid19-forecast-hub does not have a model-output dir, which
    # will cause `connect_hub()` to log a warning but not raise an exception
    hub_path = Path('test/hubs/covid19-forecast-hub')
    hub_connection = connect_hub(hub_path)
    assert hub_connection.model_output_dir == str((hub_path / 'model-output').absolute())

    # case: specified in admin.json, but using non-standard name
    shutil.copytree('test/hubs/example-complex-forecast-hub/', tmp_path, dirs_exist_ok=True)
    admin_json_path = tmp_path / 'hub-config' / 'admin.json'
    model_output_dir_name = 'nonstandard-model-output'
    with open(admin_json_path) as admin_fp:
        admin_dict = json.load(admin_fp)
        admin_dict['model_output_dir'] = model_output_dir_name
    with open(admin_json_path, 'w') as admin_fp:
        json.dump(admin_dict, admin_fp)
    hub_connection = connect_hub(tmp_path)
    assert hub_connection.model_output_dir == str((tmp_path / model_output_dir_name).absolute())


def test_query_data():
    # case: mix of csv, parquet, and arrow files. also tests that default schema (incl. 'model_id' partition) is used
    hub_connection = connect_hub(Path('test/hubs/v4_flusight'))
    hub_ds = hub_connection.get_dataset()
    assert isinstance(hub_ds, pa.dataset.UnionDataset)
    assert hub_connection.admin['file_format'] == ['csv', 'parquet', 'arrow']
    assert len(hub_ds.children) == len(hub_connection.admin['file_format'])  # one Dataset child per type
    assert sorted(hub_ds.to_table().column_names) == ['forecast_date', 'horizon', 'location', 'model_id', 'output_type',
                                                      'output_type_id', 'target', 'target_date', 'value']
    # check total row count. file row counts by forecasts/ dir:
    #   hub-baseline: 48 x 3 ; hub-ensemble: 46 x 3 ; umass-ens: 5 x 2 = 292 total
    assert hub_ds.count_rows() == 292

    # spot-check some unique column values
    assert pc.unique(hub_ds.to_table()['forecast_date']).to_pylist() == [datetime.date(2023, 4, 24),
                                                                         datetime.date(2023, 5, 1),
                                                                         datetime.date(2023, 5, 8)]
    assert pc.unique(hub_ds.to_table()['horizon']).to_pylist() == [1, 2]
    assert pc.unique(hub_ds.to_table()['location']).to_pylist() == ['US']
    assert pc.unique(hub_ds.to_table()['model_id']).to_pylist() == ['hub-baseline', 'hub-ensemble', 'umass-ens']
    assert pc.unique(hub_ds.to_table()['output_type']).to_pylist() == ['mean', 'quantile', 'pmf']
    assert pc.unique(hub_ds.to_table()['target']).to_pylist() == ['wk ahead inc flu hosp', 'wk flu hosp rate change']
    assert pc.unique(hub_ds.to_table()['target_date']).to_pylist() == [datetime.date(2023, 5, 1),
                                                                       datetime.date(2023, 5, 8),
                                                                       datetime.date(2023, 5, 15),
                                                                       datetime.date(2023, 5, 22)]

    # case: only csv files
    hub_connection = connect_hub(Path('test/hubs/flu-metrocast'))
    hub_ds = hub_connection.get_dataset()
    assert hub_connection.admin['file_format'] == ['csv']
    assert sorted(hub_ds.to_table().column_names) == ['horizon', 'location', 'model_id', 'output_type',
                                                      'output_type_id', 'reference_date', 'target', 'target_end_date',
                                                      'value']
    assert hub_ds.count_rows() == 14895

    # spot-check some unique column values
    assert pc.unique(hub_ds.to_table()['horizon']).to_pylist() == [0, 1, 2, 3, 4, -1]
    assert pc.unique(hub_ds.to_table()['location']).to_pylist() == [
        'Bronx', 'Brooklyn', 'Manhattan', 'NYC', 'Queens', 'Staten Island', 'Austin', 'Dallas', 'El Paso', 'Houston',
        'San Antonio']
    assert pc.unique(hub_ds.to_table()['model_id']).to_pylist() == ['epiENGAGE-baseline', 'epiENGAGE-ensemble_mean']
    assert pc.unique(hub_ds.to_table()['output_type']).to_pylist() == ['quantile']
    assert pc.unique(hub_ds.to_table()['reference_date']).to_pylist() == [datetime.date(2025, 1, 25),
                                                                          datetime.date(2025, 2, 1),
                                                                          datetime.date(2025, 2, 8),
                                                                          datetime.date(2025, 2, 15),
                                                                          datetime.date(2025, 2, 22),
                                                                          datetime.date(2025, 3, 1),
                                                                          datetime.date(2025, 3, 8),
                                                                          datetime.date(2025, 3, 15),
                                                                          datetime.date(2025, 3, 22),
                                                                          datetime.date(2025, 3, 29),
                                                                          datetime.date(2025, 4, 5),
                                                                          datetime.date(2025, 4, 12),
                                                                          datetime.date(2025, 4, 19),
                                                                          datetime.date(2025, 4, 26),
                                                                          datetime.date(2025, 5, 3),
                                                                          datetime.date(2025, 5, 10),
                                                                          datetime.date(2025, 5, 17),
                                                                          datetime.date(2025, 5, 24)]
    assert pc.unique(hub_ds.to_table()['target']).to_pylist() == ['ILI ED visits', 'Flu ED visits pct']

    # test a query
    hub_ds = hub_ds.filter((pc.field('location') == 'Brooklyn')
                           & (pc.field('horizon') == 2)
                           & (pc.field('output_type_id') == 0.5))
    assert hub_ds.count_rows() == 31  # only one row matches per file


def test_to_table():
    hub_connection = connect_hub(Path('test/hubs/v4_flusight'))
    hub_ds = hub_connection.get_dataset()
    table1 = hub_ds.to_table()
    table2 = hub_connection.to_table()
    assert table1 == table2


def test_get_dataset_returned_class():
    hub_connection = connect_hub(Path('test/hubs/flu-metrocast'))  # only .csv -> a FileSystemDataset
    hub_ds = hub_connection.get_dataset()
    assert isinstance(hub_ds, pa.dataset.FileSystemDataset)
    assert len(hub_ds.files) == 31

    hub_connection = connect_hub(Path('test/hubs/simple'))  # .csv and .parquet -> UnionDataset with 2 child Datasets
    hub_ds = hub_connection.get_dataset()
    assert isinstance(hub_ds, pa.dataset.UnionDataset)
    assert len(hub_ds.children) == 2
    assert all([isinstance(child, pa.dataset.FileSystemDataset) for child in hub_ds.children])
