import os
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as csv
import pyarrow.parquet as parquet
import pytest

from hubdata.connect_target_data import connect_target_data
from hubdata.create_target_data_schema import TargetType, create_target_data_schema


def test_no_target_data_json_file(tmp_path):
    # case: no hub-config/target-data.json . note that we create the test hub dynamically based on v6_target_file
    tmp_path = Path(tmp_path)
    shutil.copytree('test/hubs/v6_target_file', tmp_path, dirs_exist_ok=True)
    os.remove(tmp_path / 'hub-config/target-data.json')
    ts_ds = connect_target_data(tmp_path, TargetType.ORACLE_OUTPUT)
    exp_schema = pa.schema([('location', pa.string()),  # schema directly from data
                            ('target_end_date', pa.date32()),
                            ('target', pa.string()),
                            ('output_type', pa.string()),
                            ('output_type_id', pa.string()),
                            ('oracle_value', pa.int64())])
    assert ts_ds.schema == exp_schema


def test_no_oracle_output_data(tmp_path):
    # case: no target-data/oracle-output.csv, target-data/oracle-output.parquet, or target-data/oracle-output/ . note
    # that we create the test hub dynamically based on v6_target_file
    tmp_path = Path(tmp_path)
    shutil.copytree('test/hubs/v6_target_file', tmp_path, dirs_exist_ok=True)
    os.remove(tmp_path / 'target-data/oracle-output.csv')
    with pytest.raises(RuntimeError, match='did not find oracle-output.csv, oracle-output.parquet, or '
                                           'oracle-output/'):
        connect_target_data(tmp_path, TargetType.ORACLE_OUTPUT)


def test_more_than_one_oracle_output_data(tmp_path):
    # case: add a second file (target-data/oracle-output.parquet) in addition to target-data/oracle-output.csv . note
    # that we create the test hub dynamically based on v6_target_file
    tmp_path = Path(tmp_path)
    shutil.copytree('test/hubs/v6_target_file', tmp_path, dirs_exist_ok=True)
    pa_table = csv.read_csv(tmp_path / 'target-data/oracle-output.csv')
    parquet.write_table(pa_table, tmp_path / 'target-data/oracle-output.parquet')
    with pytest.raises(RuntimeError, match='found more than one oracle-output.csv, oracle-output.parquet, or '
                                           'oracle-output/'):
        connect_target_data(tmp_path, TargetType.ORACLE_OUTPUT)


def test_flu_metrocast():
    hub_path = Path('test/hubs/flu-metrocast')  # target-data/oracle-output.csv
    ts_ds = connect_target_data(hub_path, TargetType.ORACLE_OUTPUT)
    assert isinstance(ts_ds, pa.dataset.FileSystemDataset)
    assert len(ts_ds.files) == 1
    assert ts_ds.to_table().column_names == ['target', 'target_end_date', 'location', 'oracle_value']
    assert ts_ds.count_rows() == 31
    assert pc.unique(ts_ds.to_table()['target']).to_pylist() == ['ILI ED visits', 'Flu ED visits pct']
    assert ts_ds.schema == create_target_data_schema(hub_path, TargetType.ORACLE_OUTPUT)


def test_v6_target_dir():
    # target-data/oracle-output/output_type=cdf/part-0.parquet  # 396 rows
    # target-data/oracle-output/output_type=mean/part-0.parquet  # 33 rows
    # target-data/oracle-output/output_type=pmf/part-0.parquet  # 132 rows
    # target-data/oracle-output/output_type=quantile/part-0.parquet  # 33 rows
    # target-data/oracle-output/output_type=sample/part-0.parquet  # 33 rows
    hub_path = Path('test/hubs/v6_target_dir')
    ts_ds = connect_target_data(hub_path, TargetType.ORACLE_OUTPUT)
    assert isinstance(ts_ds, pa.dataset.FileSystemDataset)
    assert len(ts_ds.files) == 5
    assert ts_ds.to_table().column_names == ['target_end_date', 'target', 'location', 'output_type', 'output_type_id',
                                             'oracle_value']
    assert ts_ds.count_rows() == 627
    assert pc.unique(ts_ds.to_table()['target']).to_pylist() == ['wk flu hosp rate', 'wk inc flu hosp',
                                                                 'wk flu hosp rate category']
    assert ts_ds.schema == create_target_data_schema(hub_path, TargetType.ORACLE_OUTPUT)


def test_v6_target_file_hub():
    hub_path = Path('test/hubs/v6_target_file')  # target-data/oracle-output.csv
    ts_ds = connect_target_data(hub_path, TargetType.ORACLE_OUTPUT)
    assert isinstance(ts_ds, pa.dataset.FileSystemDataset)
    assert len(ts_ds.files) == 1
    assert ts_ds.to_table().column_names == ['target_end_date', 'target', 'location', 'output_type', 'output_type_id',
                                             'oracle_value']
    assert ts_ds.count_rows() == 627
    assert pc.unique(ts_ds.to_table()['target']).to_pylist() == ['wk flu hosp rate', 'wk flu hosp rate category',
                                                                 'wk inc flu hosp']


def test_v6_target_file_parquet(tmp_path):
    # case: target-data/oracle-output.parquet . note that we create the test hub dynamically based on v6_target_file
    tmp_path = Path(tmp_path)
    shutil.copytree('test/hubs/v6_target_file', tmp_path, dirs_exist_ok=True)
    pa_table = csv.read_csv(tmp_path / 'target-data/oracle-output.csv')
    parquet.write_table(pa_table, tmp_path / 'target-data/oracle-output.parquet')
    os.remove(tmp_path / 'target-data/oracle-output.csv')  # o/w invalid

    ts_ds = connect_target_data(tmp_path, TargetType.ORACLE_OUTPUT)
    assert isinstance(ts_ds, pa.dataset.FileSystemDataset)
    assert len(ts_ds.files) == 1
    assert ts_ds.to_table().column_names == ['target_end_date', 'target', 'location', 'output_type', 'output_type_id',
                                             'oracle_value']
    assert ts_ds.count_rows() == 627
    assert pc.unique(ts_ds.to_table()['target']).to_pylist() == ['wk flu hosp rate', 'wk flu hosp rate category',
                                                                 'wk inc flu hosp']
