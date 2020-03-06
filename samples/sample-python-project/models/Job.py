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
