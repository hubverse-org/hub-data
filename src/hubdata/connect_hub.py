import json
from pathlib import Path
from typing import Iterable

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
        From that page: Recognized URI schemes are “file”, “mock”, “s3fs”, “gs”, “gcs”, “hdfs” and “viewfs”. In
        addition, the argument can be a local path, either a pathlib.Path object or a str. NB: Passing a local path as a
        str requires an ABSOLUTE path, but passing the hub as a Path can be a relative path.
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

        # set self.model_metadata_schema, first checking for model-metadata-schema.json existence. warn (not error) if
        # not found to be consistent with R hubData
        self.model_metadata_schema: dict | None = None
        try:
            with (self._filesystem.open_input_file(f'{self._filesystem_path}/hub-config/model-metadata-schema.json')
                  as model_metadata_fp):
                self.model_metadata_schema = json.load(model_metadata_fp)
        except Exception as ex:
            self.model_metadata_schema = None
            logger.warn(f'model-metadata-schema.json not found: {ex!r}')

        # set self.model_output_dir, first checking for directory existence
        model_output_dir_name = self.admin['model_output_dir'] if 'model_output_dir' in self.admin else 'model-output'
        model_output_dir = f'{self._filesystem_path}/{model_output_dir_name}'
        if self._filesystem.get_file_info(model_output_dir).type == fs.FileType.NotFound:
            logger.warn(f'model_output_dir not found: {model_output_dir!r}')
        self.model_output_dir = model_output_dir


    def get_dataset(self, exclude_invalid_files: bool = False,
                    ignore_files: Iterable[str] = ('README', '.DS_Store')) -> ds:
        """
        Main entry point for getting a pyarrow dataset to work with. Prints a warning about any files that were skipped
        during dataset file discovery.

        :param: exclude_invalid_files: variable passed through to pyarrow's `dataset.dataset()` method. defaults to
            False, which works for most situations
        :param: ignore_files a str list of file **names** (not paths) or file **prefixes** to ignore when discovering
            model output files to include in dataset connections. Parent directory names should not be included. The
            default is to ignore the common files `"README"` and `".DS_Store"`, but additional files can be excluded by
            specifying them here.
        :return: a pyarrow.dataset.Dataset for my model_output_dir
        """
        # create the dataset. NB: we are using dataset "directory partitioning" to automatically get the `model_id`
        # column from directory names. regarding performance on S3-based datasets, we default `exclude_invalid_files` to
        # False, which speeds up pyarrow's dataset processing, but opens the door to errors: "unsupported files may be
        # present in the Dataset (resulting in an error at scan time)". we prevent this from happening by manually
        # constructing and passing `ignore_prefixes` based on file extensions. this method accepts `ignore_files` to
        # allow custom prefixes to ignore. it defaults to common ones for hubs

        # NB: we force file_formats to .parquet if not a LocalFileSystem (e.g., an S3FileSystem). otherwise we use the
        # list from self.admin['file_format']
        file_formats = ['parquet'] if not isinstance(self._filesystem, fs.LocalFileSystem) \
            else self.admin['file_format']
        model_out_files = self._list_model_out_files()  # model_output_dir, type='file'
        datasets = []
        file_format_to_ignore_files: dict[str, list[fs.FileInfo]] = {}  # for warning
        for file_format in file_formats:
            _ignore_files = self._list_invalid_format_files(model_out_files, file_format, ignore_files)
            file_format_to_ignore_files[file_format] = _ignore_files
            dataset = ds.dataset(self.model_output_dir, filesystem=self._filesystem, format=file_format,
                                 schema=self.schema, partitioning=['model_id'],  # NB: hard-coded partitioning!
                                 exclude_invalid_files=exclude_invalid_files,
                                 ignore_prefixes=[file_info.base_name for file_info in _ignore_files])
            datasets.append(dataset)
        datasets = [dataset for dataset in datasets if len(dataset.files) != 0]
        self._warn_unopened_files(model_out_files, ignore_files, file_format_to_ignore_files)
        if len(datasets) == 1:
            return datasets[0]
        else:
            return ds.dataset([dataset for dataset in datasets
                               if isinstance(dataset, pa.dataset.FileSystemDataset) and (len(dataset.files) != 0)])


    def _list_model_out_files(self) -> list[fs.FileInfo]:
        """
        get_dataset() helper that returns a list of all files in self.model_output_dir. note that for now uses
        FileSystem.get_file_info() regardless of whether it's a LocalFileSystem or S3FileSystem. also note that no
        filtering of files is done, i.e., invalid files might be included
        """
        return [file_info
                for file_info in
                self._filesystem.get_file_info(fs.FileSelector(self.model_output_dir, recursive=True))
                if file_info.type == fs.FileType.File]


    @staticmethod
    def _list_invalid_format_files(model_out_files: list[fs.FileInfo], file_format: str,
                                   ignore_files_default: Iterable[str]) -> list[fs.FileInfo]:
        """
        get_dataset() helper that returns a list of file paths in `model_out_files` that do *not* match the
        `file_format` extension
        """
        return [file_info for file_info in model_out_files
                if (file_info.extension != file_format)
                or any([file_info.base_name.startswith(ignore_file) for ignore_file in ignore_files_default])]


    @staticmethod
    def _warn_unopened_files(model_out_files: list[fs.FileInfo], ignore_files_default: Iterable[str],
                             file_format_to_ignore_files: dict[str, list[fs.FileInfo]]):
        """
        get_dataset() helper
        """


        def is_present_all_file_formats(file_info):
            return all([file_info in ignore_files for ignore_files in file_format_to_ignore_files.values()])


        # warn about files in model_out_files that are present in all file_format_to_ignore_files.values(), i.e., that
        # were never OK for any file_format
        unopened_files = [model_out_file for model_out_file in model_out_files
                          if is_present_all_file_formats(model_out_file)
                          and not any([model_out_file.base_name.startswith(ignore_file)
                                       for ignore_file in ignore_files_default])]

        if unopened_files:
            plural = 's' if len(unopened_files) > 1 else ''
            logger.warn(f'ignored {len(unopened_files)} file{plural}: '
                        f'{[model_out_file.path for model_out_file in unopened_files]}')


    def to_table(self, *args, **kwargs) -> pa.Table:
        """
        A convenience function that simply passes args and kwargs to `pyarrow.dataset.Dataset.to_table()`, returning the
        `pyarrow.Table`.
        """
        return self.get_dataset().to_table(*args, **kwargs)
