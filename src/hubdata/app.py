
import click
import pyarrow as pa
import structlog
from rich.console import Console, Group
from rich.panel import Panel

from hubdata import connect_hub
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
    try:
        hub_connection = connect_hub(hub_path)
    except Exception as ex:
        print(f'error connecting to hub: {ex}')
        return

    # create the hub_path group lines
    hub_path_lines = ['[b]hub_path[/b]:',
                     f'- {hub_path}']

    # create the schema group lines
    schema_lines = ['\n[b]schema[/b]:']
    for field in sorted(hub_connection.schema, key=lambda _: _.name):  # sort schema fields by name for consistency
        schema_lines.append(f'- [green]{field.name}[/green]: [bright_magenta]{field.type}[/bright_magenta]')

    # finally, print a Panel containing all the groups
    console = Console()
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
    try:
        hub_connection = connect_hub(hub_path)
    except Exception as ex:
        print(f'error connecting to hub: {ex}')
        return

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
    num_rows = hub_ds.count_rows()
    dataset_lines = ['\n[b]dataset[/b]:',
                     f'- [green]files[/green]: [bright_magenta]{num_files:,}[/bright_magenta]',
                     f'- [green]types[/green]: [bright_magenta]{found_file_types} (found) | {admin_file_types} (admin)'
                     f'[/bright_magenta]',
                     f'- [green]rows[/green]: [bright_magenta]{num_rows:,}[/bright_magenta]']

    # finally, print a Panel containing all the groups
    console = Console()
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


if __name__ == '__main__':
    cli()
