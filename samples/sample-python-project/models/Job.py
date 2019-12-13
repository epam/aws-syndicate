import os

from pynamodb.attributes import UnicodeAttribute
from pynamodb.models import Model


class Job(Model):
    class Meta:
        table_name = "Job"
        region = os.environ['AWS_REGION']

    job_id = UnicodeAttribute(hash_key=True, attr_name='job_id')
    status = UnicodeAttribute(attr_name='status')
