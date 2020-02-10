import time
from datetime import datetime

from models.Job import Job


def current_timestamp():
    return int(datetime.timestamp(datetime.now()))


def lambda_handler(event, context):
    print('Incoming event: {}'.format(event))
    processed_jobs = []
    for record in event['Records']:
        # registering job
        job_id = record['messageId']
        new_job = Job(job_id=job_id, status='CREATED',
                      creation_date=current_timestamp())
        new_job.save()

        #  job processing code here
        time.sleep(2)

        # update job status
        new_job.status = 'DONE'
        new_job.last_updated_data_sec = current_timestamp()
        new_job.save()
        processed_jobs.append(job_id)
    return 'Jobs processed: {}'.format(processed_jobs)
