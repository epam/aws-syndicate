import argparse
import json
import os

from commons.step_processors import process_steps
from commons.constants import STAGES_CONFIG_PARAM
from commons.utils import save_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Entrypoint for happy path tests',
    )

    def full_path(value: str) -> str:
        if not value.endswith('.json'):
            value = value + '.json'
        if not os.path.isabs(value):  # check if full path
            value = os.path.join(os.getcwd(), value)
        return value

    parser.add_argument('-d', '--deploy_target_bucket', required=True,
                        type=str,
                        help='* S3 bucket name where bundles will be stored.')
    parser.add_argument(
        '-c', '--config', required=False, default='happy_path_config.json',
        type=full_path,
        help='Full path to the config file with described stage checks. '
             'Default: happy_path_config.json'
    )
    parser.add_argument('-v', '--verbose', required=False, default=False,
                        action='store_true',
                        help='Enable logging verbose mode. Default: False')
    parser.add_argument('-o', '--output_file', required=False, type=full_path,
                        default='result_report.json',
                        help='Output filename. Default: result_report.json')
    parser.add_argument('-s', '--suffix', required=False, type=str,
                        help='Resource suffix.')
    parser.add_argument('-p', '--prefix', required=False, type=str,
                        help='Resource prefix.')
    return parser


def main(deploy_target_bucket: str, config: str, verbose: bool,
         output_file: str, suffix: str, prefix: str):
    result = {STAGES_CONFIG_PARAM: {}}
    with open(config) as file:
        stages = json.load(file)

    for stage, steps in stages[STAGES_CONFIG_PARAM].items():
        print(f'Processing stage {stage}')
        verification_result = process_steps(
            steps, verbose=verbose, deploy_target_bucket=deploy_target_bucket,
            suffix=suffix, prefix=prefix)
        result[STAGES_CONFIG_PARAM].update({stage: verification_result})

    save_json(output_file, result)


if __name__ == '__main__':
    main(**vars(build_parser().parse_args()))
