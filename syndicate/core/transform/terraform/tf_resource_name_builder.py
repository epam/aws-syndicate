def build_terraform_resource_name(*args):
    res_name = []
    for arg in args:
        res_name.append(arg[0].upper() + arg[1:])
    return ''.join(res_name)
