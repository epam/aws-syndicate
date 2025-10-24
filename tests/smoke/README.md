# Testing strategy for AWS Syndicate

## Content
- [Directory structure](#directory-structure)
  - [Description of Key Components](#description-of-key-components)
  - [Files for update](#files-to-update)
- [Configuration](#configuration)
  - [Config structure](#config-structure)
  - [Description of Config Components](#description-of-config-components)
  - [Available checks](#available-checks)
  - [Temporary-checks-conditions](#temporary-checks-conditions)
- [How to run](#how-to-run)
  - [Prerequisites](#prerequisites)
  - [Available script parameters](#available-script-parameters)

## Directory structure
```
tests
│   README.md  
│
└───smoke
│   │   entry_point.py
│   │   requirements.txt
│   │
│   └───configs
│   │   │   ddis_resources_check_config.json
│   │   │   least_used_resources_check_config.json
│   │   │   ...
│   │
│   └───commons
│   │   │   checkers.py
│   │   │   connections.py
│   │   │   constants.py
│   │   │   handlers.py
│   │   │   step_processors.py
│   │   │   utils.py
│   │   │   ...
│   │
│   └───sdct-at-ddis
│   │   │   ...
│   │
│   └───sdct-at-least-used-resources
│       │   ...
│   
└─── ...
```

### Description of Key Components

- **`smoke` directory**: Contains test scripts that are designed to quickly verify the basic functionalities of the system. This directory is intended for smoke testing.
  - **`entry_point.py`**: Serves as the entry point for a test scenario that verifies the successful passage of basic flows of the system.
  - **`requirements.txt`**: Lists all the libraries required to execute the tests.

#### `configs` Subdirectory
- Contains configuration files that specify parameters and settings for running the tests. 
The file name is not strict, it can be passed to the script as a parameter `-c`, `--config`. See the [Configuration](#configuration) section for more details.
  - **`ddis_resources_check_config.json`**: configuration file for the `sdct-at-ddis` project.
  - **`least_used_resources_check_config.json`**: configuration file for the `sdct-at-least-used-resources` project.

#### `commons` Subdirectory
- Contains common utility scripts and modules used across different tests:
  - **`checkers.py`**: Contains checkers functions.
  - **`connections.py`**: Manages boto3 connections.
  - **`constants.py`**: Defines constants used throughout the tests.
  - **`handlers.py`**: Contains mappings and functions that are a layer between the checkers and the step processor.
  - **`step_processors.py`**: Implements logic for processing steps of each stage according to the definition in configuration file.
  - **`utils.py`**: Includes utility functions for general purposes like file or complex structure manipulation.

#### `sdct-at-ddis` Subdirectory
- Contains the aws-project on which testing will be carried out. More details about the project can be found [here](sdct-at-ddis/README.md)

#### `sdct-at-least-used-resources` Subdirectory
- Contains the aws-project with rare used resources. More details about the project can be found [here](sdct-at-least-used-resources/README.md)

### Files to update
- Lambda and overall resources configuration files with the `_updated` suffix are required to test the `syndicate update` command. 
The content of these files apply to the current corresponding configs while the resources are being updated. 
Afterwards, the original configs return the original content. Example: 
  1. Start testing `syndicate update` stage;
  2. Change content of `sdct-at-ddis/app/lambdas/sdct-at-nodejs-lambda/lambda_config.json` file to content of `sdct-at-ddis/app/lambdas/sdct-at-nodejs-lambda/lambda_config_updated.json`;
  3. Build bundle with updated configuration;
  4. Wait for `syndicate update` to finish executing (successfully or not, whatever);
  5. Return original content of `sdct-at-ddis/app/lambdas/sdct-at-nodejs-lambda/lambda_config.json` file.

## Configuration

### Config structure
```json5
{
  "init_parameters": {
    "output_file": "output",
    // more params if needed
  },
  "stages": {
    "$STAGE_NAME": {
      "steps": [
        {
          "description": "STAGE DESCRIPTION",
          "command": ["syndicate", "update", "--force"],
          "checks": [
            {
              "index": 1,
              "name": "$CHECK1_NAME",
              "description": "CHECK1 DESCRIPTION",
              "expected_exit_code": 0
            },
            {
              "index": 2,
              "name": "$CHECK2_NAME",
              "description": "CHECK2 DESCRIPTION",
              "resources": {},
              "depends_on": [1]
            }
          ],
          "depends_on": ["$ANOTHER_STAGE_NAME"]
        }
      ]
    }
  }
}
```

### Description of Config Components
- `init_parameters`: Section where you can specify all the additional parameters that are needed to run the tests. For example: the name of the output file, etc.
- `stages`: Section with a description of each stage.
  - `$STAGE_NAME`: Related to the syndicate command name to check. Should be clear for further processing of the resulting JSON.
    - `steps`: Section with a description of each step of the stage. 
    - `depends_on`: The list of stage names, the result of which determines the execution of the current one. If at least one stage from the list fails, then the current stage will not execute.
    - `description`: Humanreadable command description.
    - `command`: List with the command plus command line arguments. Here are some default arguments for some commands that are automatically added:
      - `build` - ["--bundle-name", "$BUNDLE_NAME", "--deploy-name", "$DEPLOY_NAME"]
      - `deploy` - ["--bundle-name", "$BUNDLE_NAME", "--deploy-name", "$DEPLOY_NAME", "--replace-output"]
      - `update` - ["--bundle-name", "$BUNDLE_NAME", "--deploy-name", "$DEPLOY_NAME", "--replace-output"]
    
      `$BUNDLE_NAME` and `$DEPLOY_NAME` have internal values and DO NOT need to be specified.
    - `checks`: Section with a description of each check.
      - `index`: Check serial number.
      - `name`: One of the names of available checks. For entire list of checks see the [Checkers](#checkers) section or add your own.
      - `description`: Humanreadable check description.
      - `depends_on`: The list of checks indexes, the result of which determines the execution of the current one. If at least one check from the list fails, then the current check will not execute.
      - The parameters of a check may be extended with check-specific parameters. Custom parameters needed for a specific check (see [Checks](#checks))

### Available checks
- `exit_code` - Checks the exit code of the command from the `command` section in the step config.
  - parameters:
    - `expected_exit_code` (int) [REQUIRED] - expected exit code of the syndicate after running the command.
    - `actual_exit_code` (int) [REQUIRED] - actual exit code of the syndicate after running the command.
- `artifacts_existence` - Checks the existence of the files in the s3 bucket. 
  - parameters: 
    - `artifacts_list` (list) [REQUIRED] - names of files.
    - `deploy_target_bucket` (str) [REQUIRED] - the syndicate deployment bucket
    - `succeeded_deploy` (bool) - defines whether succeeded or failed deployment output needs to be checked.  
    - `reverse_check` (bool) - defines whether the check result must be swapped to the opposite.
- `build_meta` - Checks if resources are present in build_meta.json.
  - parameters: 
    - `resources` (dict) [REQUIRED] - Information about resources to check.  
      structure:
      ```json5
      {
        "$RESOURCE_NAME": {
          "resource_type": "$RESOURCE_TYPE"
        }
      }
      ```
    - `deploy_target_bucket` (str) [REQUIRED] - the syndicate deployment bucket.
- `deployment_output` - Checks whether resources are present in the deployment output.
  - parameters: 
    - `deploy_target_bucket` (str) [REQUIRED] - the syndicate deployment bucket. 
    - `resources` (dict) [REQUIRED] - Information about resources to check.  
      structure:
      ```json5
      {
        "$RESOURCE_NAME": {
          "resource_type": "$RESOURCE_TYPE"
        }
      }
      ```
    - `succeeded_deploy` (bool) [REQUIRED] - defines whether succeeded or failed deployment output needs to be checked.
    - `reverse_check` (bool) - defines whether the check result must be swapped to the opposite.
- `resource_existence` - Checks whether resources are present in the account. 
  - parameters:
    - `resources` (dict) [REQUIRED] - Information about resources to check.  
        structure:
        ```json5
        {
          "$RESOURCE_NAME": {
            "resource_type": "$RESOURCE_TYPE"
          }
        }
        ```
    - `deploy_target_bucket` (str) - the syndicate deployment bucket. Required for swagger_ui existence check.
    - `reverse_check` (bool) - defines whether the check result must be swapped to the opposite.
- `resource_modification` - Checks if resources were modified. 
  - parameters: 
    - `resources` (dict) [REQUIRED] - Information about resources to check.  
        structure:
        ```json5
        {
          "$RESOURCE_NAME": {
            "resource_type": "$RESOURCE_TYPE"
          }
        }
      ```
- `tag_existence` - Checks whether resources has specific tags. 
  - parameters:
    - `resources` (dict) [REQUIRED] - Information about resources to check.  
        structure:
        ```json5
        {
          "$RESOURCE_NAME": {
            "resource_type": "$RESOURCE_TYPE",
            "tags": {
              "tag_name1": "tag_value1",
              "tag_name2": "tag_value2",
              // ...
              "tag_nameN": "tag_valueN"
            }
          }
        }
        ```
    - `reverse_check` (bool) - defines whether the check result must be swapped to the opposite.
- `lambda_trigger_existence` - Checks whether lambda has triggers. 
  - parameters:
    - `triggers` (dict) [REQUIRED] - Information about lambdas to check:
        structure:
        ```json5
        {
          "triggers": {
            "$LAMBDA_NAME": [
              {
                "resource_name": "trigger_name",
                "resource_type": "sqs_queue|dynamodb_trigger|sns_topic|cloudwatch_rule"
              },
              // ...
            ]
          }
        }
        ```
- `lambda_env_existence` - Checks whether lambdas has specific environment variables. 
  - parameters:
    - `env_variables` (dict) [REQUIRED] - Information about lambdas to check. `*` in env value means value does 
not matter and only the presence of a particular key will be checked.
        structure:
        ```json5
        {
          "env_variables": {
            "$LAMBDA_NAME1": {
              "DOTNET_SHARED_STORE": "/opt/dotnetcore/store/"
            },
            "$LAMBDA_NAME2": {
                "cup_id": "*"
            }
          }
        }
        ```
- `appsync_modification` - Checks appsync resource configuration. 
  - parameters:
    - `resources` (dict) [REQUIRED] - Appsync configuration to check. Should include `resolvers` and `data_sources`.
`functions` parameter is optional.
        structure:
        ```json5
          {
              "resources": {
                "appsync_name": {
                  "data_sources": [
                    {
                      "name": "table",
                      "type": "AMAZON_DYNAMODB"
                    }
                  ],
                  "resolvers": [
                    {
                      "type_name": "Post",
                      "field_name": "id",
                      "data_source_name": "table"
                    }
                  ],
                  "functions": [
                    {
                      "name": "get_user",
                      "data_source_name": "table"
                    }
                  ]
                }
              }
          }
        ```
- `trusted_relationships_content` - Checks resources in trusted relationships of IAM role.
  - parameters:
    - `resources` (dict) [REQUIRED] - IAM roles configuration to check. Should include either `resources_absence` or `resources_presence`.
        structure:
        ```json5
          {
              "resources": {
                "iam_role_name": {
                  "resources_absence": [
                    "not_trusted_resource_name1",
                    "not_trusted_resource_nameN"
                  ],
                  "resources_presence": [
                    "trusted_resource_name1",
                    "trusted_resource_nameN"
                  ]
                }
              }
          }
        ```

### Temporary checks conditions
- Use tags from `tests/smoke/sdct-at-ddis/.syndicate-config/syndicate.yml` unless change them in happy_path_config.json:
```json5
{
  "index": 6,
  "name": "tag_existence",
  "description": "Check if tags were updated",
  "resources": {
    "sdct-at-nodejs-lambda": {
      "resource_type": "lambda",
      "tags": {
        "updated_tests": "updated_smoke", // tags from resource configuration
        "project": "sdct-auto-test",  // tags from syndicate.yml
        "project-level-tag": "set-from-project" // tags from syndicate.yml
      }
    }
  },
  "depends_on": [1, 2]
}
```

## How to run

### Important notice
- Utilizing various prefixes and/or suffixes in extended prefix mode for different test projects (e.g., sdct-at-ddis, sdct-at-least-used-resources) is essential for conducting simultaneous tests due to the duplication of resource names across different test projects.
- The AWS region where test resources will be deployed must include a default VPC and default subnet, as these are necessary for the deployment of RDS Aurora instances.
- Due to the slow deployment and cleaning of RDS resources, tests may take up to 40 minutes.

### Prerequisites
1. Specify valid credentials in the `.aws/credentials` file or set credentials in the `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` env variables.
2. Install python 3.10+.
3. Install maven.
4. Install .NET SDK.
5. Install aws-syndicate from pypi: `pip install aws-syndicate`; or from local folder: `pip install -e PATH_TO_REPO/aws-syndicate`.
6. Create aws-syndicate config files and set its path to `SDCT_CONF` env variable. Example of syndicate configs in the 
`tests/smoke/sdct-at-ddis/.syndicate-config` folder.
7. Create deployment bucket if needed: `syndicate create_deploy_target_bucket`.
8. Example command to run the test via the console: `python3 tests/smoke/entry_point.py --verbose`

### Available script parameters
  - `-c, --config`: [optional] full path to the config file with described stage checks. Default config is tests/smoke/configs/ddis_resources_check_config.json
  - `--verbose`: [optional] Enable logging verbose mode. Disabled by default.
