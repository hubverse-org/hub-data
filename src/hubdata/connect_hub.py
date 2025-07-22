import json
import os
from pathlib import Path
from typing import Iterable

import pyarrow as pa
import pyarrow.dataset as ds
import structlog
from cloudpathlib import AnyPath, S3Client, S3Path
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
    - hub_path: os.PathLike pointing to a hub's root directory as passed to `connect_hub()`
    - schema: the pa.Schema for `HubConnection.get_dataset()`. created by the constructor via `create_hub_schema()`
    - admin: the hub's `admin.json` contents as a dict
    - tasks: "" `tasks.json` ""
    - model_output_dir: Path to the hub's model output directory
    """


    def __init__(self, hub_path: str | os.PathLike):
        """
        :param hub_path: str or Path pointing to a hub's root directory as passed to `connect_hub()`
        """
        # set self.hub_path using cloudpath. note that we do some work if it's an S3Path to make it function with public
        # buckets without requiring credentials (o/w get NoCredentialsError)
        anypath = AnyPath(hub_path)
        if isinstance(anypath, S3Path):
            anypath = S3Client(no_sign_request=True).CloudPath(str(anypath))  # str() -> input string
        self.hub_path: os.PathLike = anypath

        # set self.admin and self.tasks, checking for existence
        try:
            with open(self.hub_path / 'hub-config/admin.json') as admin_fp, \
                    open(self.hub_path / 'hub-config/tasks.json') as tasks_fp:
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
            with open(self.hub_path / 'hub-config/model-metadata-schema.json') as model_metadata_fp:
                self.model_metadata_schema = json.load(model_metadata_fp)
        except Exception as ex:
            self.model_metadata_schema = None
            logger.warn(f'model-metadata-schema.json not found: {ex!r}')

        # set self.model_output_dir, first checking for directory existence
        model_output_dir = self.hub_path / self._model_output_dir_name()
        if not model_output_dir.exists():
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
        # get an arrow FileSystem for hub_path, letting it decide the correct subclass based on that arg, catching any
        # errors. we set `from_uri()`'s `uri` argument based on whether self.hub_path is a Path (i.e., a local
        # filesystem-based hub) or an S3Path (an S3-based hub). for the latter we use `str()` to get the input string
        # that it was passed, e.g., 's3://covid-variant-nowcast-hub'
        try:
            filesystem, filesystem_path = fs.FileSystem.from_uri(
                self.hub_path if isinstance(self.hub_path, Path) else str(self.hub_path))
        except Exception:
            raise RuntimeError(f'invalid hub_path: {self.hub_path}')

        # create the dataset. NB: we are using dataset "directory partitioning" to automatically get the `model_id`
        # column from directory names. regarding performance on S3-based datasets, we default `exclude_invalid_files` to
        # False, which speeds up pyarrow's dataset processing, but opens the door to errors: "unsupported files may be
        # present in the Dataset (resulting in an error at scan time)". we prevent this from happening by manually
        # constructing and passing `ignore_prefixes` based on file extensions. this method accepts `ignore_files` to
        # allow custom prefixes to ignore. it defaults to common ones for hubs

        # NB: we force file_formats to .parquet if not a LocalFileSystem (e.g., an S3FileSystem). otherwise we use the
        # list from self.admin['file_format']
        file_formats = ['parquet'] if not isinstance(filesystem, fs.LocalFileSystem) else self.admin['file_format']
        model_out_files = self._list_model_out_files()  # model_output_dir, type='file'
        datasets = []
        file_format_to_ignore_files: dict[str, list[os.PathLike]] = {}  # for warning
        for file_format in file_formats:
            _ignore_files = self._list_invalid_format_files(model_out_files, file_format, ignore_files)
            file_format_to_ignore_files[file_format] = _ignore_files
            dataset = ds.dataset(f'{filesystem_path}/{self._model_output_dir_name()}', filesystem=filesystem,
                                 format=file_format,
                                 schema=self.schema, partitioning=['model_id'],  # NB: hard-coded partitioning!
                                 exclude_invalid_files=exclude_invalid_files,
                                 ignore_prefixes=[path.stem for path in _ignore_files])
            datasets.append(dataset)
        datasets = [dataset for dataset in datasets if len(dataset.files) != 0]
        self._warn_unopened_files(model_out_files, ignore_files, file_format_to_ignore_files)
        if len(datasets) == 1:
            return datasets[0]
        else:
            return ds.dataset([dataset for dataset in datasets
                               if isinstance(dataset, pa.dataset.FileSystemDataset) and (len(dataset.files) != 0)])


    def _model_output_dir_name(self):
        return self.admin['model_output_dir'] if 'model_output_dir' in self.admin else 'model-output'


    def _list_model_out_files(self) -> list[os.PathLike]:
        """
        get_dataset() helper that returns a list of all files of any type in self.model_output_dir. note that for now
        uses FileSystem.get_file_info() regardless of whether it's a LocalFileSystem or S3FileSystem. also note that no
        filtering of files is done, i.e., invalid files might be included
        """
        return [path for path in self.model_output_dir.glob('**/*') if path.is_file()]


    @staticmethod
    def _list_invalid_format_files(model_out_files: list[os.PathLike], file_format: str,
                                   ignore_files_default: Iterable[str]) -> list[os.PathLike]:
        """
        get_dataset() helper that returns a list of file paths in `model_out_files` that do *not* match the
        `file_format` extension
        """
        return [path for path in model_out_files
                if (path.suffix != f'.{file_format}')  # pathlib wants the dot for suffixes
                or any([path.name.startswith(ignore_file) for ignore_file in ignore_files_default])]


    @staticmethod
    def _warn_unopened_files(model_out_files: list[os.PathLike], ignore_files_default: Iterable[str],
                             file_format_to_ignore_files: dict[str, list[os.PathLike]]):
        """
        get_dataset() helper
        """


        def is_present_all_file_formats(file_info):
            return all([file_info in ignore_files for ignore_files in file_format_to_ignore_files.values()])


        # warn about files in model_out_files that are present in all file_format_to_ignore_files.values(), i.e., that
        # were never OK for any file_format
        unopened_files = [path for path in model_out_files
                          if is_present_all_file_formats(path)
                          and not any([path.stem.startswith(ignore_file) for ignore_file in ignore_files_default])]

        if unopened_files:
            plural = 's' if len(unopened_files) > 1 else ''
            logger.warn(f'ignored {len(unopened_files)} file{plural}: {unopened_files}')


    def to_table(self, *args, **kwargs) -> pa.Table:
        """
        A convenience function that simply passes args and kwargs to `pyarrow.dataset.Dataset.to_table()`, returning the
        `pyarrow.Table`.
        """
        return self.get_dataset().to_table(*args, **kwargs)
