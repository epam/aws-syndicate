import argparse
from pathlib import Path
from typing import Optional, List

from commons.task_processors import process_task_verification
from commons.constants import COMMANDS_TO_TEST
from commons.utils import save_json
from syndicate.core.handlers import build, deploy, clean, update


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Entrypoint for smokes',
    )
    parser.add_argument(
        '--stages', required=False, type=str, nargs='*',
        choices=COMMANDS_TO_TEST,
        help='Commands to be tested. Multiple entries can be specified.'
    )
    parser.add_argument(
        '--verbose', required=False, type=str, nargs='*',
        choices=COMMANDS_TO_TEST,
        help='Commands to be tested. Multiple entries can be specified.'
    )

    def markdown(value: str) -> Path:
        if not value.endswith('.md'):
            value = value + '.md'
        return Path(value)
    parser.add_argument('--filename', required=False, type=markdown,
                        help='Output file')
    return parser


def test_build() -> dict:
    build()  # pass params
    task_steps = {
        1: {'description': '',
            'handler': validation_steps['IM01']['handler'],
            'params': {'lambda_name': lambda_name,
                       'error_code': validation_steps['IM01']['error_code']
                       }
            },
        2: {'description': '',
            'handler': validation_steps['IM02']['handler'],
            'params': {'lambda_name': lambda_name,
                       'runtime': runtime,
                       'error_code': validation_steps['IM02']['error_code']
                       },
            'depends_on': [1]
            }
    }
    result = process_task_verification(task_steps=task_steps)


def test_deploy() -> dict:
    deploy()
    ...


def test_clean() -> dict:
    clean()
    ...


def test_update() -> dict:
    update()
    ...


def main(stages: Optional[List[str]], filename: Optional[Path]):
    command_test_mapping = {
        'build': test_build,
        'deploy': test_deploy,
        'clean': test_clean,
        'update': test_update
    }
    results = {}

    if stages:
        for stage in (command_test_mapping[s] for s in stages if s in command_test_mapping):
            results.update(stage())
    else:
        for stage in command_test_mapping.values():
            results.update(stage())

    save_json(filename, results)


if __name__ == '__main__':
    main(**vars(build_parser().parse_args()))
