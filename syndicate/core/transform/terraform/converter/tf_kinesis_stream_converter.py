"""
    Copyright 2021 EPAM Systems, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
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
