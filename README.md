[![Quality gate](https://sonarcloud.io/api/project_badges/quality_gate?project=aws-syndicate)](https://sonarcloud.io/dashboard?id=aws-syndicate)
* [![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=aws-syndicate&metric=security_rating)](https://sonarcloud.io/dashboard?id=aws-syndicate) 
* [![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=aws-syndicate&metric=sqale_rating)](https://sonarcloud.io/dashboard?id=aws-syndicate) 
* [![Bugs](https://sonarcloud.io/api/project_badges/measure?project=aws-syndicate&metric=bugs)](https://sonarcloud.io/dashboard?id=aws-syndicate) 
* [![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=aws-syndicate&metric=vulnerabilities)](https://sonarcloud.io/dashboard?id=aws-syndicate) 

# AWS deployment framework for serverless applications
aws-syndicate is an Amazon Web Services deployment framework written in Python, which allows to easily deploy serverless applications using resource descriptions. The framework allows to work with applications that engage the following AWS services:

* API Gateway

* AWS Batch

* CloudWatch Events

* Cognito

* DocumentDB

* DynamoDB

* Elastic Beanstalk

* Elastic Compute Cloud

* Identity and Access Management

* Kinesis

* Lambda

* Lambda Layers

* Simple Notification Service

* Simple Queue Service

* Simple Storage Service

* Step Functions

## Changelog

[See CHANGELOG here](https://github.com/epam/aws-syndicate/blob/master/CHANGELOG.md "aws-syndicate changelog").

## Installing

[Install aws-syndicate from PyPI](https://pypi.org/project/aws-syndicate/ "aws-syndicate on PyPI")

#### Installation from sources
**Prerequisites**

1) Installed [Python 3.7](https://www.python.org/downloads/ "Python 3.7") or higher version;
2) Installed package manager [PIP 9.0](https://pypi.org/project/pip/ "PIP 9.0") or higher version;
3) Installed [Apache Maven 3.3.9](https://maven.apache.org/download.cgi "Apache Maven 3.3.9") or higher version (for Java projects).

**macOS**

Detailed guide how to install Python you can find [here](https://wsvincent.com/install-python3-mac/ "here").
Also [here](https://www.baeldung.com/install-maven-on-windows-linux-mac "here") you can find detailed guild how to install the [latest Apache Maven](https://maven.apache.org/download.cgi "latest Apache Maven").

1) Create virtual environment:
  `python3 -m venv syndicate_venv`

2) Activate your virtual environment:
  `source syndicate_venv/bin/activate`

3) Install Syndicate framework with pip from GitHub:
  `pip3 install git+https://github.com/epam/aws-syndicate.git@master`

4) Set up a Syndicate Java [plugin](https://github.com/epam/aws-syndicate/tree/master/plugin "plugin"):
	`mvn install /aws-syndicate/plugin/`

5) Go to the Common configuration.

**Linux**

Detailed guide how to install Python you can find [here](https://docs.python-guide.org/starting/install3/linux/ "here").
Also [here](https://www.baeldung.com/install-maven-on-windows-linux-mac "here") you can find detailed guild how to install the [latest Apache Maven](https://maven.apache.org/download.cgi "latest Apache Maven").

1) Create virtual environment:
  `python3 -m venv syndicate_venv`

2) Activate your virtual environment:
  `source syndicate_venv/bin/activate`

3) Install Syndicate framework with pip from GitHub:
  `pip3 install git+https://github.com/epam/aws-syndicate.git@master`

4) Set up a Syndicate Java [plugin](https://github.com/epam/aws-syndicate/tree/master/plugin "plugin"):
	`mvn install /aws-syndicate/plugin/`

5) Go to the Common configuration.

**Common prerequisites**

1) Installed [Python 3.7](https://www.python.org/downloads/ "Python 3.7") or higher version;

	_*Windows*: Detailed guide how to install Python you can find [here](https://www.ics.uci.edu/~pattis/common/handouts/pythoneclipsejava/python.html "here")._

	_*Linux*: Detailed guide how to install Python you can find [here](https://docs.python-guide.org/starting/install3/linux/ "here")._

	_*macOS*: Detailed guide how to install Python you can find [here](https://wsvincent.com/install-python3-mac/ "here"). If you use Ubuntu 16.04 or earlier [here](https://www.pytorials.com/install-python36-on-ubuntu/ "here") you can find installation guide._

2) Installed package manager [PIP 9.0](https://pypi.org/project/pip/ "PIP 9.0") or higher version;
3) Installed [virtualenv](https://virtualenv.pypa.io/en/latest/installation.html "virtualenv");
4) Installed [Apache Maven](https://maven.apache.org/download.cgi "Apache Maven").

	_*Windows*: [Here](https://docs.wso2.com/display/IS323/Installing+Apache+Maven+on+Windows "Here") you can find detailed guild how to install the [latest Apache Maven](https://maven.apache.org/download.cgi "latest Apache Maven")._

	_*Linux*: [Here](https://www.baeldung.com/install-maven-on-windows-linux-mac "Here") you can find detailed guild how to install the [latest Apache Maven](https://maven.apache.org/download.cgi "latest Apache Maven")._

	_*macOS*: [Here](https://www.baeldung.com/install-maven-on-windows-linux-mac "Here") you can find detailed guild how to install the [latest Apache Maven](https://maven.apache.org/download.cgi "latest Apache Maven")._

**Installation guide**

1) Create virtual environment:

    `virtualenv -p python3 syndicate_venv`

2) Activate your virtual environment:

    Linux/macOS: 
    `source syndicate_venv/bin/activate`
    
    Windows: 
    `\syndicate_venv\Scripts\activate.bat`

3) Install Syndicate framework with pip from GitHub:

    `pip3 install git+https://github.com/epam/aws-syndicate.git@master`

## Common configuration

It's time to configure aws-syndicate.

**Generate Syndicate project draft**

Execute `syndicate generate project` command to generates project with all the necessary components and in a right
folders/files hierarchy to start developing in a min.
Command example:

    syndicate generate project
    --name $project_name
    --config_path $path_to_project

All the provided information is validated.
After the project folder will be generated the command will return the following message:

    Project name: $project_name
    Project path: $path_to_project

The following files will be created in this folder: .gitignore, .syndicate, CHANGELOG.md, deployment_resources.json, README.md.

For more details please execute `syndicate generate project --help`

**Generate Syndicate configuration files**

Execute `syndicate generate config` command to create Syndicate configuration files.
Command example: 

    syndicate generate config
    --name $configuration_name
    --region $region_name 
    --bundle_bucket_name $s3_bucket_name
    --access_key $access_key 
    --secret_key $secret_key
    --session_token $aws_session_token
    --project_path $relative_path_to_project
    --prefix $prefix 
    --suffix $suffix 
    --config_path $path_to_store_config
    --use_temp_creds $use_temp_creds
    --serial_number $serial_number
    
All the provided information is validated.

*Note:* you may not specify `--access_key` and `--secret_key` params. It this case Syndicate
will try to find your credentials by the path `~/.aws`.

*Note:* You can force Syndicate to generate temporary credentials and use them
 for deployment. For such cases, set `use_temp_creds` parameter to `True` and
 specify serial number if IAM user which will be used for deployment has a 
 policy that requires MFA authentication. Syndicate will prompt you to enter
 MFA code to generate new credentials, save and use them until expiration.

After the configuration files will be generated the command will return the following message:

    Syndicate initialization has been completed. Set SDCT_CONF:
    Unix: export SDCT_CONF=$path_to_store_config
    Windows: setx SDCT_CONF $path_to_store_config
    
Just copy one of the last two lines, depending on your OS, and execute the command.
The commands sets the environment variable SDCT_CONF required by aws-syndicate 
to operate.

> Pay attention that the default syndicate_aliases.yaml file has been generated. 
> Your application may require additional aliases to be deployed - please add them to the file.

For more details please execute `syndicate generate config --help`

**Generate draft of lambda functions**

Execute `syndicate generate lambda` command to generate required environment for lambda function except business logic.
Command example:

    syndicate generate lambda
    --name $lambda_name_1
    --name $lambda_name_2
    --runtime python|java|nodejs
    --project_path $project_path

All the provided information is validated.
Different environments will be created for different runtimes:
* for Python

```
    .
    ├── $project_path
    │   └── src
    │       ├── commons
    │       │   ├── __init__.py
    │       │   ├── abstract_lambda.py
    │       │   ├── exception.py
    │       │   └── log_helper.py
    │       └── lambdas
    │           ├── $lambda_name_1
    │           │   ├── __init__.py
    │           │   ├── deployment_resources.json
    │           │   ├── handler.py
    │           │   ├── lambda_config.json
    │           │   ├── local_requirements.txt
    │           │   └── requirements.txt
    │           ├── $lambda_name_2
    │           │   ├── __init__.py
    │           │   ├── deployment_resources.json
    │           │   ├── handler.py
    │           │   ├── lambda_config.json
    │           │   ├── local_requirements.txt
    │           │   └── requirements.txt
    │           ├── __init__.py
    │           └── ...
    └── ...
```

* for Java

```
    .
    ├── $project_path
    │   └── jsrc
    │       └── main
    │           └── java
    │               └── com
    │                   └── $projectpath
    │                       ├── $lambda_name_1.java
    │                       └── $lambda_name_2.java
    └── ...
```

* for NodeJS

```
    .
    ├── $project_path
    │   └── app
    │       └── lambdas
    │           ├── $lambda_name_1
    │           │   ├── deployment_resources.json
    │           │   ├── lambda_config.json
    │           │   ├── index.js
    │           │   ├── package.json
    │           │   └── package-lock.json
    │           └── $lambda_name_2
    │               ├── deployment_resources.json
    │               ├── lambda_config.json
    │               ├── index.js
    │               ├── package.json
    │               └── package-lock.json
    └── ...
```
For more details please execute `syndicate generate lambda --help`

Deployment
------------
If you are just getting familiar with the functionality, you can use one of the pre-prepared examples that contain a
minimum set of AWS resources and lambdas.

The aws-syndicate/examples folder contains structure examples for different runtimes.
Go to any example you like best and set the environment variable `SDCT_CONF=$path_to_the_selected_example`.

Add your account details to `sdct.conf`/`syndicate.yml` file - account id, secret access key, access key and bucket name for deployment.
To `sdct_aliases.conf`/`syndicate_aliases.yml` add your account id, region name (eu-central-1, us-west-1, etc.) and other
values in the file that start with a `$` sign.

Create an S3 bucket for aws-syndicate artifacts:

    $ syndicate create_deploy_target_bucket

Next, build aws-syndicate bundle with artifacts to be deployed:

    $ syndicate build --bundle_name demo-deploy

Then, deploy AWS resources:

    $ syndicate deploy --bundle_name demo-deploy --deploy_name sdct-example

We have done it! The demo serverless application is ready to be used.

If you need to update AWS resources from the latest built bundle:

    $ syndicate update

If you need to clean AWS resources:

    $ syndicate clean

Documentation
------------
You can find a detailed documentation [here](https://github.com/epam/aws-syndicate/blob/master/docs/01_sdct_quick_start.pdf)

Getting Help
------------

We use GitHub issues for tracking bugs and feature requests. You can find our public backlog [here](https://github.com/epam/aws-syndicate/projects/1). If it turns out that you may have found a bug, please [open an issue](https://github.com/epam/aws-syndicate/issues/new/choose) with some of existing templates.

Default label for bugs, improvements and feature requests is `To-Think-About`, it defines that ticket requires additional information about what should be done in scope of this issue. 
`To-Do` label should be added only for tickets with clear and reviwed issue scope.

But before creating new issues - check existing, it may cover you problem or question. For increasing issue priority - just add "+1" comment. 

Would like to contribute?
-------------------------

Please, check [contributor guide](https://github.com/epam/aws-syndicate/blob/master/CONTRIBUTING.md) before starting. 
# [![SonarCloud](https://sonarcloud.io/images/project_badges/sonarcloud-white.svg)](https://sonarcloud.io/dashboard?id=aws-syndicate)
