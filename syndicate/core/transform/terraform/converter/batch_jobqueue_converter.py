from syndicate.core.resources.batch_jobqueue_resource import DEFAULT_STATE
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.tf_transform_helper import \
    build_com_env_arn


class BatchJobQueueEnvConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        state = resource.get('state')
        if not state:
            state = DEFAULT_STATE
        priority = resource.get('priority')
        compute_order = resource.get('compute_environment_order', [])
        batch_queue_env = job_queue(name=name, state=state, priority=priority,
                                    compute_environment_order=compute_order)
        self.template.add_aws_batch_job_queue(meta=batch_queue_env)


def job_queue(name, state, priority, compute_environment_order):
    params = {
        'name': name,
        'state': state,
        'priority': priority
    }

    com_env_order = []
    for order_def in compute_environment_order:
        order = order_def['order']
        compute_env = order_def['compute_environment']
        com_env_order.append(build_com_env_arn(com_env_name=compute_env))

    if com_env_order:
        params['compute_environments'] = com_env_order

    resource = {
        name: params
    }
    return resource
