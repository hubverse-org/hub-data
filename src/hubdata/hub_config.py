import json
from pathlib import Path


class HubConfig:
    """Provides convenient access to various parts of a hub's `tasks.json` file.

    Attributes
    ----------
    hub_dir : pathlib.Path
        Path to a hub's root directory.
        (see `Hubverse documentation <https://hubverse.io/en/latest/user-guide/hub-structure.html>`_)
    tasks : dict
        The hub's `tasks.json` contents
    model_metadata_schema : dict
        The hub's `model-metadata-schema.json` contents
    """

    def __init__(self, hub_dir: Path):
        """Initialize the HubConfig object.

        Parameters
        ----------
        param hub_dir : pathlib.Path
            Path to a hub's root directory.
            (see `Hubverse documentation <https://hubverse.io/en/latest/user-guide/hub-structure.html>`_)
        """

        self.hub_dir = hub_dir
        if not self.hub_dir.exists():
            raise RuntimeError(f'hub_dir not found: {self.hub_dir}')

        with open(self.hub_dir / 'hub-config' / 'tasks.json') as fp:
            self.tasks: dict = json.load(fp)

        with open(self.hub_dir / 'hub-config' / 'model-metadata-schema.json') as fp:
            self.model_metadata_schema: dict = json.load(fp)
