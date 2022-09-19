from syndicate.core.generators.deployment_resources.\
    cloudwatch_event_rule_generator import CloudwatchEventRuleGenerator
from syndicate.core.constants import EVENT_BRIDGE_RULE_TYPE


class EventBridgeRuleGenerator(CloudwatchEventRuleGenerator):
    RESOURCE_TYPE = EVENT_BRIDGE_RULE_TYPE
