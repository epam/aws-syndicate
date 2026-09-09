import re
from pathlib import Path

from syndicate.core.generators import _write_content_to_file

PYTHON_STANDARD_TEMPLATE = 'python-standard'

PYTHON_STANDARD_AGENTS = """# Project instructions

This file is the canonical guidance for contributors and coding agents working
on this AWS Syndicate project.

## Project map

- `lambdas/`: Python Lambda source files.
- `commons/`: shared Python application code.
- `deployment_resources.json`: generated default deployment resources.
- `tests/unit/`: fast offline tests.
- `tests/integration/`: package and CLI boundary tests.
- `tests/e2e/`: entry-point tests that may require an environment.
- `docs/`: durable project documentation.
- `skills/verify-project/SKILL.md`: portable project verification procedure.

## Development commands

This project targets Python 3.14 and uses `uv` for dependencies:

```shell
uv sync
uv run pytest tests/unit
uv run pytest
uv lock --check
```

Run `uv lock` after changing `pyproject.toml`. Do not edit `uv.lock` by hand.

## AWS safety

- Keep unit tests offline and mock AWS clients at their boundary.
- Never run `syndicate deploy`, `syndicate update`, `syndicate clean`, or other
  AWS-mutating commands without explicit user approval.
- Confirm the target AWS account, region, and resource scope before an approved
  deployment operation.
- Never commit credentials, tokens, private keys, or real `.env` files.

## Change workflow

Inspect the source, tests, and documentation before editing. Add a focused test
for behavior changes, run the focused test first, then run the complete suite.
Preserve the existing AWS Syndicate project layout and avoid unrelated
refactoring.
"""

PYTHON_STANDARD_README = """# {project_name}

AWS Syndicate project scaffold using the provider-neutral Python project
structure.

## Requirements

- Python 3.14
- `uv`
- AWS credentials only for commands that access AWS

## Setup

```shell
uv sync
```

Generate a Lambda and its test files with:

```shell
syndicate generate lambda --name ExampleLambda --runtime python --project-path .
```

## Quality checks

```shell
uv run pytest tests/unit
uv run pytest
uv lock --check
```

## AWS operations

Build locally before deployment:

```shell
syndicate build
```

Deployment and cleanup change AWS resources. Confirm the target account and
region before running `syndicate deploy`, `syndicate update`, or
`syndicate clean`.

## Layout

- `lambdas/` contains Lambda handlers.
- `commons/` contains shared application code.
- `tests/` contains unit, integration, and end-to-end test layers.
- `AGENTS.md` is the canonical contributor and coding-agent guidance.
- `docs/architecture.md` records project-specific architecture decisions.
"""

PYTHON_STANDARD_PYPROJECT = """[project]
name = "{distribution_name}"
version = "0.1.0"
description = "AWS Syndicate application project."
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "aws-syndicate",
]

[dependency-groups]
dev = [
    "pytest",
]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: tests that cross a package or CLI boundary",
    "e2e: tests that may require a deployed environment",
]
"""

PYTHON_STANDARD_GITIGNORE = """.syndicate
logs/
.syndicate-config-*/
__pycache__/
.pytest_cache/
.venv/
.env
.env.*
!.env.example
dist/
build/
*.egg-info/
"""

PYTHON_STANDARD_CHANGELOG = """# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Added

- Initial AWS Syndicate project scaffold.
"""

PYTHON_STANDARD_VENV = """# Python environment

This project uses Python 3.14 and `uv`. The generated project does not create
`.venv/`; create it locally with:

```shell
uv sync
```

Activation is optional when using `uv run`.
"""

PYTHON_STANDARD_ARCHITECTURE = """# Architecture

## AWS Syndicate project

Lambda handlers live under `lambdas/`, shared code lives under `commons/`, and
deployment resources are described in `deployment_resources.json`.

## Tests

- `tests/unit/` contains deterministic offline tests.
- `tests/integration/` contains package and CLI boundary tests.
- `tests/e2e/` contains checks that may require deployed resources.

## Instruction layering

Universal project rules live in `AGENTS.md`. Tool-specific adapters may point
to it but must not become a competing source of truth.
"""

PYTHON_STANDARD_SKILL = """---
name: verify-project
description: Run the tests and lockfile checks for an AWS Syndicate Python project.
---

# Verify project

Run from the project root:

1. Run `uv lock --check`.
2. Run `uv run pytest tests/unit`.
3. Run `uv run pytest`.
4. Report each command and its result.

This skill is read-only. It must not edit source files, update `uv.lock`, or
perform AWS deployments, updates, or cleanup.
"""

PYTHON_STANDARD_FILES = {
    'AGENTS.md': PYTHON_STANDARD_AGENTS,
    'README.md': PYTHON_STANDARD_README,
    'CHANGELOG.md': PYTHON_STANDARD_CHANGELOG,
    'pyproject.toml': PYTHON_STANDARD_PYPROJECT,
    '.python-version': '3.14\n',
    '.gitignore': PYTHON_STANDARD_GITIGNORE,
    'venv.md': PYTHON_STANDARD_VENV,
    'docs/architecture.md': PYTHON_STANDARD_ARCHITECTURE,
    'skills/verify-project/SKILL.md': PYTHON_STANDARD_SKILL,
    '.env.example': '# Add safe environment-variable names here. Never add secrets.\n',
    'tests/unit/test_scaffold.py': (
        'import sys\n\n\n'
        'def test_project_targets_python_314():\n'
        "    assert sys.version_info >= (3, 14)\n"
    ),
    'tests/integration/README.md': (
        '# Integration tests\n\n'
        'Add tests for package and CLI boundaries here.\n'
    ),
    'tests/e2e/README.md': (
        '# End-to-end tests\n\n'
        'Add tests that require a deployed environment here.\n'
    ),
}


def _distribution_name(project_name):
    distribution_name = re.sub(r'[^a-z0-9]+', '-', project_name.lower())
    return distribution_name.strip('-') or 'syndicate-project'


def generate_python_standard_project(
    full_project_path,
    project_name,
):
    distribution_name = _distribution_name(project_name)
    output_path = Path(full_project_path)

    for relative_path, content in PYTHON_STANDARD_FILES.items():
        rendered = content.format(
            project_name=project_name,
            distribution_name=distribution_name,
        )
        target = output_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        _write_content_to_file(file=str(target), content=rendered)

    (output_path / 'commons').mkdir(exist_ok=True)
    (output_path / 'lambdas').mkdir(exist_ok=True)
