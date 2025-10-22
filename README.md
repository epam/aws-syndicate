[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](http://www.apache.org/licenses/LICENSE-2.0.txt)

[![PyPI - Version](https://img.shields.io/pypi/v/aws-syndicate.svg)](https://pypi.org/project/aws-syndicate)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/aws-syndicate.svg)](https://pypi.org/project/aws-syndicate)

[![Maven Central](https://maven-badges.herokuapp.com/maven-central/net.sf.aws-syndicate/deployment-configuration-processor/badge.svg)](https://maven-badges.herokuapp.com/maven-central/net.sf.aws-syndicate/deployment-configuration-processor)

# Syndicate

aws-syndicate is an Amazon Web Services deployment framework written in Python,
which allows to easily deploy serverless applications using resource
descriptions.

## Changelog

[See CHANGELOG here](https://github.com/epam/aws-syndicate/blob/master/CHANGELOG.md "aws-syndicate changelog")

## 1. Installation

### 1.1 Installation from PyPI

[Install aws-syndicate from PyPI](https://pypi.org/project/aws-syndicate/ "aws-syndicate on PyPI")

### 1.2 Installation from source code

#### 1.2.1 Prerequisites

1) [Python 3.10](https://www.python.org/downloads/ "Python 3.10") version;
2) Package manager [PIP 22.0](https://pypi.org/project/pip/ "PIP 22.0")
   or higher version;
3) [Apache Maven 3.3.9](https://maven.apache.org/download.cgi "Apache Maven 3.3.9")
or higher version (for Java projects).
4) [SDK 8.0.402](https://dotnet.microsoft.com/en-us/download/dotnet/8.0 "SDK 8.0.402")
or higher version (for .NET projects).

#### 1.2.2 Installation on macOS

Detailed guide how to install Python you can find
[here](https://docs.python-guide.org/starting/install3/osx/ "here").
Also [here](https://www.baeldung.com/install-maven-on-windows-linux-mac "here") 
you can find detailed guild how to install
the [latest Apache Maven](https://maven.apache.org/download.cgi "latest Apache Maven").  
.NET installation guide can be found [here](https://learn.microsoft.com/en-us/dotnet/core/install/macos ".NET installation guide"), it is needed if you plan to work with runtime `.NET`.


1. Pull the project
```shell
git clone https://github.com/epam/aws-syndicate.git
```
2. Create virtual environment:
```shell
python3 -m venv syndicate_venv
```
3. Activate your virtual environment:
```shell
source syndicate_venv/bin/activate
```
4. Install Syndicate framework with pip from GitHub:
```shell
pip3 install aws-syndicate/.
```
5. Set up a Syndicate Java [plugin](https://github.com/epam/aws-syndicate/tree/master/plugin "plugin"):
```shell
mvn install -f aws-syndicate/plugin/
```
6. Go to the `2. Usage guide`

#### 1.2.2 Installation on Linux

Detailed guide how to install Python you can
find [here](https://docs.python-guide.org/starting/install3/linux/ "here").
Also [here](https://www.baeldung.com/install-maven-on-windows-linux-mac "here")
you can find detailed guild how to install
the [latest Apache Maven](https://maven.apache.org/download.cgi "latest Apache Maven").  
.NET installation guide can be found [here](https://learn.microsoft.com/en-us/dotnet/core/install/linux ".NET installation guide"), it is needed if you plan to work with runtime `.NET`.

1. Pull the project
```shell
git clone https://github.com/epam/aws-syndicate.git
```
2. Create virtual environment:
```shell
python3 -m venv syndicate_venv
```
3. Activate your virtual environment:
```shell
source syndicate_venv/bin/activate
```
4. Install Syndicate framework with pip from GitHub:
```shell
pip3 install aws-syndicate/.
```
5. Set up a Syndicate Java [plugin](https://github.com/epam/aws-syndicate/tree/master/plugin "plugin"):
```shell
mvn install -f aws-syndicate/plugin/
```
6. Go to the `2. Usage guide`

#### 1.2.3 Installation on Windows

Detailed guide how to install Python you can
find [here](https://docs.python-guide.org/starting/install3/win/ "here").
Also [here](https://www.baeldung.com/install-maven-on-windows-linux-mac "here")
you can find detailed guild how to install
the [latest Apache Maven](https://maven.apache.org/download.cgi "latest Apache Maven").
.NET installation guide can be found [here](https://learn.microsoft.com/en-us/dotnet/core/install/windows ".NET installation guide"), it is needed if you plan to work with runtime `.NET`.

1. Pull the project
```shell
git clone https://github.com/epam/aws-syndicate.git
```
2. Create virtual environment:
```shell
python3 -m venv syndicate_venv
```
3. Activate your virtual environment:
```shell
syndicate_venv\Scripts\activate.bat
```
4. Install Syndicate framework with pip from GitHub:
```shell
pip3 install aws-syndicate/.
```
5. Set up a Syndicate Java [plugin](https://github.com/epam/aws-syndicate/tree/master/plugin "plugin"):
```shell
mvn install -f aws-syndicate/plugin/
```
6. Go to the `2. Usage guide`

## 2. Usage guide

### 2.1 Creating Project files

Execute `syndicate generate project` command to generate the project with all the
necessary components and in a right folders/files hierarchy to start developing
in a min. Command example:
```shell
syndicate generate project 
    --name $project_name
    --config_path $path_to_project
```

All the provided information is validated. After the project folder will be
generated the command will return the following message:
```shell
    Project name: $project_name
    Project path: $path_to_project
```

The following files will be created in this folder: .gitignore, .syndicate,
CHANGELOG.md, deployment_resources.json, README.md.

Command sample:
```shell
syndicate generate project --name DemoSyndicateJava && cd DemoSyndicateJava
```

For more details please execute `syndicate generate project --help`

### 2.2 Creating configuration files for environment

Execute the `syndicate generate config` command to create Syndicate configuration
files. Command example:

```shell
syndicate generate config
    --name                      $configuration_name   [required]
    --region                    $region_name          [required]
    --bundle_bucket_name        $s3_bucket_name       [required]
    --access_key                $access_key  
    --secret_key                $secret_key   
    --config_path               $path_to_store_config
    --project_path              $relative_path_to_project
    --prefix                    $prefix
    --suffix                    $suffix
    --extended_prefix           $extended_prefix_mode
    --use_temp_creds            $use_temp_creds #Specify,if use mfa or access_role
    --access_role               $role_name
    --serial_number             $serial_number
    --tags                      $KEY:VALUE
    --iam_permissions_boundary  $ARN  
```

All the provided information is validated.

*Note:* you may not specify `--access_key` and `--secret_key` params. In this
case Syndicate will try to find your credentials by the path `~/.aws`.

*Note:* You can force Syndicate to generate temporary credentials and use them
for deployment. For such cases, set `use_temp_creds` parameter to `True` and
specify serial number if IAM user which will be used for deployment has a policy
that requires MFA authentication. Syndicate will prompt you to enter MFA code to
generate new credentials, save and use them until expiration.

After the configuration files will be generated the command will return the
following message:
```shell
 Syndicate initialization has been completed. 
 Set SDCT_CONF:
 Unix: export SDCT_CONF=$path_to_store_config
 Windows: setx SDCT_CONF $path_to_store_config
```

Just copy one of the last two lines, depending on your OS, and execute the
command. The commands set the environment variable SDCT_CONF required by
aws-syndicate to operate.

> Pay attention that the default syndicate_aliases.yaml file has been generated.
> Your application may require additional aliases to be deployed - please add them to the file.

Command sample:
```shell
SYNDICATE_AWS_ACCESS_KEY=# enter your aws_access_key_id here
SYNDICATE_AWS_SECRET_KEY=# enter your aws_secret_access_key here
syndicate generate config --name dev --region eu-central-1 --bundle_bucket_name syndicate-artifacts-eu-central-1 --access_key $SYNDICATE_AWS_ACCESS_KEY --secret_key $SYNDICATE_AWS_SECRET_KEY --config_path $(pwd) --prefix syn- --suffix -dev --tags ENV:DEV
```

For more details please execute `syndicate generate config --help`

### 2.3 Creating lambda files

Execute `syndicate generate lambda` command to generate required environment for
lambda function except business logic. Command example:
```shell
syndicate generate lambda
    --name $lambda_name_1
    --runtime python|java|nodejs|dotnet
    --project_path $project_path
```

All the provided information is validated. Different environments will be
created for different runtimes:

* for Python

```
    .
    ├── $project_path
    │   └── pyapp
    │       ├─── src
    │       │   ├── commons
    │       │   │   ├── __init__.py
    │       │   │   ├── abstract_lambda.py
    │       │   │   ├── exceptions.py
    │       │   │   └── log_helper.py
    │       │   └── lambdas
    │       │       ├── $lambda_name_1
    │       │       │   ├── __init__.py
    │       │       │   ├── deployment_resources.json
    │       │       │   ├── handler.py
    │       │       │   ├── lambda_config.json
    │       │       │   ├── local_requirements.txt
    │       │       │   └── requirements.txt
    │       │       ├── $lambda_name_2
    │       │       │   ├── __init__.py
    │       │       │   ├── deployment_resources.json
    │       │       │   ├── handler.py
    │       │       │   ├── lambda_config.json
    │       │       │   ├── local_requirements.txt
    │       │       │   └── requirements.txt
    │       │       ├── __init__.py
    │       │       └── ...
    │       └── tests
    │           ├── test_$lambda_name_1
    │           │   └── test_success.py
    │           ├── test_$lambda_name_2
    │           │   └── test_success.py
    │           ├── __init__.py
    │           └── ...
    └── ...
```

* for Java

```
    .
    ├── $project_path
    │   └── japp
    │       └── src
    │           ├── main
    │           │   └── java
    │           │       └── com
    │           │           └── $project_name
    │           │               └── $lambda_name_1.java
    │           │               └── $lambda_name_2.java
    │           │               └── ...
    │           └── pom.xml
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

* for .NET

```
   .
    ├── $project_path
    │   └── dnapp
    │       └── lambdas
    │           └── $lambda_name
    │               ├── deployment_resources.json
    │               ├── lambda_config.json
    │               ├── Function.cs
    │               └── Function.csproj
    └── ...
```

Command sample:
```shell
syndicate generate lambda --name DemoLambda --runtime java --project_path $(pwd)
```

For more details please execute `syndicate generate lambda --help`

### 2.4 Add other infrastructure components 

This step is optional and could be skipped while getting familiar with syndicate.

All the resources syndicate works with could be generated in the same way as lambda. 
Invoke the `syndicate generate meta --help` command to find out which resources are available. 


### 2.5 Open project in your IDE

Now the project is ready to be adjusted. Consider opening your favourite IDE and observe the files created by syndicate. 

## 3. Deployment


### 3.1 Create an S3 bucket for aws-syndicate artifacts:
```shell
syndicate create_deploy_target_bucket
```

### 3.2 Build project artifacts
```shell
syndicate build
```

### 3.3 Deploy project resources to AWS account
```shell
syndicate deploy
```
Now the DemoLambda is created and available to be tested.  

### 3.4 Update resources
In order to be sure your latest changes works well on the AWS account the application should be deployed to the AWS account.
To do this use the following commands set:
```shell
syndicate build
syndicate update
```

### 3.5 Lambdas invocations metrics
```shell
syndicate profiler
```

### 3.6 Clean up project resources from AWS Account
```shell
syndicate clean 
```

### 3.7 Observing the environment manipulation history
```shell
syndicate status # this shows the general CLI dashboard where latest modification, locks state, latest event, project resources are shown
syndicate status --events # this returns all the history of what happened to the environment
```

## 4. Examples

If you are just getting familiar with the functionality, you can use one of the
pre-prepared examples that contain a minimum set of AWS resources and lambdas.

The aws-syndicate/examples folder contains structure examples for different
runtimes. Go to any example you like best and set the environment
variable `SDCT_CONF=$path_to_the_selected_example`.

Add your account details to `syndicate.yml` file - account id,
secret access key, access key and bucket name for deployment.
To `syndicate_aliases.yml` add your account id, region
name (eu-central-1, us-west-1, etc.) and other values in the file that start
with a `$` sign.

Documentation
------------
Documentation you can find [here](https://github.com/epam/aws-syndicate/wiki)

Getting Help
------------

We use GitHub issues for tracking bugs and feature requests. You can find our
public backlog [here](https://github.com/epam/aws-syndicate/projects/1). If it
turns out that you may have found a bug,
please [open an issue](https://github.com/epam/aws-syndicate/issues/new/choose)
with some of existing templates.

Default label for bugs, improvements and feature requests is `To-Think-About`,
it defines that ticket requires additional information about what should be done
in scope of this issue.
`To-Do` label should be added only for tickets with clear and reviewed issue
scope.

But before creating new issues - check existing, they may cover your problem or
question. For increasing issue priority - just add "+1" comment.

Would like to contribute?
-------------------------

Please,
check [contributor guide](https://github.com/epam/aws-syndicate/blob/master/CONTRIBUTING.md)
before starting.

# [![SonarCloud](https://sonarcloud.io/images/project_badges/sonarcloud-white.svg)](https://sonarcloud.io/dashboard?id=aws-syndicate)
