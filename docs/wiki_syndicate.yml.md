## The structure of the syndicate.yml file

```yaml
acces_role: role_name                                                           #Optional. The role's name. (Don't specify with the `use_temp_creds` value)
account_id: account_id                                                          #Required. The ID of the AWS account
aws_access_key_id: deployment_access_key                                        #Optional. AWS access key id that is used to deploy the application.
aws_secret_access_key: deployment_secret_key                                    #Optional. AWS secret key that is used to deploy the application.
deploy_target_bucket: name of the artifacts bucket name                         #Required. Name of the bucket that is used for uploading artifacts.
project_path: /path/to/custodian-service/src                                    #Required. Path to project folder
region: deployment_region                                                       #Required. The region that is used to deploy the application by pattern: {prefix}resource_name{suffix}. Must be less than or equal to 5.
resources_preffix: prefix- (-stg)                                               #Optional. Prefix that is added to project names while deployment by pattern: {prefix}resource_name{suffix}. Must be less than or equal to 5.
resources_suffix: -suffix (-stg)                                                #Optional. Suffix that is added to project names while deployment by pattern: {prefix}resource_name{suffix}. Must be less than or equal to 5.
serial_number: arn/number_mfa                                                   #Optional. The identification number of the MFA device that is associated with the IAM user which will be used for deployment
tags:                                                                           #Optional. The tag name of the resources
    key: value
use_temp_creds: bool (true/false)                                               #Optional. Indicates Syndicate to generate and use temporary AWS credentials.
temp_aws_session_token: temp_deployment_session_token                           #Generated automatically if 'use_temp_creds' is 'true' or 'access_role' is set. AWS session token that is used to deploy the application.
temp_aws_access_key_id: temp_deployment_access_key                              #Generated automatically if 'use_temp_creds' is 'true' or 'access_role' is set. AWS access key id that is used to deploy the application.
temp_aws_secret_access_key: temp_deployment_secret_key                          #Generated automatically if 'use_temp_creds' is 'true' or 'access_role' is set. AWS secret key that is used to deploy the application.
expiration: temp_creds_expiration_iso_date                                      #Generated automatically if 'use_temp_creds' is 'true' or 'access_role' is set. ISO datetime string - the moment when the temp creds will expire.
iam_permissions_boundary: arn:aws:iam::<account_id>:policy/<role_boundary>      #Optional. Defines the boundary limit for IAM permissions using a specific policy in your AWS account.
```
