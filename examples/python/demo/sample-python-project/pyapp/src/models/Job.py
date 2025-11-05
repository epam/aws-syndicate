"""
    Copyright 2018 EPAM Systems, Inc.

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

import os

from pynamodb.attributes import UnicodeAttribute, NumberAttribute
from pynamodb.models import Model


class Job(Model):
    class Meta:
        table_name = "Job"
        region = os.environ['AWS_REGION']

    job_id = UnicodeAttribute(hash_key=True, attr_name='job_id')
    status = UnicodeAttribute(attr_name='status')
    creation_date_sec = NumberAttribute(attr_name='creation_date', default=0)
    last_updated_data_sec = NumberAttribute(attr_name='last_updated_date',
                                            default=0)
