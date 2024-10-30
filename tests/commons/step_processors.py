from commons import handlers
from syndicate.core.handlers import build, deploy, clean, update


def run_build(params):
    verbose = params.get('verbose')
    bundle_name = params.get('bundle_name')
    result = build(verbose=verbose, bundle_name=bundle_name)
    return True if not result else False


def run_deploy(params):
    verbose = params.get('verbose')
    bundle_name = params.get('bundle_name')
    deploy_name = params.get('deploy_name')
    result = deploy(verbose=verbose, bundle_name=bundle_name,
                    deploy_name=deploy_name)
    return True if not result else False


def run_clean(params):
    verbose = params.get('verbose')
    bundle_name = params.get('bundle_name')
    deploy_name = params.get('deploy_name')
    result = clean(verbose=verbose, bundle_name=bundle_name,
                   deploy_name=deploy_name)
    return True if not result else False


def run_update(params):
    verbose = params.get('verbose')
    bundle_name = params.get('bundle_name')
    deploy_name = params.get('deploy_name')
    result = update(verbose=verbose, bundle_name=bundle_name,
                    deploy_name=deploy_name)
    return True if not result else False


def get_s3_file(params):
    bucket_name = params.get('bucket_name')
    file_key = params.get('file_key')
    result = handlers.get_s3_bucket_file_content(
        bucket_name=bucket_name, file_key=file_key)
    return True if result else False
