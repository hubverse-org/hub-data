# Changelog

All notable changes to `hubdata` are documented here.

## Unreleased

### Added

- Added support for user-specified directory-style partitioning of model output data via a new `partitions` argument to `connect_hub()` (the Python analogue of the R hubData package's `connect_hub()` `partitions` argument). Pass a dict mapping directory partition column names to their pyarrow data types, applied in order from the outermost to the innermost directory level (e.g., `partitions={'round_id': pa.date32(), 'model_id': pa.string()}`). The default (`{'model_id': pa.string()}`) preserves the previous behavior; pass an empty dict to disable directory partitioning. Also fixed the `partitions` type annotations in `create_hub_schema()` to accept any number of partitions.

## 0.2.0

### Added

- Added support for [Target (Observed) Data](https://docs.hubverse.io/en/latest/user-guide/target-data.html) via the two new API functions `create_target_data_schema()` and `connect_target_data()`, along with CLI support via two new subcommands (`time-series` and `oracle-output`).

### Changed

- N/A

### Internal

- N/A

## 0.1.5

### Added

- N/A

### Changed

- N/A

### Internal

- Correcting a workflow release issue.

## 0.1.4

### Added

- N/A

### Changed

- Added a documentation link back to the repo - see the issue [add a link to the GitHub in the documentation front page and on the pypi listing #51](https://github.com/hubverse-org/hub-data/issues/51)

### Internal

- N/A

## 0.1.3

### Added

- Added the `HubConnection.model_metadata_schema` property

### Changed

- Fixed a bug in `create_hub_schema()` where it was allowing `tasks.json` `"required": null` and `"optional": null` values to influence type inference - see the closed issue [create_hub_schema() does not match R version for FluSight-forecast-hub #45](https://github.com/hubverse-org/hub-data/issues/45)

### Internal

- N/A

## 0.1.2

### Added

- N/A

### Changed

- Small documentation updates

### Internal

- N/A

## 0.1.1

### Added

- Initial release
- Includes automatic building and publishing to [pypi.org](https://pypi.org/project/hubdata/)
- Includes documentation under **docs/source**

### Changed

- N/A

### Internal

- N/A
