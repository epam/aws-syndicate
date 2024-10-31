from datetime import datetime

DEPLOY_NAME = 'autotest'
BUNDLE_NAME = f'happy_path_autotest_{datetime.now().strftime("%y%m%d.%H%M%S")}'

STAGES_CONFIG_PARAM = 'stages'
STEPS_CONFIG_PARAM = 'steps'
DESCRIPTION_CONFIG_PARAM = 'description'
COMMAND_CONFIG_PARAM = 'command'
CHECKS_CONFIG_PARAM = 'checks'
NAME_CONFIG_PARAM = 'name'
DEPENDS_ON_CONFIG_PARAM = 'depends_on'
