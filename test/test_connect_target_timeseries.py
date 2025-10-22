import os
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as csv
import pyarrow.parquet as parquet
import pytest

from hubdata.connect_target_timeseries import connect_target_timeseries
from hubdata.create_timeseries_schema import create_timeseries_schema


def test_no_time_series_data(tmp_path):
    # case: no target-data/time-series.csv, target-data/time-series.parquet, or target-data/time-series/ . note that we
    # create the test hub dynamically based on v6_target_file
    tmp_path = Path(tmp_path)
    shutil.copytree('test/hubs/v6_target_file', tmp_path, dirs_exist_ok=True)
    os.remove(tmp_path / 'target-data/time-series.csv')
    with pytest.raises(RuntimeError, match='did not find time-series.csv, time-series.parquet, or time-series/'):
        connect_target_timeseries(tmp_path)


def test_more_than_one_time_series_data(tmp_path):
    # case: add a second file (target-data/time-series.parquet) in addition to target-data/time-series.csv . note that
    # we create the test hub dynamically based on v6_target_file
    tmp_path = Path(tmp_path)
    shutil.copytree('test/hubs/v6_target_file', tmp_path, dirs_exist_ok=True)
    pa_table = csv.read_csv(tmp_path / 'target-data/time-series.csv')
    parquet.write_table(pa_table, tmp_path / 'target-data/time-series.parquet')
    with pytest.raises(RuntimeError, match='found more than one time-series.csv, time-series.parquet, or time-series/'):
        connect_target_timeseries(tmp_path)


def test_flu_metrocast():
    hub_path = Path('test/hubs/flu-metrocast')  # target-data/time-series.csv
    ts_ds = connect_target_timeseries(hub_path)
    assert isinstance(ts_ds, pa.dataset.FileSystemDataset)
    assert len(ts_ds.files) == 1
    assert ts_ds.to_table().column_names == ['target', 'target_end_date', 'location', 'as_of', 'observation']
    assert ts_ds.count_rows() == 100
    assert pc.unique(ts_ds.to_table()['target']).to_pylist() == ['ILI ED visits', 'Flu ED visits pct']
    assert ts_ds.schema == create_timeseries_schema(hub_path)


def test_v6_target_dir():
    # target-data/time-series/target=wk%20flu%20hosp%20rate/part-0.parquet  # 33 rows
    # target-data/time-series/target=wk%20inc%20flu%20hosp/part-0.parquet  # ""
    hub_path = Path('test/hubs/v6_target_dir')
    ts_ds = connect_target_timeseries(hub_path)
    assert isinstance(ts_ds, pa.dataset.FileSystemDataset)
    assert len(ts_ds.files) == 2
    assert ts_ds.to_table().column_names == ['target_end_date', 'target', 'location', 'observation']
    assert ts_ds.count_rows() == 66
    assert pc.unique(ts_ds.to_table()['target']).to_pylist() == ['wk flu hosp rate', 'wk inc flu hosp']  # partitions
    assert ts_ds.schema == create_timeseries_schema(hub_path)


def test_v6_target_file_hub():
    hub_path = Path('test/hubs/v6_target_file')  # target-data/time-series.csv
    ts_ds = connect_target_timeseries(hub_path)
    assert isinstance(ts_ds, pa.dataset.FileSystemDataset)
    assert len(ts_ds.files) == 1
    assert ts_ds.to_table().column_names == ['target_end_date', 'target', 'location', 'observation']
    assert ts_ds.count_rows() == 66
    assert pc.unique(ts_ds.to_table()['target']).to_pylist() == ['wk inc flu hosp', 'wk flu hosp rate']


def test_v6_target_file_parquet(tmp_path):
    # case: target-data/time-series.parquet . note that we create the test hub dynamically based on v6_target_file
    tmp_path = Path(tmp_path)
    shutil.copytree('test/hubs/v6_target_file', tmp_path, dirs_exist_ok=True)
    pa_table = csv.read_csv(tmp_path / 'target-data/time-series.csv')
    parquet.write_table(pa_table, tmp_path / 'target-data/time-series.parquet')
    os.remove(tmp_path / 'target-data/time-series.csv')  # o/w invalid

    ts_ds = connect_target_timeseries(tmp_path)
    assert isinstance(ts_ds, pa.dataset.FileSystemDataset)
    assert len(ts_ds.files) == 1
    assert ts_ds.to_table().column_names == ['target_end_date', 'target', 'location', 'observation']
    assert ts_ds.count_rows() == 66
    assert pc.unique(ts_ds.to_table()['target']).to_pylist() == ['wk inc flu hosp', 'wk flu hosp rate']
