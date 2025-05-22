from datetime import datetime

DEPLOY_NAME = 'autotest'
BUNDLE_NAME = 'happy_path_autotest'
UPDATED_BUNDLE_NAME = 'happy_path_autotest_updated_{time}'.format(
    time=datetime.now().isoformat().replace(':', '_')
)

BUILD_COMMAND = 'build'
DEPLOY_COMMAND = 'deploy'
UPDATE_COMMAND = 'update'
CLEAN_COMMAND = 'clean'

STAGES_CONFIG_PARAM = 'stages'
INIT_PARAMS_CONFIG_PARAM = 'init_parameters'
STEPS_CONFIG_PARAM = 'steps'
DESCRIPTION_CONFIG_PARAM = 'description'
COMMAND_CONFIG_PARAM = 'command'
CHECKS_CONFIG_PARAM = 'checks'
NAME_CONFIG_PARAM = 'name'
DEPENDS_ON_CONFIG_PARAM = 'depends_on'
RESOURCE_TYPE_CONFIG_PARAM = 'resource_type'
RESOURCE_NAME_CONFIG_PARAM = 'resource_name'
RESOURCE_META_CONFIG_PARAM = 'resource_meta'
INDEX_CONFIG_PARAM = 'index'
OUTPUT_FILE_CONFIG_PARAM = 'output_file'
TAGS_CONFIG_PARAM = 'tags'

DEPLOY_OUTPUT_DIR = 'outputs'

STAGE_PASSED_REPORT_PARAM = 'stage_passed'

SWAGGER_UI_RESOURCE_TYPE = 'swagger_ui'
API_GATEWAY_OAS_V3_RESOURCE_TYPE = 'api_gateway_oas_v3'
LAMBDA_LAYER_RESOURCE_TYPE = 'lambda_layer'
RDS_DB_INSTANCE_RESOURCE_TYPE = 'rds_db_instance'
