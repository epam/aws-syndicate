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
from troposphere import kinesis

from syndicate.connection.kinesis_connection import validate_shard_count
from .cf_resource_converter import CfResourceConverter
from ..cf_transform_utils import kinesis_stream_logic_name


class CfKinesisStreamConverter(CfResourceConverter):

    def convert(self, name, meta):
        stream = kinesis.Stream(kinesis_stream_logic_name(name))
        stream.Name = name
        shard_count = meta['shard_count']
        validate_shard_count(shard_count)
        stream.ShardCount = shard_count
        self.template.add_resource(stream)
