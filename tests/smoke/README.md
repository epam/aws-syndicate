# Testing strategy for AWS Syndicate

## Directory structure
```
tests
│   README.md  
│
└───smoke
│   │   happy_path.py
│   │   happy_path_config.json
│   │   requirements.txt
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
│   └───sdct-auto-test
│       │   ...
│   
└─── ...
```

### Description of Key Components

- **`smoke` directory**: Contains test scripts that are designed to quickly verify the basic functionalities of the system. This directory is intended for smoke testing.
  - **`happy_path.py`**: Serves as the entry point for a test scenario that verifies the successful passage of basic flows of the system.
  - **`happy_path_config.json`**: A configuration file that specifies parameters and settings for running the tests. The file name is not strict, it can be passed to the script as a parameter `-c`, `--config`. See the [Configuration](#configuration) section for more details.
  - **`requirements.txt`**: Lists all the libraries required to execute the tests.

#### `commons` Subdirectory
- Contains common utility scripts and modules used across different tests:
  - **`checkers.py`**: Contains checkers functions.
  - **`connections.py`**: Manages boto3 connections.
  - **`constants.py`**: Defines constants used throughout the tests.
  - **`handlers.py`**: Contains mappings and functions that are a layer between the checkers and the step processor.
  - **`step_processors.py`**: Implements logic for processing steps of each stage according to the definition in `happy_path_config.json`.
  - **`utils.py`**: Includes utility functions for general purposes like file or complex structure manipulation.

#### `sdct-auto-test` Subdirectory
- Contains the aws-project on which testing will be carried out. More details about the project can be found [here](sdct-auto-test/README.md)

## Configuration

### Config structure
```json
{
  "init_parameters": {
    "suffix": "-test",
    "deploy_target_bucket": "bucket",
    "prefix": "sdct-",
    "output_file": "output",
    ...
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
- `init_parameters`: Section where you can specify all the additional parameters that are needed to run the tests. For example: the name of the deployment bucket with the bundle, the suffix and prefix of the resources, the name of the output file, etc.
- `stages`: Section with a description of each stage.
  - `$STAGE_NAME`: Related to the syndicate command name to check. Should be clear for further processing of the resulting JSON.
    - `steps`: Section with a description of each step of the stage. 
    - `depends_on`: The list of stage names, the result of which determines the execution of the current one. If at least one stage from the list fails, then the current stage will not execute.
    - `description`: Humanreadable command description.
    - `command`: List with the command plus command line arguments. Here are some default arguments for some commands that are automatically added:
      - `build` - ["--bundle_name", "$BUNDLE_NAME", "--deploy_name", "$DEPLOY_NAME"]
      - `deploy` - ["--bundle_name", "$BUNDLE_NAME", "--deploy_name", "$DEPLOY_NAME", "--replace_output"]
      - `update` - ["--bundle_name", "$BUNDLE_NAME", "--deploy_name", "$DEPLOY_NAME", "--replace_output"]
    
      `$BUNDLE_NAME` and `$DEPLOY_NAME` have internal values and DO NOT need to be specified.
    - `checks`: Section with a description of each check.
      - `index`: Check serial number.
      - `name`: One of the names of available checks. For entire list of checks see the [Checkers](#checkers) section or add your own.
      - `description`: Humanreadable check description.
      - `depends_on`: The list of checks indexes, the result of which determines the execution of the current one. If at least one check from the list fails, then the current check will not execute.
      - The parameters of a check may be extended with check-specific parameters. Custom parameters needed for a specific check (see [Checks](#checks))

## Available checks
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
      ```json
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
      ```json
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
        ```json
        {
          "$RESOURCE_NAME": {
            "resource_type": "$RESOURCE_TYPE"
          }
        }
        ```
    - `deploy_target_bucket` (str) - the syndicate deployment bucket. Required for swagger_ui existence check.
    - `reverse_check` (bool) - defines whether the check result must be swapped to the opposite.
- `resource_modification`: Checks if resources were modified. 
  - parameters: 
    - `resources` (dict) [REQUIRED] - Information about resources to check.  
        structure:
        ```json
        {
          "$RESOURCE_NAME": {
            "resource_type": "$RESOURCE_TYPE"
          }
        }
        ```

## How to run
### Prerequisites
1. Specify valid credentials in the `.aws/credentials` file or set credentials in the `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` env variables.
2. Installed python 3.10+
3. Install requirements from corresponding `requirements.txt`
4. Install aws-syndicate
5. Create aws-syndicate config files and set its path to `SDCT_CONF` env variable

### Available script parameters
  - `-c, --config`: [optional] full path to the config file with described stage checks. Default config is happy_path_config.json
  - `--verbose`: [optional] Enable logging verbose mode. Disabled by default.
