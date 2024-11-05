import subprocess
from datetime import datetime
from typing import List, Optional
import sys
from pathlib import Path

parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)

from commons.constants import STEPS_CONFIG_PARAM, \
    COMMAND_CONFIG_PARAM, CHECKS_CONFIG_PARAM, NAME_CONFIG_PARAM, \
    DESCRIPTION_CONFIG_PARAM, DEPENDS_ON_CONFIG_PARAM, BUILD_COMMAND, \
    BUNDLE_NAME, DEPLOY_COMMAND, UPDATE_COMMAND, DEPLOY_NAME, \
    INDEX_CONFIG_PARAM, STAGE_PASSED_REPORT_PARAM
from commons.handlers import HANDLERS_MAPPING


def process_steps(steps: dict[str: List[dict]],
                  verbose: Optional[bool] = False,
                  deploy_target_bucket: Optional[str] = None,
                  suffix: Optional[str] = None, prefix: Optional[str] = None,
                  skip_stage: bool = False):
    result = []
    for step in steps[STEPS_CONFIG_PARAM]:
        verifications = {}
        step_description = step.get(DESCRIPTION_CONFIG_PARAM, None)
        validation_steps = {
            DESCRIPTION_CONFIG_PARAM: step_description,
            CHECKS_CONFIG_PARAM: [],
            STAGE_PASSED_REPORT_PARAM: True if not skip_stage else False
        }
        if skip_stage:
            print('Skipping the stage because the stages on which it '
                  'depends did not execute successfully.')
            return [validation_steps]

        validation_checks = validation_steps[CHECKS_CONFIG_PARAM]
        command_to_execute = step[COMMAND_CONFIG_PARAM]
        if verbose:
            command_to_execute.append('--verbose')
        if BUILD_COMMAND in command_to_execute:
            command_to_execute.extend(['--bundle_name', BUNDLE_NAME])
        if DEPLOY_COMMAND in command_to_execute:
            command_to_execute.extend(['--bundle_name', BUNDLE_NAME,
                                       '--deploy_name', DEPLOY_NAME,
                                       '--replace_output'])
        if UPDATE_COMMAND in command_to_execute:
            command_to_execute.extend(['--bundle_name', BUNDLE_NAME,
                                       '--deploy_name', DEPLOY_NAME,
                                       '--replace_output'])

        print(f'Run command: {command_to_execute}')
        execution_datetime = datetime.utcnow()
        exec_result = subprocess.run(command_to_execute, check=False,
                                     capture_output=True, text=True)
        for check in step[CHECKS_CONFIG_PARAM]:
            index = check[INDEX_CONFIG_PARAM]
            depends_on = check.pop(DEPENDS_ON_CONFIG_PARAM, None)
            if depends_on is not None:
                if not all(verifications[i]
                           if verifications else True for i in depends_on):
                    verifications[index] = False
                    validation_steps[STAGE_PASSED_REPORT_PARAM] = False
                    continue

            handler_name = check.pop(NAME_CONFIG_PARAM, None)
            check_description = check.pop(DESCRIPTION_CONFIG_PARAM, None)
            handler = HANDLERS_MAPPING.get(handler_name)
            if not handler:
                print(f'Invalid handler `{handler_name}`')
                continue

            print(f'Executing handler `{handler_name}`')
            check_result = handler(actual_exit_code=exec_result.returncode,
                                   deploy_target_bucket=deploy_target_bucket,
                                   suffix=suffix, prefix=prefix,
                                   update_time=execution_datetime, **check)
            validation_checks.append({
                'index': index,
                'description': check_description,
                'step_passed': check_result is True,
                'meta': check_result if type(check_result) is dict else {}
            })
            verifications.update({index: check_result is True})
            if check_result is not True:
                validation_steps[STAGE_PASSED_REPORT_PARAM] = False
        result.append(validation_steps)
    return result
