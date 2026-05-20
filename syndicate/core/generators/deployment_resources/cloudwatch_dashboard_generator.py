from syndicate.core.constants import CLOUD_WATCH_DASHBOARD_TYPE
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator


class CloudWatchDashboardGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = CLOUD_WATCH_DASHBOARD_TYPE
    CONFIGURATION = {
        'dashboard_body': dict,
        'tags': dict
    }

    def _resolve_configuration(self, defaults_dict=None) -> dict:
        result = super()._resolve_configuration()
        if not result['dashboard_body']:
            default_body = {
                "widgets": [
                    {
                        "type": "text",
                        "x": 0,
                        "y": 0,
                        "width": 24,
                        "height": 2,
                        "properties": {
                            "markdown":
                                "# Dashboard\nWelcome to the example "
                                "dashboard deployed using aws-syndicate."
                        }
                    }
                ]
            }
            result['dashboard_body'].update(default_body)
        return result
