from typing import Optional

from tests.smoke.commons import connections


def exit_code(actual_exit_code: int, expected_exit_code: int, **kwargs):
    return actual_exit_code == expected_exit_code


def artifacts_exist(artifacts_list: list, deploy_target_bucket: str,
                    suffix: Optional[str] = None, prefix: Optional[str] = None,
                    **kwargs):
    missing_resources = []
    for artifact in artifacts_list:
        exist = connections.get_s3_bucket_object(
            bucket_name=deploy_target_bucket, file_key=artifact)
        if not exist:
            missing_resources.append(artifact)
    return {'missing_resources': missing_resources} \
        if missing_resources else True


def build_meta(resources: dict, suffix: Optional[str] = None,
               prefix: Optional[str] = None, **kwargs):
    ...


HANDLERS_MAPPING = {
    'exit_code': exit_code,
    'artifacts_exist': artifacts_exist,
    'build_meta': build_meta
}
