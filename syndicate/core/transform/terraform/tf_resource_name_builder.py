def build_terraform_resource_name(*args):
    res_name = []
    for arg in args:
        if arg:
            res_name.append(arg[0].upper() + arg[1:])
    return ''.join(res_name)


def lambda_layer_name(layer_name):
    return build_terraform_resource_name(layer_name, 'layer')
