[![Quality gate](https://sonarcloud.io/api/project_badges/quality_gate?project=aws-syndicate)](https://sonarcloud.io/dashboard?id=aws-syndicate)
* [![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=aws-syndicate&metric=security_rating)](https://sonarcloud.io/dashboard?id=aws-syndicate) 
* [![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=aws-syndicate&metric=sqale_rating)](https://sonarcloud.io/dashboard?id=aws-syndicate) 
* [![Bugs](https://sonarcloud.io/api/project_badges/measure?project=aws-syndicate&metric=bugs)](https://sonarcloud.io/dashboard?id=aws-syndicate) 
* [![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=aws-syndicate&metric=vulnerabilities)](https://sonarcloud.io/dashboard?id=aws-syndicate) 

# AWS deployment framework for serverless applications
aws-syndicate is an Amazon Web Services deployment framework written in Python, which allows to easily deploy serverless applications using resource descriptions. The framework allows to work with applications that engage the following AWS services:

* API Gateway

* CloudWatch Events

* Cognito

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
3) Installed [Apache Maven 3.3.9](https://maven.apache.org/download.cgi "Apache Maven 3.3.9") or higher version.

**macOS**

Detailed guide how to install Python you can find [here](https://wsvincent.com/install-python3-mac/ "here").
Also [here](https://www.baeldung.com/install-maven-on-windows-linux-mac "here") you can find detailed guild how to install [Apache Maven 3.3.9](https://maven.apache.org/download.cgi "Apache Maven 3.3.9").

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
Also [here](https://www.baeldung.com/install-maven-on-windows-linux-mac "here") you can find detailed guild how to install [Apache Maven 3.3.9](https://maven.apache.org/download.cgi "Apache Maven 3.3.9").

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
3) Installed [virtualenv](https://virtualenv.pypa.io/en/latest/installation/ "virtualenv");
4) Installed [Apache Maven 3.3.9](https://maven.apache.org/download.cgi "Apache Maven 3.3.9") or higher version.

	_*Windows*: [Here](https://docs.wso2.com/display/IS323/Installing+Apache+Maven+on+Windows "Here") you can find detailed guild how to install [Apache Maven 3.3.9](https://maven.apache.org/download.cgi "Apache Maven 3.3.9")._

	_*Linux*: [Here](https://www.baeldung.com/install-maven-on-windows-linux-mac "Here") you can find detailed guild how to install [Apache Maven 3.3.9](https://maven.apache.org/download.cgi "Apache Maven 3.3.9")._

	_*macOS*: [Here](https://www.baeldung.com/install-maven-on-windows-linux-mac "Here") you can find detailed guild how to install [Apache Maven 3.3.9](https://maven.apache.org/download.cgi "Apache Maven 3.3.9")._

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

Next, create and set up a configuration file **[sdct.conf](https://github.com/epam/aws-syndicate/blob/master/examples/demo-config/sdct.conf)**:

	# absolute path to the examples/demo-project folder
	project_path=FOLDER_PATH

	resources_suffix=
	resources_prefix=sdct-
	# region name, example - eu-central-1
	region=REGION_NAME
	# bucket name to upload deployment artifacts, must be unique across all AWS accounts
	deploy_target_bucket=BUCKET_NAME
	# your account id
	account_id=ACCOUNT_ID
	access_role=

	aws_access_key_id=ACCESS_KEY_ID
	aws_secret_access_key=SECRET_ACCESS_KEY

	# build configuration
	build_projects_mapping=mvn:/demo-java;python:/demo-python

FOLDER_PATH - replace with absolute path to the folder **examples/demo-project** <br/> ACCOUNT_ID - replace with your AWS account id <br/> REGION_NAME - replace with region name where infrastructure will be deployed <br/> BUCKET_NAME - replace with an S3 bucket name which will be used as a storage for framework artifacts (bucket name must be unique across all AWS accounts) <br/> ACCESS_KEY_ID and SECRET_ACCESS_KEY - replace with AWS credentials for user with admin permissions

Then, set up an aliases file **[sdct_aliases.conf](https://github.com/epam/aws-syndicate/blob/master/examples/demo-config/sdct_aliases.conf)**:

    region=REGION_NAME
	notification_bucket=BUCKET_NAME
	account_id=ACCOUNT_ID

ACCOUNT_ID - replace with your AWS account id <br/> BUCKET_NAME - replace with an S3 bucket name which will be used in demo application (bucket name must be unique across all AWS accounts) <br/> REGION_NAME - replace with region name where infrastructure will be deployed

Then, set up an environment variable **SDCT_CONF**:

    export SDCT_CONF=FOLDER_PATH

FOLDER_PATH - absolute path to the folder where are located files **sdct.conf** and **sdct_aliases.conf**

Deployment
------------
The demo application consists of the following infrastructure:
*  2 IAM roles
* 3 IAM policies
* 1 DynamoDB table
* 1 S3 bucket
* 2 lambdas
* 1 API Gateway

Create an S3 bucket for aws-syndicate artifacts:

    $ syndicate create_deploy_target_bucket

Next, build aws-syndicate bundle with artifacts to be deployed:

    $ syndicate build_bundle --bundle_name demo-deploy

Then, deploy AWS resources:

    $ syndicate deploy --bundle_name demo-deploy --deploy_name sdct-example

We have done it!

The demo serverless application is ready to be used.

If you need to clean AWS resources:

    $ syndicate clean --bundle_name demo-deploy --deploy_name sdct-example

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
