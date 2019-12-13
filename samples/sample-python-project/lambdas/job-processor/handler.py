from models.Job import Job


def lambda_handler(event, context):
    print('Incoming event: {}'.format(event))
    processed_jobs = []
    for record in event['Records']:
        # registering job
        job_id = record['messageId']
        new_job = Job(job_id=job_id, status='CREATED')
        new_job.save()

        #  job processing code here

        # update job status
        new_job.status = 'DONE'
        new_job.save()
        processed_jobs.append(job_id)
    return 'Jobs processed: {}'.format(processed_jobs)
