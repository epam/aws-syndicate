from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import CLOUD_WATCH_ALARM_TYPE
from syndicate.commons.log_helper import get_logger, get_user_logger

_LOG = get_logger(
    'syndicate.core.generators.deployment_resources.cloudwatch_alarm_generator')
USER_LOG = get_user_logger()


class CloudWatchAlarmGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = CLOUD_WATCH_ALARM_TYPE
    CONFIGURATION = {
        "metric_name": None,
        "namespace": None,
        "period": 1200,  # seconds
        "evaluation_periods": 1,
        "threshold": 1.0,
        "comparison_operator": "GreaterThanOrEqualToThreshold",
        "statistic": "SampleCount",
        "sns_topics": list,
    }

    def _generate_resource_configuration(self) -> dict:
        self._validate_period()
        return super()._generate_resource_configuration()

    def _validate_period(self):
        _LOG.info("Validating given period...")
        to_validate = self._dict.get('period')
        if not to_validate:
            _LOG.warning("The period wasn't given. Skipping validation...")
            return
        if any(to_validate == valid for valid in [10, 30]) \
                or to_validate % 60 == 0:
            _LOG.info(f"Period: '{to_validate}' is valid")
            return
        message = "Valid values for period are 10, 30, or any " \
                  "multiple of 60"
        _LOG.error(f'Period validation error: {message}')
        raise ValueError(message)
