from datetime import datetime

COMMANDS_TO_TEST = ['build', 'deploy', 'clean', 'update']

DEPLOY_NAME = 'autotest'
BUNDLE_NAME = f'happy_path_autotest_{datetime.now().strftime("%y%m%d.%H%M%S")}'
