from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class CloudWatchRuleConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        rule_type = resource.get('rule_type')
        region = resource.get('region')
        if not region:
            region = self.config.region

        if rule_type == 'ec2':
            instance_ids = resource.get('instance_ids')
            instance_states = resource.get('instance_states')
        elif rule_type == 'schedule':
            expression = resource.get('expression')
        elif rule_type == 'api_call':
            operations = resource.get('operations')
            aws_service = resource.get('aws_service')

        pass
