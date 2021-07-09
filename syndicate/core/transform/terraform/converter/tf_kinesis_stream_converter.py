from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class KinesisStreamConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        shard_count = resource.get('shard_count')

        stream = build_kinesis_stream_meta(stream_name=name,
                                           shard_count=shard_count)
        self.template.add_aws_kinesis_stream(meta=stream)


def build_kinesis_stream_meta(stream_name, shard_count):
    resource = {
        stream_name: {
            "name": stream_name,
            "shard_count": shard_count
        }
    }
    return resource
