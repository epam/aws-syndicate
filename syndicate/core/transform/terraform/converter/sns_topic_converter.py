from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class SNSTopicConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        region = resource.get('region')
        if not region:
            region = self.config.region
        topic = sns_topic(sns_topic_name=name)
        self.template.add_aws_sns_topic(meta=topic)


def sns_topic(sns_topic_name):
    resource = {
        sns_topic_name: [
            {
                "name": sns_topic_name
            }
        ]
    }
    return resource
