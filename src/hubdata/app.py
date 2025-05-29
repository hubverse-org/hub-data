import pathlib

import click
import structlog
from rich.console import Console, Group
from rich.panel import Panel

from hubdata import HubConfig, create_hub_schema
from hubdata.logging import setup_logging

setup_logging()
logger = structlog.get_logger()


@click.group()
def cli():
    pass


@cli.command(name='schema')
@click.argument('hub_dir', type=click.Path(file_okay=False, exists=True, path_type=pathlib.Path))
def print_schema(hub_dir):
    """
    A subcommand that prints the schema for `hub_dir`.
    """
    hub_config = HubConfig(hub_dir)
    schema = create_hub_schema(hub_config.tasks)
    rounds = hub_config.tasks['rounds']
    console = Console()

    # create the hub_dir group lines
    hub_dir_lines = ['[b]hub_dir[/b]:',
                     f'- {hub_dir}']

    # create the rounds group lines
    rounds_lines = [f'\n[b]rounds[/b] ({len(rounds)}):']
    for the_round in rounds:
        plural = 's' if len(the_round['model_tasks']) > 1 else ''
        rounds_lines.append(f'- [green]{the_round['round_id']}[/green] ({len(the_round['model_tasks'])} '
                            f'model task{plural})')

    # create the schema group lines
    schema_lines = ['\n[b]schema[/b]:']
    for field in sorted(schema, key=lambda _: _.name):
        schema_lines.append(f'- [green]{field.name}[/green]: [bright_magenta]{field.type}[/bright_magenta]')

    # finally, print a Panel containing all the groups
    console.print(
        Panel(
            Group(Group(*hub_dir_lines), Group(*rounds_lines), Group(*schema_lines)),
            border_style='green',
            expand=False,
            padding=(1, 2),
            subtitle='[italic]hubdata[/italic]',
            subtitle_align='right',
            title=f'[bright_red]{hub_dir.name}[/bright_red]',
            title_align='left')
    )


if __name__ == '__main__':
    cli()
