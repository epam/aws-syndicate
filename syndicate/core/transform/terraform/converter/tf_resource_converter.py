from abc import abstractmethod

from syndicate.core.transform.terraform.terraform_template import \
    TerraformTemplate


class TerraformResourceConverter:

    def __init__(self, template: TerraformTemplate, config=None,
                 resources_provider=None):
        self.template = template
        self.config = config
        self.resources_provider = resources_provider

    @abstractmethod
    def convert(self, name, resource):
        pass
