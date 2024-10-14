# lambda-with-url-with-layers

This project is an example of solution that contains:
- lambda function with name `hello_world` and runtime `dotnet`
  - configured lambda function URL
  - configured usage of lambda alias and publishing of lambda versions
- lambda layer with name `external_libs` to store external libraries
- lambda layer with name `custom_lib` to store library created from custom code

### Notice
The solution was tested on .NET SDK version  8.0.402

## Lambda function URL configuration
1. Add the next key-value pair to the file lambda_config.json
```
  "url_config": {
    "auth_type": "NONE"
  }
```

## Configure lambda alias
1. Add the next key-value pair to the file lambda_config.json
```
  "alias": "${lambdas_alias_name}"
```
2. Define lambda alias name by adding proper value of the key `lambdas_alias_name` in the file `syndicate_aliases.yml`
```
  lambdas_alias_name: demo
```

## Configure lambda function versions publishing
1. Add the next key-value pair to the file lambda_config.json
```
  "publish_version": true
```

## Assembledge of the package(HWP.1.0.2.nupkg) for the `custom_lib` layer
1. dotnet build `path/to/custom_lib_source_code`
2. dotnet pack `path/to/custom_lib_source_code` -p:Version=1.0.2

#### Expected response
```buildoutcfg
Hello world from lambda! Hello World from layer!
```
---
