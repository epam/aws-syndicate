import re


def to_logic_name(resource_name):
    name_components = re.split('[^a-zA-Z0-9]', resource_name)
    formatted = []
    for component in name_components:
        component_len = len(component)
        if component_len > 1:
            formatted.append(component[0].upper() + component[1:])
        elif component_len == 1:
            formatted.append(component[0].upper())
    return ''.join(formatted)


def lambda_function_logic_name(function_name):
    return to_logic_name(function_name)


def lambda_alias_logic_name(function_name, alias):
    return to_logic_name('{}{}Alias'.format(
        function_name, alias.capitalize()))


def lambda_publish_version_logic_name(function_name):
    return to_logic_name('{}PublishVersion'.format(function_name))
