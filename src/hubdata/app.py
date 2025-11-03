from pathlib import Path

import click
import pyarrow as pa
import structlog
from rich.console import Console, Group
from rich.panel import Panel

from hubdata import connect_hub, connect_target_data
from hubdata.create_target_data_schema import TargetType
from hubdata.logging import setup_logging

setup_logging()
logger = structlog.get_logger()


@click.group()
def cli():
    pass


@cli.command(name='schema')
@click.argument('hub_path')
def print_schema(hub_path):
    """
    A subcommand that prints the output of `create_hub_schema()` for `hub_path`.

    :param hub_path: as passed to `connect_hub()`: either a local file system hub path or a cloud-based hub URI.
        Note: A local file system path must be an ABSOLUTE path and not a relative one
    """
    console = Console()
    try:
        with console.status('Connecting to hub...'):
            hub_connection = connect_hub(hub_path)
    except Exception as ex:
        print(f'There was a problem connecting to hub: {ex}')
        return

    # create the hub_path group lines
    hub_path_lines = ['[b]hub_path[/b]:',
                      f'- {hub_path}']

    # create the schema group lines
    schema_lines = ['\n[b]schema[/b]:']
    for field in sorted(hub_connection.schema, key=lambda _: _.name):  # sort schema fields by name for consistency
        schema_lines.append(f'- [green]{field.name}[/green]: [bright_magenta]{field.type}[/bright_magenta]')

    # finally, print a Panel containing all the groups
    console.print(
        Panel(
            Group(Group(*hub_path_lines), Group(*schema_lines)),
            border_style='green',
            expand=False,
            padding=(1, 2),
            subtitle='[italic]hubdata[/italic]',
            subtitle_align='right',
            title='[bright_red]schema[/bright_red]',
            title_align='left')
    )


@cli.command(name='dataset')
@click.argument('hub_path')
def print_dataset_info(hub_path):
    """
    A subcommand that prints dataset information for `hub_path`.

    :param hub_path: as passed to `connect_hub()`: either a local file system hub path or a cloud-based hub URI.
        Note: A local file system path must be an ABSOLUTE path and not a relative one
    """
    console = Console()
    try:
        with console.status('Connecting to hub...'):
            hub_connection = connect_hub(hub_path)
    except Exception as ex:
        print(f'There was a problem connecting to hub: {ex}')
        return

    with console.status('Getting dataset...'):
        hub_ds = hub_connection.get_dataset()
    if not isinstance(hub_ds, pa.dataset.FileSystemDataset) and not isinstance(hub_ds, pa.dataset.UnionDataset):
        print(f'unsupported dataset type: {type(hub_ds)}')
        return

    # create the hub_path group lines
    hub_path_lines = ['[b]hub_path[/b]:',
                      f'- {hub_path}']

    # create the schema group lines
    schema_lines = ['\n[b]schema[/b]:']
    for field in sorted(hub_connection.schema, key=lambda _: _.name):  # sort schema fields by name for consistency
        schema_lines.append(f'- [green]{field.name}[/green]: [bright_magenta]{field.type}[/bright_magenta]')

    # create the dataset group lines
    filesystem_datasets = hub_ds.children if isinstance(hub_ds, pa.dataset.UnionDataset) else [hub_ds]
    num_files = sum([len(child_ds.files) for child_ds in filesystem_datasets])
    found_file_types = ', '.join([child_ds.format.default_extname for child_ds in filesystem_datasets])
    admin_file_types = ', '.join(hub_connection.admin['file_format'])
    dataset_lines = ['\n[b]dataset[/b]:',
                     f'- [green]files[/green]: [bright_magenta]{num_files:,}[/bright_magenta]',
                     f'- [green]types[/green]: [bright_magenta]{found_file_types} (found) | {admin_file_types} (admin)'
                     f'[/bright_magenta]']

    # finally, print a Panel containing all the groups
    console.print(
        Panel(
            Group(Group(*hub_path_lines), Group(*schema_lines), Group(*dataset_lines)),
            border_style='green',
            expand=False,
            padding=(1, 2),
            subtitle='[italic]hubdata[/italic]',
            subtitle_align='right',
            title='[bright_red]dataset[/bright_red]',
            title_align='left')
    )


@cli.command(name='time-series')
@click.argument('hub_path')
def print_target_data_time_series(hub_path):
    """
    A subcommand that prints target data time-series information for `hub_path`, including its schema.

    :param hub_path: as passed to `connect_hub()`: either a local file system hub path or a cloud-based hub URI.
        Note: A local file system path must be an ABSOLUTE path and not a relative one
    """
    _print_target_data(hub_path, True)


@cli.command(name='oracle-output')
@click.argument('hub_path')
def print_target_data_oracle_output(hub_path):
    """
    A subcommand that prints target data oracle-output information for `hub_path`, including its schema.

    :param hub_path: as passed to `connect_hub()`: either a local file system hub path or a cloud-based hub URI.
        Note: A local file system path must be an ABSOLUTE path and not a relative one
    """
    _print_target_data(hub_path, False)


def _print_target_data(hub_path, is_time_series: bool):
    console = Console()
    try:
        with console.status('Connecting to hub target data...'):
            td_conn = connect_target_data(hub_path,
                                          TargetType.TIME_SERIES if is_time_series else TargetType.ORACLE_OUTPUT)
    except Exception as ex:
        print(f'There was a problem connecting to hub target data: {ex}')
        return

    # create the hub_path group lines
    hub_path_lines = ['[b]hub_path[/b]:',
                      f'- {hub_path}']

    target_type_str = 'time-series' if is_time_series else 'oracle-output'
    target_type_lines = ['\n[b]target type[/b]:',
                         f'- {target_type_str}']

    # create the schema group lines. NB: the Dataset's schema might have been inferred
    schema_lines = ['\n[b]schema[/b]:']
    schema = td_conn.schema
    if schema is None:
        schema_lines.append('- [green]None (inferred from data)[/green]')
    else:
        for field in sorted(schema, key=lambda _: _.name):  # sort schema fields by name for consistency
            schema_lines.append(f'- [green]{field.name}[/green]: [bright_magenta]{field.type}[/bright_magenta]')

    target_data_ds = td_conn.get_dataset()
    num_files = len(target_data_ds.files)
    extname = target_data_ds.format.default_extname
    loc_path = Path(td_conn.found_file_info.path)
    location_str = loc_path.parts[-1] + (' (file)' if td_conn.found_file_info.is_file else ' (dir)')
    dataset_lines = ['\n[b]dataset[/b]:',
                     f'- [green]location[/green]: [bright_magenta]{location_str}[/bright_magenta]',
                     f'- [green]files[/green]: [bright_magenta]{num_files:,}[/bright_magenta]',
                     f'- [green]type[/green]: [bright_magenta]{extname}[/bright_magenta]']

    # finally, print a Panel containing all the groups
    console.print(
        Panel(
            Group(Group(*hub_path_lines), Group(*target_type_lines), Group(*schema_lines), Group(*dataset_lines)),
            border_style='green',
            expand=False,
            padding=(1, 2),
            subtitle='[italic]hubdata[/italic]',
            subtitle_align='right',
            title='[bright_red]target data[/bright_red]',
            title_align='left')
    )


if __name__ == '__main__':
    cli()
