from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class DynamoDbStreamConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        table_name = resource.get('table')
        stream_view_type = resource.get('stream_view_type')
        self.template.add_dynamo_db_stream(table_name=table_name,
                                           view_type=stream_view_type)
