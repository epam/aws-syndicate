import argparse
import json

from commons.step_processors import process_steps
from commons.constants import STAGES_CONFIG_PARAM, INIT_PARAMS_CONFIG_PARAM, \
    OUTPUT_FILE_CONFIG_PARAM, DEPENDS_ON_CONFIG_PARAM, \
    STAGE_PASSED_REPORT_PARAM
from commons.utils import save_json, full_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Entrypoint for happy path tests',
    )

    parser.add_argument(
        '-c', '--config', required=False, default='happy_path_config.json',
        type=full_path,
        help='Full path to the config file with described stage checks. '
             'Default: happy_path_config.json'
    )
    parser.add_argument('-v', '--verbose', required=False, default=False,
                        action='store_true',
                        help='Enable logging verbose mode. Default: False')
    return parser


def main(verbose: bool, config: str):
    def should_process_stage(stage_info):
        depends_on = stage_info.get(DEPENDS_ON_CONFIG_PARAM)
        if not depends_on:
            return True

        for k, v in result.get(STAGES_CONFIG_PARAM, {}).items():
            if k in depends_on and any(
                    i.get(STAGE_PASSED_REPORT_PARAM) is False for i in v):
                return False
        return True

    result = {STAGES_CONFIG_PARAM: {}}
    with open(config) as file:
        config_file = json.load(file)

    init_params = config_file.get(INIT_PARAMS_CONFIG_PARAM, {})
    output_file = init_params.pop(full_path(OUTPUT_FILE_CONFIG_PARAM),
                                  full_path('result_report.json'))

    for stage, stage_info in config_file[STAGES_CONFIG_PARAM].items():
        print(f'Processing stage `{stage}`')
        verification_result = process_steps(
            stage_info, verbose=verbose,
            skip_stage=not should_process_stage(stage_info), **init_params)
        result[STAGES_CONFIG_PARAM].update({stage: verification_result})

    save_json(output_file, result)


if __name__ == '__main__':
    main(**vars(build_parser().parse_args()))
