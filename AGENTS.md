# Agent guidance

## Project overview

`aws-syndicate` is a Python 3.14 command-line tool for building and deploying
serverless resources to AWS. The main package is under `syndicate/`; unit tests
are under `tests/unit/`, smoke tests are under `tests/smoke/`, and runnable
examples are under `examples/`. Detailed generated-project guidance is in
`docs/python-project-structure-golden-standard.md`.

## Development commands

Use the repository virtual environment or `uv`:

```shell
uv sync --extra test
uv run --extra test python -m pytest tests/unit -q
uv build --out-dir .tmp-dist
```

The smoke tests require AWS credentials, an AWS account, and deployed test
resources. Do not run them unless the user explicitly requests it and provides
the required environment.

## AWS safety

- Do not run `syndicate deploy`, `syndicate update`, `syndicate clean`, or any
  other AWS-mutating command without explicit user approval.
- Confirm the intended AWS account, region, and resource scope before an
  approved deployment operation.
- Never add credentials, tokens, account secrets, or generated credential files
  to the repository.
- Keep unit tests offline and mock AWS clients at their boundary.

## Change conventions

- Keep active Python runtime references on `python3.14`; historical changelog
  entries should remain unchanged.
- Add unit tests in the existing `unittest` style under `tests/unit/`.
- Preserve existing public APIs and avoid unrelated refactoring.
- Do not commit generated directories or files such as `.pytest_cache/`,
  `dist/`, `.tmp-dist/`, or `aws_syndicate.egg-info/`.
