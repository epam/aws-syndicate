from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import EVENT_BRIDGE_SCHEDULE_TYPE


class EventBridgeScheduleGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = EVENT_BRIDGE_SCHEDULE_TYPE
    CONFIGURATION = {
        'schedule_content': {
            'flexible_time_window': dict,
            'schedule_expression': str,
            'target': {
                'arn': str,
                'role_arn': str,
                'input': str,
                'dead_letter_config': dict
            }
        },
        'tags': dict,
    }

    def __init__(self, **kwargs):
        if kwargs.get('mode'):
            kwargs['flexible_time_window'] = {
                'maximum_window_in_minutes': kwargs.pop(
                    'maximum_window_in_minutes', None),
                'mode': kwargs.pop('mode')
            }

        kwargs['target'] = {
            'arn': kwargs.pop('target_arn'),
            'role_arn': kwargs.pop('role_arn')
        }
        if kwargs.get('dead_letter_arn'):
            kwargs['target']['dead_letter_config'] = {
                'arn': kwargs.pop('dead_letter_arn', None)
            }

        resource_name = kwargs.pop('resource_name', {})
        tags = kwargs.pop('tags', {})
        project_path = kwargs.pop('project_path', {})
        schedule_content = kwargs
        kwargs = {'schedule_content': schedule_content, 'tags': tags,
                  'project_path': project_path, 'resource_name': resource_name}
        super().__init__(**kwargs)
