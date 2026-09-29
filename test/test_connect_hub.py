import datetime
import json
import os
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

    # spot-check model_metadata_schema
    assert (list(connect_hub(hub_path).model_metadata_schema.keys()) == ['$schema', 'title', 'description', 'type',
                                                                         'properties', 'additionalProperties',
                                                                         'required'])

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


@pytest.mark.parametrize('config_file_is_error_msg',
                         [('admin.json', True, 'admin.json or tasks.json not found'),
                          ('tasks.json', True, 'admin.json or tasks.json not found'),
                          ('model-metadata-schema.json', False, 'model-metadata-schema.json not found')])
def test_missing_files_or_dirs(tmp_path, config_file_is_error_msg):
    """
    tests file not found or directory not found cases. notes:
    - the case of hub_dir itself missing is tested above by `test_hub_dir_existence()`
    - the case of model-output dir missing is tested above by `test_admin_model_output_dir()`
    """
    shutil.copytree('test/hubs/example-complex-forecast-hub/', tmp_path, dirs_exist_ok=True)

    original_file = tmp_path / 'hub-config' / config_file_is_error_msg[0]
    new_file = tmp_path / 'hub-config' / f'{config_file_is_error_msg[0]}.orig'
    os.rename(original_file, new_file)
    if config_file_is_error_msg[1]:
        with pytest.raises(RuntimeError, match=f'{config_file_is_error_msg[2]}'):
            connect_hub(tmp_path)
    else:
        connect_hub(tmp_path)
    os.rename(new_file, original_file)


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


def test_connect_hub_partitions_default():
    # partitions not passed -> defaults to {'model_id': pa.string()} (the previous hard-coded behavior)
    hub_connection = connect_hub(Path('test/hubs/flu-metrocast'))
    assert hub_connection.partitions == {'model_id': pa.string()}
    assert hub_connection.schema.field('model_id').type == pa.string()
    hub_ds = hub_connection.get_dataset()
    table = hub_ds.to_table()
    assert table.schema.field('model_id').type == pa.string()
    assert sorted(pc.unique(table['model_id']).to_pylist()) == ['epiENGAGE-baseline', 'epiENGAGE-ensemble_mean']


def _build_directory_partitioned_hub(tmp_path: Path) -> None:
    """
    builds a minimal hub at tmp_path using flu-metrocast's hub-config, with model output data stored using two-level
    directory-style partitioning: model-output/<round_id>/<model_id>/*.csv
    """
    shutil.copytree('test/hubs/flu-metrocast/hub-config', tmp_path / 'hub-config')
    csv_rows = {
        ('2025-01-25', 'epiENGAGE-baseline'): [
            '2025-01-25,ILI ED visits,0,Bronx,2025-01-25,quantile,0.5,100.0',
            '2025-01-25,ILI ED visits,1,Queens,2025-02-01,quantile,0.5,200.0',
        ],
        ('2025-02-01', 'epiENGAGE-ensemble_mean'): [
            '2025-02-01,Flu ED visits pct,0,Bronx,2025-02-01,quantile,0.25,50.0',
        ],
    }
    for (round_id, model_id), rows in csv_rows.items():
        partition_dir = tmp_path / 'model-output' / round_id / model_id
        partition_dir.mkdir(parents=True, exist_ok=True)
        with open(partition_dir / f'{round_id}-{model_id}.csv', 'w') as csv_fp:
            csv_fp.write('reference_date,target,horizon,location,target_end_date,output_type,output_type_id,value\n')
            csv_fp.write('\n'.join(rows) + '\n')


def test_connect_hub_partitions_custom(tmp_path):
    # case: two-level directory partitioning with declared data types, including a non-string (date32) partition
    _build_directory_partitioned_hub(tmp_path)
    partitions = {'round_id': pa.date32(), 'model_id': pa.string()}
    hub_connection = connect_hub(tmp_path, partitions=partitions)
    assert hub_connection.partitions == partitions

    # the connection's schema matches create_hub_schema() called with the same partitions
    assert hub_connection.schema == create_hub_schema(
        hub_connection.tasks, partitions=(('round_id', pa.date32()), ('model_id', pa.string()))
    )

    hub_ds = hub_connection.get_dataset()
    table = hub_ds.to_table()
    assert sorted(table.column_names) == [
        'horizon',
        'location',
        'model_id',
        'output_type',
        'output_type_id',
        'reference_date',
        'round_id',
        'target',
        'target_end_date',
        'value',
    ]
    assert table.num_rows == 3

    # partition columns have the declared data types and the expected values parsed from directory names
    assert table.schema.field('round_id').type == pa.date32()
    assert sorted(pc.unique(table['round_id']).to_pylist()) == [datetime.date(2025, 1, 25), datetime.date(2025, 2, 1)]
    assert table.schema.field('model_id').type == pa.string()
    assert sorted(pc.unique(table['model_id']).to_pylist()) == ['epiENGAGE-baseline', 'epiENGAGE-ensemble_mean']

    # filtering on a partition column works
    filtered_table = hub_ds.to_table(filter=pc.field('round_id') == datetime.date(2025, 1, 25))
    assert filtered_table.num_rows == 2
    assert sorted(pc.unique(filtered_table['model_id']).to_pylist()) == ['epiENGAGE-baseline']


def test_connect_hub_partitions_disabled(tmp_path):
    # case: empty dict disables directory partitioning (for hubs with model output files directly in the dir)
    shutil.copytree('test/hubs/flu-metrocast/hub-config', tmp_path / 'hub-config')
    model_output_dir = tmp_path / 'model-output'
    model_output_dir.mkdir()
    with open(model_output_dir / '2025-01-25-team1-goodmodel.csv', 'w') as csv_fp:
        csv_fp.write('reference_date,target,horizon,location,target_end_date,output_type,output_type_id,value\n'
                     '2025-01-25,ILI ED visits,0,Bronx,2025-01-25,quantile,0.5,100.0\n')

    hub_connection = connect_hub(tmp_path, partitions={})
    assert hub_connection.partitions == {}
    assert 'model_id' not in hub_connection.schema.names
    assert 'round_id' not in hub_connection.schema.names

    table = hub_connection.get_dataset().to_table()
    assert 'model_id' not in table.column_names
    assert table.num_rows == 1


@pytest.mark.parametrize(
    'bad_partitions',
    [
        ['model_id'],  # not a dict
        {'model_id': 'string'},  # data type is not a pyarrow DataType
        {1: pa.string()},  # column name is not a str
    ],
)
def test_connect_hub_partitions_invalid(bad_partitions):
    with pytest.raises(TypeError):
        connect_hub(Path('test/hubs/flu-metrocast'), partitions=bad_partitions)


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


def test__list_model_out_files():
    hub_connection = connect_hub(Path('test/hubs/v4_flusight'))
    model_out_files = hub_connection._list_model_out_files()
    model_out_files_clean = [_ for _ in model_out_files if not _.base_name.startswith('.DS_Store')]
    assert len(model_out_files_clean) == 10  # including README.md and invalid.txt
    assert (sorted([_.base_name for _ in model_out_files_clean]) ==
            ['2023-04-24-hub-baseline.csv', '2023-04-24-hub-ensemble.csv',
             '2023-05-01-hub-baseline.csv', '2023-05-01-hub-ensemble.arrow', '2023-05-01-umass-ens.csv',
             '2023-05-08-hub-baseline.parquet', '2023-05-08-hub-ensemble.parquet', '2023-05-08-umass-ens.csv',
             'README.md', 'invalid.txt'])

    for file_format, exp_invalid in (
            ('csv', ['2023-05-01-hub-ensemble.arrow', '2023-05-08-hub-baseline.parquet',
                     '2023-05-08-hub-ensemble.parquet', 'README.md', 'invalid.txt']),
            ('parquet', ['2023-04-24-hub-baseline.csv', '2023-04-24-hub-ensemble.csv', '2023-05-01-hub-baseline.csv',
                         '2023-05-01-hub-ensemble.arrow', '2023-05-01-umass-ens.csv', '2023-05-08-umass-ens.csv',
                         'README.md', 'invalid.txt']),
            ('arrow', ['2023-04-24-hub-baseline.csv', '2023-04-24-hub-ensemble.csv', '2023-05-01-hub-baseline.csv',
                       '2023-05-01-umass-ens.csv', '2023-05-08-hub-baseline.parquet', '2023-05-08-hub-ensemble.parquet',
                       '2023-05-08-umass-ens.csv', 'README.md', 'invalid.txt'])):
        invalid_format_files = hub_connection._list_invalid_format_files(model_out_files, file_format,
                                                                         ['README', '.DS_Store'])
        invalid_format_files_clean = [_ for _ in invalid_format_files if not _.base_name.startswith('.DS_Store')]
        assert sorted([_.base_name for _ in invalid_format_files_clean]) == exp_invalid
