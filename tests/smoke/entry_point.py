import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

cur_dir = Path(__file__).resolve().parent
parent_dir = str(cur_dir.parent)
sys.path.append(parent_dir)

from commons.step_processors import process_steps
from commons.constants import STAGES_CONFIG_PARAM, INIT_PARAMS_CONFIG_PARAM, \
    OUTPUT_FILE_CONFIG_PARAM, DEPENDS_ON_CONFIG_PARAM, \
    STAGE_PASSED_REPORT_PARAM, BUNDLE_NAME, CLEAN_COMMAND
from commons.utils import save_json, full_path, split_deploy_bucket_path
from commons.connections import delete_s3_folder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Entrypoint for tests',
    )

    parser.add_argument(
        '-c', '--config', required=False,
        default=full_path('ddis_resources_check_config.json',
                          os.path.join(str(cur_dir), 'configs')),
        type=full_path,
        help='Full path to the config file with described stage checks. '
             'Default: configs/ddis_resources_check_config.json'
    )
    parser.add_argument('-v', '--verbose', required=False, default=False,
                        action='store_true',
                        help='Enable logging verbose mode. Default: False')
    return parser


def force_clean(only_bundle=False):
    from syndicate.core.conf.processor import ConfigHolder
    from syndicate.core import CONF_PATH

    print(f'\nCleaning bundle {"and resources" if not only_bundle else ""}')
    if not only_bundle:
        command_to_execute = ['syndicate', 'clean']
        exec_result = subprocess.run(command_to_execute, check=False,
                                     capture_output=True, text=True)
        print(f'Execution return code: {exec_result.returncode}')

    config = ConfigHolder(CONF_PATH)
    deploy_bucket, path = split_deploy_bucket_path(config.deploy_target_bucket)
    delete_s3_folder(deploy_bucket, os.path.join(*path, BUNDLE_NAME))


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
    with open(config, 'rb') as file:
        raw_data = file.read()
        decoded_data = raw_data.decode('utf-8', errors='replace')
        config_file = json.loads(decoded_data)

    init_params = config_file.get(INIT_PARAMS_CONFIG_PARAM, {})
    output_file = full_path(init_params.pop(OUTPUT_FILE_CONFIG_PARAM,
                                            'result_report.json'))

    try:
        for stage, stage_info in config_file[STAGES_CONFIG_PARAM].items():
            print(f'\nProcessing stage `{stage}`')
            verification_result = process_steps(
                stage_info, verbose=verbose,
                skip_stage=not should_process_stage(stage_info), **init_params)
            result[STAGES_CONFIG_PARAM].update({stage: verification_result})

        print(f'Saving result report to {output_file}')
        output_list = [{k:v} for k, v in result[STAGES_CONFIG_PARAM].items()]
        save_json(output_file, {STAGES_CONFIG_PARAM: output_list})
    except Exception as e:
        print(e)
        raise e
    finally:
        only_bundle = False
        if CLEAN_COMMAND in result[STAGES_CONFIG_PARAM] and all(
                i['stage_passed'] for i in result[STAGES_CONFIG_PARAM][CLEAN_COMMAND]):
            print('Only bundle is True')
            only_bundle = True
        force_clean(only_bundle)


if __name__ == '__main__':
    main(**vars(build_parser().parse_args()))
