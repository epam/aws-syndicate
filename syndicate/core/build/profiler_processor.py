import os

from math import ceil
from syndicate.commons.log_helper import get_logger
from syndicate.core import ResourceProvider
from syndicate.core.build.bundle_processor import load_deploy_output
from syndicate.core.helper import exit_on_exception
from syndicate.core.constants import DATE_FORMAT_ISO_8601
from datetime import datetime, timedelta

MIN_STATISTIC_VALUE = 'Minimum'
MAX_STATISTIC_VALUE = 'Maximum'
AVG_STATISTIC_VALUE = 'Average'
SUM_STATISTIC_VALUE = "Sum"

DURATION_METRIC = "Duration"
INVOCATION_METRIC = "Invocations"
ERROR_METRIC = "Errors"
CONCURRENT_EXECUTIONS_METRIC = "ConcurrentExecutions"
SUCCESS_RATE_METRIC = f"Success rate{os.linesep}(%)"

UTC_TIMESTAMP = f'Metrics time stamp{os.linesep}(UTC)'
METRIC_NAMES = ["Invocations", "Errors", "Throttles", "Duration",
                "DestinationDeliveryFailures", "DeadLetterErrors",
                "IteratorAge", "ConcurrentExecutions"]

_LOG = get_logger('syndicate.core.build.profiler_processor')


def _get_cw_client():
    return ResourceProvider.instance.cw_alarm().client.client


@exit_on_exception
def get_lambdas_name(bundle_name, deploy_name):
    output = load_deploy_output(bundle_name, deploy_name)
    lambda_output = {key: value for key, value in output.items() if
                     value['resource_meta'].get('resource_type') == 'lambda'}

    if not lambda_output:
        _LOG.warning('No Lambdas to describe metrics, exiting')
        return

    lambda_names = [definition['resource_name']
                    for lambda_arn, definition in lambda_output.items()]

    return lambda_names


def add_success_rate_column(prettify_metrics_dict):
    invocations = []
    errors = []
    success_rate = []
    for metric_type, metric_data in prettify_metrics_dict.items():
        if metric_type.startswith(INVOCATION_METRIC):
            invocations = metric_data
        elif metric_type.startswith(ERROR_METRIC):
            errors = metric_data

    for idx, data in enumerate(invocations):
        percent = round(((data - errors[idx]) / data) * 100, 2)
        success_rate.append(percent)

    if success_rate:
        prettify_metrics_dict[SUCCESS_RATE_METRIC] = success_rate
    return prettify_metrics_dict


def handle_data_points(prettify_metrics_dict, data_points, label):
    for data in data_points:
        unit = f"{os.linesep}({data['Unit']})".replace('Milliseconds',
                                                       'Ms')
        label_unit = label + unit

        time_stamp = str(data['Timestamp']).split('+')[0]

        metric_data = None
        statistics = [AVG_STATISTIC_VALUE, MIN_STATISTIC_VALUE,
                      MAX_STATISTIC_VALUE, SUM_STATISTIC_VALUE]
        for statistic in statistics:
            if statistic in data:
                metric_data = data[statistic]
                if int(metric_data) == metric_data:
                    metric_data = int(metric_data)
                else:
                    metric_data = round(metric_data, 2)

        if label_unit not in prettify_metrics_dict:
            prettify_metrics_dict.update({label_unit: [metric_data]})
        else:
            prettify_metrics_dict[label_unit].append(metric_data)

        if time_stamp not in prettify_metrics_dict[UTC_TIMESTAMP]:
            prettify_metrics_dict[UTC_TIMESTAMP].append(time_stamp)


def process_metrics(prettify_metrics_dict, metrics):
    for metric_type in metrics:
        label = metric_type['Label']
        data_points = metric_type['Datapoints']
        data_points.sort(key=lambda date: date['Timestamp'], reverse=True)

        if UTC_TIMESTAMP not in prettify_metrics_dict and data_points:
            prettify_metrics_dict.update({UTC_TIMESTAMP: []})

        handle_data_points(prettify_metrics_dict, data_points, label)

    add_success_rate_column(prettify_metrics_dict)
    return prettify_metrics_dict


def period_calculation(time_range):
    single_call_data_points = 1440
    divider = 60

    time_range_in_sec = time_range.total_seconds()
    period = time_range_in_sec / single_call_data_points

    if period < divider:
        allowed_min_values = [1, 5, 10, 30]
        for num in allowed_min_values:
            if num >= period:
                period = num
                break
        if period not in allowed_min_values:
            period = divider
    else:
        nearest_multiple = divider * ceil(period / divider)
        period = nearest_multiple
    return int(period)


def validate_time_range(from_date, to_date):
    if not (from_date and to_date):
        from_date = datetime.utcnow() - timedelta(hours=1)
        to_date = datetime.utcnow()
    else:
        from_date = datetime.strptime(from_date, DATE_FORMAT_ISO_8601)
        from_date = datetime.utcfromtimestamp(datetime.timestamp(from_date))
        to_date = datetime.strptime(to_date, DATE_FORMAT_ISO_8601)
        to_date = datetime.utcfromtimestamp(datetime.timestamp(to_date))
    time_range = to_date - from_date
    if time_range <= timedelta(seconds=0):
        raise AssertionError(f'The parameter from_date must be more than the'
                             f' parameter to_date.')
    return from_date, to_date, time_range


def get_metric(lambda_name, metric, statistics, from_date, to_date, period):
    cw_client = _get_cw_client()

    response = cw_client.get_metric_statistics(
        Namespace='AWS/Lambda',
        Dimensions=[
            {
                'Name': 'FunctionName',
                'Value': lambda_name
            }
        ],
        MetricName=metric,
        StartTime=from_date,
        EndTime=to_date,
        Period=period,
        Statistics=statistics
    )
    return response


def save_metric_to_dict(metric_value_dict, lambda_name, response):
    if lambda_name not in metric_value_dict:
        metric_value_dict.update({lambda_name: [response]})
    else:
        metric_value_dict[lambda_name].append(response)
    return metric_value_dict


def process_duration_metric(lambda_name, metric, from_date, to_date, period,
                            metric_value_dict):
    statistics_abbreviation = {MIN_STATISTIC_VALUE: 'Min.',
                               AVG_STATISTIC_VALUE: 'Avg.',
                               MAX_STATISTIC_VALUE: 'Max.'}
    for statistic in statistics_abbreviation:
        response = get_metric(lambda_name, metric, [statistic],
                              from_date, to_date, period)
        statistic_name = statistic
        response['Label'] = statistics_abbreviation[
                                statistic_name] + ' ' + \
                            response['Label']
        metric_value_dict = save_metric_to_dict(metric_value_dict,
                                                lambda_name,
                                                response)
    return metric_value_dict


def process_invocation_metric(lambda_name, metric, from_date, to_date, period,
                              metric_value_dict):
    sum_statistic = [SUM_STATISTIC_VALUE]
    response = get_metric(lambda_name, metric, sum_statistic,
                          from_date, to_date, period)
    metric_value_dict = save_metric_to_dict(metric_value_dict,
                                            lambda_name, response)
    return metric_value_dict


def process_cncr_execution_metric(lambda_name, metric, from_date, to_date,
                                  period, metric_value_dict):
    max_statistics = [MAX_STATISTIC_VALUE]
    response = get_metric(lambda_name, metric, max_statistics,
                          from_date, to_date, period)
    response['Label'] = 'Concurrent Executions'
    metric_value_dict = save_metric_to_dict(metric_value_dict,
                                            lambda_name, response)
    return metric_value_dict


METRIC_TYPE_HANDLERS = {
    DURATION_METRIC: process_duration_metric,
    INVOCATION_METRIC: process_invocation_metric,
    CONCURRENT_EXECUTIONS_METRIC: process_cncr_execution_metric
}


def process_another_metrics_types(lambda_name, metric, from_date, to_date,
                                  period, metric_value_dict):
    max_statistics = [MAX_STATISTIC_VALUE]
    response = get_metric(lambda_name, metric, max_statistics,
                          from_date, to_date, period)
    metric_value_dict = save_metric_to_dict(metric_value_dict,
                                            lambda_name, response)
    return metric_value_dict


def get_metric_statistics(bundle_name, deploy_name, from_date, to_date):
    from_date, to_date, time_range = validate_time_range(from_date, to_date)

    period = period_calculation(time_range)

    lambda_names = get_lambdas_name(bundle_name, deploy_name)
    metric_value_dict = {}
    for lambda_name in lambda_names:
        for metric in METRIC_NAMES:
            metric_handler = METRIC_TYPE_HANDLERS.get(metric)
            if metric_handler:
                metric_handler(lambda_name, metric, from_date, to_date, period,
                               metric_value_dict)
            else:
                process_another_metrics_types(lambda_name, metric, from_date,
                                              to_date, period,
                                              metric_value_dict)
    return metric_value_dict
