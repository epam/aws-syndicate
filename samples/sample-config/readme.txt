To use syndicate the sdct.conf file should contain some parameters.
We prepared template of sdct.conf for you, so just update some values in it
and try syndicate.

Replace with following placeholders to get correct sdct.conf:
$YOUR_PATH in 'project_path' property with actual path of the project;
$YOUR_BUCKET_NAME in 'deploy_target_bucket' with name of the bucket where you want syndicate to store projects artifacts;
$ACCOUNT_ID in 'account_id' property to AWS account id where syndicate will deploys this demo;
    Update $ACCOUNT_ID in sdct_aliases.conf too;
$ACCESS_KEY in 'aws_access_key_id' with your Access key ID acceptable of account specified in account_id;
$SECRET_KEY in 'aws_secret_access_key' with your Secret access key acceptable of account specified in account_id;

Now export path to config files: export SDCT_CONF=$path_to_project/aws-syndicate/samples/sample-config

That's all.
Try 'syndicate build_bundle --bundle_name demo' and then 'syndicate deploy --bundle_name demo --deploy_name demo'.
To clean execute 'syndicate clean --bundle_name demo --deploy_name demo'.