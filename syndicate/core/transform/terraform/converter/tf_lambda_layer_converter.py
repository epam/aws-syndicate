from syndicate.core.constants import S3_PATH_NAME
from syndicate.core.resources.helper import validate_params
from syndicate.core.resources.lambda_resource import \
    LAMBDA_LAYER_REQUIRED_PARAMS
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.tf_resource_name_builder import \
    lambda_layer_name


class LambdaLayerConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        validate_params(name, resource, LAMBDA_LAYER_REQUIRED_PARAMS)

        key = resource[S3_PATH_NAME]
        description = resource.get('description')
        s3_bucket = self.config.deploy_target_bucket
        runtimes = resource.get('runtimes')
        licenses = resource.get('license')

        resource_name = lambda_layer_name(layer_name=name)
        layer = aws_lambda_layer_version(resource_name=resource_name,
                                         layer_name=name,
                                         description=description,
                                         s3_bucket=s3_bucket, s3_key=key,
                                         runtimes=runtimes,
                                         license_info=licenses)
        self.template.add_aws_lambda_layer_version(meta=layer)


def aws_lambda_layer_version(resource_name, layer_name, description=None,
                             license_info=None, runtimes=None,
                             s3_key=None, s3_bucket=None):
    layer = {
        'layer_name': layer_name
    }

    if description:
        layer['description'] = description
    if license_info:
        layer['license_info'] = license_info
    if runtimes:
        layer['compatible_runtimes'] = runtimes
    if s3_key:
        layer['s3_key'] = s3_key
    if s3_bucket:
        layer['s3_bucket'] = s3_bucket

    resource = {
        resource_name: layer
    }
    return resource
