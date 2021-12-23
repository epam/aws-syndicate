from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import CLOUD_WATCH_RULE_TYPE
import click

DEFAULT_CRON_EXPRESSION = 'rate(1 hour)'


class CloudwatchEventRuleGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = CLOUD_WATCH_RULE_TYPE
    CONFIGURATION = {
        "rule_type": None,
        "region": None
    }

    def __init__(self, **kwargs):
        rule_type = kwargs.get('rule_type')
        if rule_type == 'schedule':
            self.CONFIGURATION['expression'] = DEFAULT_CRON_EXPRESSION
        elif rule_type == 'ec2':
            self.CONFIGURATION['instance_ids'] = list
            self.CONFIGURATION['instance_states'] = list
        elif rule_type == 'api_call':
            if not kwargs.get('aws_service'):
                raise click.MissingParameter(
                    "'aws_service' option is required "
                    "if if rule_type is 'api_call'",
                    param_type='option',
                    param_hint='aws_service')
            self.CONFIGURATION['aws_service'] = None
            self.CONFIGURATION['operations'] = list
        super().__init__(**kwargs)
