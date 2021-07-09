from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class SNSApplicationConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        platform = resource.get('platform')
        attributes = resource.get('attributes')
        platform_credential = attributes.get('PlatformCredential')
        platform_principal = attributes.get('PlatformPrincipal')

        app_meta = build_sns_app_meta(application_name=name, platform=platform,
                                      platform_credential=platform_credential,
                                      platform_principal=platform_principal)
        self.template.add_aws_sns_platform_application(meta=app_meta)


def build_sns_app_meta(application_name, platform, platform_credential,
                       platform_principal):
    application = {}
    if application_name:
        application.update({'name': application_name})

    if platform:
        application.update({'platform': platform})

    if platform_credential:
        application.update({'platform_credential': platform_credential})

    if platform_principal:
        application.update({'platform_principal': platform_principal})

    resource = {
        application_name: application
    }
    return resource
