from abc import abstractmethod

from syndicate.core.transform.terraform.terraform_template import \
    TerraformTemplate


class TerraformResourceConverter:

    def __init__(self, template: TerraformTemplate, config=None):
        self.template = template
        self.config = config

    @abstractmethod
    def convert(self, name, resource):
        pass
