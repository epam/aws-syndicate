from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import STEP_FUNCTION_TYPE


class StepFunctionGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = STEP_FUNCTION_TYPE
    CONFIGURATION = {
        "definition": {
            "States": {
                "ExampleState": {
                    "Type": "Succeed"
                }
            },
            "Comment": "A description of your state machine",
            "StartAt": "ExampleState",
        },
        "event_sources": list,
        "dependencies": list,
        "iam_role": None,
    }
