from pathlib import Path

import pyarrow as pa

from hubdata.create_target_data_schema import TargetType, create_target_data_schema


def test_no_target_data_json_file():
    # make sure `create_target_data_schema()` does not raise an error if no hub-config/target-data.json is present
    assert create_target_data_schema(Path('test/hubs/v4_flusight'), TargetType.ORACLE_OUTPUT) is None


def test_ecfh():
    # hub-config/target-data.json:
    #   - observable_unit: top-level only
    #   - versioned: top-level only, false
    #   - time-series: absent
    #   - oracle-output: present. has_output_type_ids
    act_schema = create_target_data_schema(Path('test/hubs/example-complex-forecast-hub'), TargetType.ORACLE_OUTPUT)

    # REF: columns: https://github.com/hubverse-org/example-complex-forecast-hub/blob/main/target-data/oracle-output.csv
    #   location, target_end_date, target, output_type, output_type_id, oracle_value
    #   ---------------------------------  <- observable_unit
    #               has_output_type_ids -> ---------------------------
    #                                                       required -> ------------
    exp_schema = pa.schema([('target_end_date', pa.date32()),
                            ('target', pa.string()),
                            ('location', pa.string()),
                            ('output_type', pa.string()),
                            ('output_type_id', pa.string()),
                            ('oracle_value', pa.float64())])
    assert act_schema == exp_schema


def test_flu_metrocast():
    # hub-config/target-data.json:
    #   - observable_unit: top-level only
    #   - time-series: present. versioned
    #   - oracle-output: absent
    act_schema = create_target_data_schema(Path('test/hubs/flu-metrocast'), TargetType.ORACLE_OUTPUT)

    # REF: columns: https://github.com/reichlab/flu-metrocast/blob/main/target-data/oracle-output.csv
    #   target_end_date, location, target, oracle_value
    #   --------------------------------- <- observable_unit
    #                          required -> ------------
    exp_schema = pa.schema([('target', pa.string()),
                            ('target_end_date', pa.date32()),
                            ('location', pa.string()),
                            ('oracle_value', pa.float64())])
    assert act_schema == exp_schema


def test_flusight_forecast_hub():
    # hub-config/target-data.json:
    #   - observable_unit: top-level and oracle-output
    #   - versioned: top-level only, true
    #   - time-series: present. non_task_id_schema: present
    #   - oracle-output: present. has_output_type_ids, observable_unit
    act_schema = create_target_data_schema(Path('test/hubs/FluSight-forecast-hub'), TargetType.ORACLE_OUTPUT)

    # REF: columns: https://github.com/cdcepi/FluSight-forecast-hub/blob/main/target-data/oracle-output.csv
    #   as_of, target, target_end_date, location, horizon, output_type, output_type_id, oracle_value
    #   ----- <- versioned                                                  required -> -------------
    #          ------------------------------------------ <- observable_unit
    #                               has_output_type_ids -> ---------------------------
    exp_schema = pa.schema([('target', pa.string()),
                            ('target_end_date', pa.date32()),
                            ('location', pa.string()),
                            ('horizon', pa.int32()),
                            ('as_of', pa.date32()),
                            ('output_type', pa.string()),
                            ('output_type_id', pa.string()),
                            ('oracle_value', pa.float64())])
    assert act_schema == exp_schema


def test_variant_nowcast_hub():
    # hub-config/target-data.json:
    #   - observable_unit: top-level only
    #   - versioned: top-level only, true
    #   - time-series: absent
    #   - oracle-output: absent
    act_schema = create_target_data_schema(Path('test/hubs/variant-nowcast-hub'), TargetType.ORACLE_OUTPUT)

    # REF: columns: https://github.com/reichlab/variant-nowcast-hub/blob/main/target-data/oracle-output/nowcast_date%3D2024-09-11/oracle.parquet
    #  target_date, location, clade, oracle_value, nowcast_date, as_of
    #  ----------------------------                ------------ <- observable_unit
    #                    required -> ------------                ----- <- versioned
    exp_schema = pa.schema([('location', pa.string()),
                            ('clade', pa.string()),
                            ('target_date', pa.date32()),
                            ('nowcast_date', pa.date32()),
                            ('as_of', pa.date32()),
                            ('oracle_value', pa.float64())])
    assert act_schema == exp_schema


def test_v6_target_dir_hub():
    # hub-config/target-data.json:
    #   - observable_unit: top-level only
    #   - versioned: top-level only, false
    #   - time-series: absent
    #   - oracle-output: present. has_output_type_ids
    act_schema = create_target_data_schema(Path('test/hubs/v6_target_dir'), TargetType.ORACLE_OUTPUT)

    # REF: columns: /.../v6_target_dir/target-data/oracle-output/output_type=cdf/part-0.parquet
    #  location, target_end_date, target, output_type, output_type_id, oracle_value
    #  --------------------------------- <- observable_unit
    #              has_output_type_ids -> ---------------------------  (output_type is injected via partition)
    #                                                      required -> ------------
    exp_schema = pa.schema([('target_end_date', pa.date32()),
                            ('target', pa.string()),
                            ('location', pa.string()),
                            ('output_type', pa.string()),
                            ('output_type_id', pa.string()),
                            ('oracle_value', pa.float64())])
    assert act_schema == exp_schema


def test_v6_target_file_hub():
    # hub-config/target-data.json:
    #   - observable_unit: top-level only
    #   - versioned: top-level only, false
    #   - time-series: absent
    #   - oracle-output: present. has_output_type_ids
    act_schema = create_target_data_schema(Path('test/hubs/v6_target_file'), TargetType.ORACLE_OUTPUT)

    # REF: columns: /.../v6_target_file/target-data/oracle-output.csv
    #  location, target_end_date, target, output_type, output_type_id, oracle_value
    #  --------------------------------- <- observable_unit
    #              has_output_type_ids -> ---------------------------  (output_type is injected via partition)
    #                                                      required -> ------------
    exp_schema = pa.schema([('target_end_date', pa.date32()),
                            ('target', pa.string()),
                            ('location', pa.string()),
                            ('output_type', pa.string()),
                            ('output_type_id', pa.string()),
                            ('oracle_value', pa.float64())])
    assert act_schema == exp_schema
