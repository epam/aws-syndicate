import argparse
from pathlib import Path
from typing import Optional, List

from commons.task_processors import process_task_verification
from commons.constants import COMMANDS_TO_TEST, DEPLOY_NAME, BUNDLE_NAME
from commons.utils import save_json

from tests.smoke.commons.step_processors import get_s3_file, run_build, run_deploy, \
    run_clean, run_update


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Entrypoint for happy path tests',
    )
    parser.add_argument(
        '-s', '--stages', required=False, type=str, nargs='*',
        choices=COMMANDS_TO_TEST,
        help='Commands to be tested. Multiple entries can be specified.'
    )
    parser.add_argument('-v', '--verbose', required=False, default=False,
                        action='store_true',
                        help='Enable logging verbose mode.')

    def ext_json(value: str) -> Path:
        if not value.endswith('.json'):
            value = value + '.json'
        return Path(value)

    parser.add_argument('--filename', required=False, type=ext_json,
                        help='Output filename.')
    return parser


def test_build(verbose: bool) -> dict:
    task_steps = {
        1: {
            'description': 'Exit code 0',
            'handler': run_build,
            'params': {
                'verbose': verbose,
                'bundle_name': BUNDLE_NAME
            }
        },
        2: {'description': 'build_meta.json is present in deployment bucket',
            'handler': get_s3_file,
            'params': {'bucket_name': '',
                       'file_key': 'build_meta.json '},
            'depends_on': [1]
            }
    }
    result = process_task_verification(task_steps=task_steps)


def test_deploy(verbose: bool) -> dict:
    task_steps = {
        1: {
            'description': 'Exit code 0',
            'handler': run_deploy,
            'params': {
                'verbose': verbose,
                'bundle_name': BUNDLE_NAME,
                'deploy_name': DEPLOY_NAME
            }
        },
    }
    ...


def test_clean(verbose: bool) -> dict:
    task_steps = {
        1: {
            'description': 'Exit code 0',
            'handler': run_clean,
            'params': {
                'verbose': verbose,
                'bundle_name': BUNDLE_NAME,
                'deploy_name': DEPLOY_NAME
            }
        },
    }
    ...


def test_update(verbose: bool) -> dict:
    task_steps = {
        1: {
            'description': 'Exit code 0',
            'handler': run_update,
            'params': {
                'verbose': verbose,
                'bundle_name': BUNDLE_NAME,
                'deploy_name': DEPLOY_NAME
            }
        },
    }
    ...


def main(stages: Optional[List[str]], verbose: bool, filename: Optional[Path]):
    command_test_mapping = {
        'build': test_build,
        'deploy': test_deploy,
        'clean': test_clean,
        'update': test_update
    }
    results = {}

    if stages:
        for stage in (command_test_mapping[s] for s in stages if
                      s in command_test_mapping):
            results.update(stage(verbose))
    else:
        for stage in command_test_mapping.values():
            results.update(stage(verbose))

    save_json(filename, results)


if __name__ == '__main__':
    main(**vars(build_parser().parse_args()))
