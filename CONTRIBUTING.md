# Contributing to hubdata

## Reporting bugs

If something isn't working as described, or if you find a mistake in the documentation, please feel free to report a bug by [opening an issue](https://github.com/hubverse-org/hub-data/issues/new).

## Contributing to the code base

Contributions to the code base are welcome. If you want to add a new feature, please open an issue before doing any work, to ensure that the suggestion aligns with the project's goals and overall direction.

If you'd like to tackle an existing issue, please leave a comment on it.

### Submitting code changes

After you've completed the changes described in the issue you're working on, you can submit them by [creating a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork) (PR) to this repository.

Please ensure the following are true before creating the PR:

- Your change is covered by tests, if applicable
- Project documentation is updated, if applicable
- The following local dev commands pass (see [dev.md](docs/source/dev.md)):
    - `uv run pytest`
    - `uv run ruff check`
    - `uv tool run mypy . --ignore-missing-imports --disable-error-code=attr-defined`
- The `## unreleased` section of [CHANGELOG.md](CHANGELOG.md) contains a description of your change

The PR itself should:

- Have a descriptive title
- Be [linked to its corresponding issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue) in the description
- Have a description that includes any other information or context that will help a code reviewer understand your changes
