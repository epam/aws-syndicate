from abc import ABC, abstractmethod
from pprint import pformat

from syndicate.core.resources.helper import filter_dict_by_shape


class AbstractExternalResource(ABC):
    @abstractmethod
    def define_resource_shape(self):
        pass

    @abstractmethod
    def describe_meta(self, name):
        pass

    def compare_meta(self, name, syndicate_meta):
        aws_meta = self.describe_meta(name)

        resource_shape = self.define_resource_shape()
        syndicate_meta = self.filter_meta(
            meta=syndicate_meta,
            shape=resource_shape
        )

        aws_resource_meta = aws_meta.get(name)
        if not aws_resource_meta:
            return f"External resource '{name}' does not exist"

        aws_meta = self.filter_meta(
            meta=aws_resource_meta,
            shape=resource_shape
        )

        for key in syndicate_meta.keys():
            syndicate_value = syndicate_meta.get(key)
            aws_value = aws_meta.get(key)

            if isinstance(aws_value, list):
                try:  # sorting flat list
                    syndicate_value.sort()
                    aws_value.sort()
                except TypeError:  # sorting list of dicts
                    sort_key = list(aws_value[0].keys())[0]

                    syndicate_value.sort(key=lambda k: k[sort_key])
                    aws_value.sort(key=lambda k: k[sort_key])

        if syndicate_meta != aws_meta:
            return self.get_errors(
                resource_name=name,
                syndicate_meta=syndicate_meta,
                aws_meta=aws_meta
            )

    @staticmethod
    def filter_meta(meta, shape):
        return filter_dict_by_shape(meta, shape)

    @staticmethod
    def get_errors(resource_name, syndicate_meta, aws_meta):
        errors = [f"'{resource_name}' resource meta mismatch:"]
        for key in syndicate_meta.keys():
            syndicate_value = syndicate_meta.get(key)
            aws_value = aws_meta.get(key)

            if isinstance(aws_value, (str, int)) and syndicate_value != aws_value:
                errors.append(f"Expected '{key}' value: '{pformat(syndicate_value)}',\nGot '{pformat(aws_value)}'")
            if isinstance(aws_value, list):
                for aws_item, syndicate_item in zip(aws_value, syndicate_value):
                    if aws_item != syndicate_item:
                        errors.append(
                            f"Expected '{key}' value: '{pformat(syndicate_item)}',\nGot '{pformat(aws_item)}'")
        return '\n'.join(errors)
