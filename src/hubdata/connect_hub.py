import json
from pathlib import Path

import pyarrow as pa
import pyarrow.dataset as ds
import structlog
from pyarrow import fs

from hubdata.create_hub_schema import create_hub_schema

logger = structlog.get_logger()


def connect_hub(hub_path: str | Path):
    """
    The main entry point for connecting to a hub, providing access to the instance variables documented in
    `HubConnection`, including admin.json and tasks.json as dicts. It also allows connecting to data in the hub's model
    output directory for querying and filtering across all model files. The hub can be located in a local file system or
    in the cloud on AWS or GCS. Note: Calls `create_hub_schema()` to get the schema to use when calling
    `HubConnection.get_dataset()`. See: https://docs.hubverse.io/en/latest/user-guide/hub-structure.html for details on
    how hubs directories are laid out.

    :param hub_path: str (for local file system hubs or cloud based ones) or Path (local file systems only) pointing to
        a hub's root directory. it is passed to https://arrow.apache.org/docs/python/generated/pyarrow.fs.FileSystem.html#pyarrow.fs.FileSystem.from_uri
        From that page:
            Recognized URI schemes are “file”, “mock”, “s3fs”, “gs”, “gcs”, “hdfs” and “viewfs”. In addition, the
            argument can be a pathlib.Path object, or a string describing an absolute local path.
    :return: a HubConnection
    :raise: RuntimeError if `hub_path` is invalid
    """
    return HubConnection(hub_path)


class HubConnection:
    """
    Provides convenient access to various parts of a hub's `tasks.json` file. Use the `connect_hub` function to create
    instances of this class, rather than by direct instantiation

    Instance variables:
    - hub_path: str pointing to a hub's root directory as passed to `connect_hub()`
    - schema: the pa.Schema for `HubConnection.get_dataset()`. created by the constructor via `create_hub_schema()`
    - admin: the hub's `admin.json` contents as a dict
    - tasks: "" `tasks.json` ""
    - model_output_dir: Path to the hub's model output directory
    """


    def __init__(self, hub_path: str | Path):
        """
        :param hub_path: str or Path pointing to a hub's root directory as passed to `connect_hub()`
        """
        # set self.hub_path and then get an arrow FileSystem for it, letting it decide the correct subclass based on
        # that arg, catching any errors. also set two internal instance variables used by HubConnection.get_dataset():
        # self._filesystem and self._filesystem_path
        self.hub_path: str | Path = hub_path
        try:
            self._filesystem, self._filesystem_path = fs.FileSystem.from_uri(self.hub_path)
        except Exception:
            raise RuntimeError(f'invalid hub_path: {self.hub_path}')

        # set self.admin and self.tasks, checking for existence
        try:
            with self._filesystem.open_input_file(f'{self._filesystem_path}/hub-config/admin.json') as admin_fp, \
                    self._filesystem.open_input_file(f'{self._filesystem_path}/hub-config/tasks.json') as tasks_fp:
                self.admin = json.load(admin_fp)
                self.tasks = json.load(tasks_fp)
        except Exception as ex:
            raise RuntimeError(f'admin.json or tasks.json not found: {ex}')

        # set schema
        self.schema = create_hub_schema(self.tasks)

        # set self.model_output_dir, first checking for directory existence
        model_output_dir_name = self.admin['model_output_dir'] if 'model_output_dir' in self.admin else 'model-output'
        model_output_dir = f'{self._filesystem_path}/{model_output_dir_name}'
        if self._filesystem.get_file_info(model_output_dir).type == fs.FileType.NotFound:
            logger.warn(f'model_output_dir not found: {model_output_dir!r}')
        self.model_output_dir = model_output_dir


    def get_dataset(self) -> ds:
        """
        :return: a pyarrow.dataset.Dataset for my model_output_dir
        """
        # create the dataset. NB: we are using dataset "directory partitioning" to automatically get the `model_id`
        # column from directory names

        # NB: we force file_formats to .parquet if not a LocalFileSystem (e.g., an S3FileSystem). otherwise we use the
        # list from self.admin['file_format']
        file_formats = ['parquet'] if not isinstance(self._filesystem, fs.LocalFileSystem) \
            else self.admin['file_format']
        schema = create_hub_schema(self.tasks)
        datasets = [ds.dataset(self.model_output_dir, filesystem=self._filesystem, format=file_format,
                               partitioning=['model_id'],  # NB: hard-coded partitioning!
                               exclude_invalid_files=True, schema=schema)
                    for file_format in file_formats]
        datasets = [dataset for dataset in datasets if len(dataset.files) != 0]
        if len(datasets) == 1:
            return datasets[0]
        else:
            return ds.dataset([dataset for dataset in datasets
                               if isinstance(dataset, pa.dataset.FileSystemDataset) and (len(dataset.files) != 0)])


    def to_table(self, *args, **kwargs) -> pa.Table:
        """
        A helper function that simply passes args and kwargs to `pyarrow.dataset.Dataset.to_table()`, returning the
        `pyarrow.Table`.
        """
        return self.get_dataset().to_table(*args, **kwargs)
