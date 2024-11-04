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
  - **`happy_path.py`**: Serves as the entry point for a test scenario that verifies the successful operation of the system.
  - **`happy_path_config.json`**: A configuration file that specifies parameters and settings for running the tests. The file name is not strict, it can be passed to the script as a parameter `-c`, `--config`. See the [Configuration](#configuration) section for more details.
  - **`requirements.txt`**: Lists all the libraries required to execute the tests.

#### `commons` Subdirectory
- Contains common utility scripts and modules used across different tests:
  - **`checkers.py`**: Contains checkers for each step.
  - **`connections.py`**: Manages boto3 connections.
  - **`constants.py`**: Defines constants used throughout the tests.
  - **`handlers.py`**: Contains mappings and functions that are a layer between the handlers and the step processor.
  - **`step_processors.py`**: Implements logic for processing of each stage from `happy_path_config.json`.
  - **`utils.py`**: Includes utility functions for general purposes like file or complex structure manipulation.

#### `sdct-auto-test` Subdirectory
- Contains the project on which testing will be carried out.

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
              "name": "$CHECKER1_NAME",
              "description": "CHECKER1 DESCRIPTION",
              "expected_exit_code": 0
            },
            {
              "index": 2,
              "name": "$CHECKER2_NAME",
              "description": "CHECKER2 DESCRIPTION",
              "resources": [],
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
- `init_parameters`: Section where you can specify all the additional parameters that are needed to run the checkers. For example: the name of the bucket with the bundle, the suffix and prefix of the resources, the name of the output file, etc.
- `stages`: Section with a description of each stage.
  - `$STAGE_NAME`: Command name to check. Should be clear for further processing of the resulting json.
    - `steps`: Section with a description of each command step. 
    - `depends_on`: The list of stage names, the result of which determines the execution of the current one. If at least one stage from the list fails, then the current stage will not execute.
    - `description`: Humanreadable command description.
    - `command`: List of command line arguments. Here some default arguments for some commands that are automatically added:
      - `build` - ["--bundle_name", "$BUNDLE_NAME", "--deploy_name", "$DEPLOY_NAME"]
      - `deploy` - ["--bundle_name", "$BUNDLE_NAME", "--deploy_name", "$DEPLOY_NAME"]
      - `update` - ["--bundle_name", "$BUNDLE_NAME", "--deploy_name", "$DEPLOY_NAME", "--replace_output"]
    
      `$BUNDLE_NAME` and `$DEPLOY_NAME` have internal values and DO NOT need to be specified.
    - `checks`: Section with a description of each checker.
      - `index`: Checker serial number.
      - `name`: One of the names of available checkers. For entire list of checkers see the [Checkers](#checkers) section or add your own.
      - `description`: Humanreadable check description.
      - `depends_on`: The list of checkers indexes, the result of which determines the execution of the current one. If at least one checker from the list fails, then the current checker will not execute.
      - `expected_exit_code`, `resources`, `more_params`: Custom parameters needed for a specific checker (see [Checkers](#checkers))

## Checkers
- `exit_code`: Check exit code of command from `command` section in config. Required parameters: `actual_exit_code`, `expected_exit_code`.
- `artifacts_existence`: Check if files in s3 bucket exist. Required parameters: `artifacts_list`, `deploy_target_bucket`. Optional parameters: `succeeded_deploy`.
- `build_meta`: Check if all resources in build_meta.json exist. Required parameters: `resources`, `deploy_target_bucket`.
- `deployment_output`: Check if all resources present in deployment output. Required parameters: `deploy_target_bucket`, `resources`. Optional parameters: `succeeded_deploy`, `prefix`, `suffix`.
- `resource_existence`: Check if all resources present in account. Required parameters: `resources`, `deploy_target_bucket`. Optional parameters: `prefix`, `suffix`.
- `resource_modification`: Check if resources were modified. Required parameters: `resources`. Optional parameters: `prefix`, `suffix`.
- `outputs_modification`: Check the time of output.json file last modification. Required parameters: `deploy_target_bucket`.

## How to run
### Prerequisites
1. Specify valid credentials in the `.aws/credentials` file or set credentials in the `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` env variables.
2. Installed python 3.10+
3. Install requirements from corresponding `requirements.txt`

### Available script parameters
  - `-c, --config`: [optional] full path to the config file with described stage checks. Default config is happy_path_config.json
  - `--verbose`: [optional] Enable logging verbose mode. Disabled by default.
