from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class CloudWatchAlarmConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        metric_name = resource.get('metric_name')
        period = resource.get('period')
        evaluation_periods = resource.get('evaluation_periods')
        threshold = resource.get('threshold')
        comparison_operator = resource.get('comparison_operator')
        statistic = resource.get('statistic')
        ok_actions = resource.get('sns_topics')
        namespace = resource.get('namespace')

        alarm = build_cloud_watch_alarm_meta(alarm_name=name,
                                             metric_name=metric_name,
                                             period=period,
                                             evaluation_periods=evaluation_periods,
                                             threshold=threshold,
                                             comparison_operator=comparison_operator,
                                             statistic=statistic,
                                             ok_actions=ok_actions,
                                             namespace=namespace)
        self.template.add_aws_cloudwatch_metric_alarm(alarm)


def build_cloud_watch_alarm_meta(alarm_name, comparison_operator,
                                 evaluation_periods, ok_actions,
                                 metric_name, namespace, period, statistic,
                                 threshold):
    resource = {
        alarm_name: [
            {
                "alarm_name": alarm_name,
                "comparison_operator": comparison_operator,
                "evaluation_periods": evaluation_periods,
                "ok_actions": ok_actions,
                "metric_name": metric_name,
                "namespace": namespace,
                "period": period,
                "statistic": statistic,
                "threshold": threshold
            }
        ]
    }
    return resource
