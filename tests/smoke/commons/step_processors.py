import subprocess
from typing import List, Optional

from tests.smoke.commons.constants import STEPS_CONFIG_PARAM, \
    COMMAND_CONFIG_PARAM, CHECKS_CONFIG_PARAM, NAME_CONFIG_PARAM, \
    DESCRIPTION_CONFIG_PARAM, DEPENDS_ON_CONFIG_PARAM
from tests.smoke.commons.handlers import HANDLERS_MAPPING


def process_steps(steps: List[dict], verbose: Optional[bool] = False,
                  deploy_target_bucket: Optional[str] = None,
                  suffix: Optional[str] = None, prefix: Optional[str] = None):
    result = []
    for step in steps[STEPS_CONFIG_PARAM]:
        verifications = []
        step_description = step.get(DESCRIPTION_CONFIG_PARAM, None)
        validation_steps = {DESCRIPTION_CONFIG_PARAM: step_description,
                            CHECKS_CONFIG_PARAM: []}
        validation_checks = validation_steps[CHECKS_CONFIG_PARAM]

        # exec_result = 0
        command_to_execute = step[COMMAND_CONFIG_PARAM] + ['--verbose'] if \
            verbose else ['']
        exec_result = subprocess.run(command_to_execute,
                                     capture_output=True, text=True)
        for check in step[CHECKS_CONFIG_PARAM]:
            index = step[CHECKS_CONFIG_PARAM].index(check)
            depends_on = check.pop(DEPENDS_ON_CONFIG_PARAM, None)
            if depends_on is not None:
                if not all(verifications[i]
                           if verifications else True for i in depends_on):
                    verifications[index] = False
                    continue

            handler_name = check.pop(NAME_CONFIG_PARAM, None)
            check_description = check.pop(DESCRIPTION_CONFIG_PARAM, None)
            handler = HANDLERS_MAPPING.get(handler_name)
            if not handler:
                print(f'Invalid handler `{handler_name}`')
                continue

            # check_result = handler(actual_exit_code=exec_result,
            check_result = handler(actual_exit_code=exec_result.returncode,
                                   deploy_target_bucket=deploy_target_bucket,
                                   suffix=suffix, prefix=prefix, **check)
            validation_checks.append({
                'index': index,
                'description': check_description,
                'step_passed': check_result is True,
                'meta': check_result if type(check_result) == dict else {}
            })
        result.append(validation_steps)
    return result
