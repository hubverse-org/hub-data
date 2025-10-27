from pathlib import Path

import pyarrow as pa

from hubdata.create_target_data_schema import TargetType, create_target_data_schema


def test_no_target_data_json_file():
    # make sure `create_timeseries_schema()` does not raise an error if no hub-config/target-data.json is present
    assert create_target_data_schema(Path('test/hubs/v4_flusight'), TargetType.TIME_SERIES) is None


def test_ecfh():
    # hub-config/target-data.json:
    #   - observable_unit: top-level only
    #   - versioned: top-level only, false
    #   - time-series: absent
    #   - oracle-output: present. has_output_type_ids
    act_schema = create_target_data_schema(Path('test/hubs/example-complex-forecast-hub'), TargetType.TIME_SERIES)

    # REF: columns: /.../example-complex-forecast-hub/target-data/time-series.csv
    #   target_end_date, target, location, observation
    #   ---------------------------------  <- observable_unit
    #                          required -> -----------
    exp_schema = pa.schema([('target_end_date', pa.date32()),
                            ('target', pa.string()),
                            ('location', pa.string()),
                            ('observation', pa.float64())])
    assert act_schema == exp_schema


def test_flu_metrocast():
    # hub-config/target-data.json:
    #   - observable_unit: top-level only
    #   - versioned: top-level only, true
    #   - time-series: absent
    #   - oracle-output: absent
    act_schema = create_target_data_schema(Path('test/hubs/flu-metrocast'), TargetType.TIME_SERIES)

    # REF: columns: /.../flu-metrocast/target-data/time-series.csv
    #   as_of, location, target, target_end_date, observation
    #   ----- <- versioned            required -> -----------
    #          ---------------------------------- <- observable_unit
    exp_schema = pa.schema([('target', pa.string()),
                            ('target_end_date', pa.date32()),
                            ('location', pa.string()),
                            ('as_of', pa.date32()),
                            ('observation', pa.float64())])
    assert act_schema == exp_schema


def test_flusight_forecast_hub():
    # hub-config/target-data.json:
    #   - observable_unit: top-level and oracle-output
    #   - versioned: top-level only, true
    #   - time-series: present. non_task_id_schema: present
    #   - oracle-output: present. has_output_type_ids, observable_unit
    act_schema = create_target_data_schema(Path('test/hubs/FluSight-forecast-hub'), TargetType.TIME_SERIES)

    # REF: columns: /.../FluSight-forecast-hub/target-data/time-series.csv
    #   as_of, target, target_end_date, location, location_name, observation, weekly_rate
    #   ----- <- versioned                           required -> -----------
    #          ---------------------------------- <- observable_unit
    #                       non_task_id_schema -> -------------               -----------
    exp_schema = pa.schema([('target', pa.string()),
                            ('target_end_date', pa.date32()),
                            ('location', pa.string()),
                            ('as_of', pa.date32()),
                            ('location_name', pa.string()),
                            ('weekly_rate', pa.float64()),
                            ('observation', pa.float64())])
    assert act_schema == exp_schema


def test_variant_nowcast_hub():
    # hub-config/target-data.json:
    #   - observable_unit: top-level only
    #   - versioned: top-level only, true
    #   - time-series: absent
    #   - oracle-output: absent
    act_schema = create_target_data_schema(Path('test/hubs/variant-nowcast-hub'), TargetType.TIME_SERIES)

    # REF: columns: https://github.com/reichlab/variant-nowcast-hub/blob/main/target-data/time-series/as_of%3D2024-10-08/nowcast_date%3D2024-09-11/timeseries.parquet
    #  target_date, location, clade, observation, nowcast_date, as_of
    #                                ----------- <- required
    #                                              versioned -> -----
    #  ----------------------------               ------------ <- observable_unit
    exp_schema = pa.schema([('location', pa.string()),
                            ('clade', pa.string()),
                            ('target_date', pa.date32()),
                            ('nowcast_date', pa.date32()),
                            ('as_of', pa.date32()),
                            ('observation', pa.float64())])
    assert act_schema == exp_schema


def test_v6_target_dir_hub():
    # hub-config/target-data.json:
    #   - observable_unit: top-level only
    #   - versioned: top-level only, false
    #   - time-series: absent
    #   - oracle-output: present. has_output_type_ids
    act_schema = create_target_data_schema(Path('test/hubs/v6_target_dir'), TargetType.TIME_SERIES)

    # REF: columns: /.../v6_target_dir/target-data/time-series/target=wk%20flu%20hosp%20rate/part-0.parquet
    #  target_end_date, target, location, observation
    #                         required -> -----------
    #  --------------------------------- <- observable_unit
    exp_schema = pa.schema([('target_end_date', pa.date32()),
                            ('target', pa.string()),
                            ('location', pa.string()),
                            ('observation', pa.float64())])
    assert act_schema == exp_schema


def test_v6_target_file_hub():
    # hub-config/target-data.json:
    #   - observable_unit: top-level only
    #   - versioned: top-level only, false
    #   - time-series: absent
    #   - oracle-output: present. has_output_type_ids
    act_schema = create_target_data_schema(Path('test/hubs/v6_target_file'), TargetType.TIME_SERIES)

    # REF: columns: /.../v6_target_file/target-data/time-series.csv
    #  target_end_date, target, location, observation
    #                         required -> -----------
    #  --------------------------------- <- observable_unit
    exp_schema = pa.schema([('target_end_date', pa.date32()),
                            ('target', pa.string()),
                            ('location', pa.string()),
                            ('observation', pa.float64())])
    assert act_schema == exp_schema
