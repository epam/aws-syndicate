from copy import deepcopy
from pathlib import Path

from syndicate.core.constants import (LAMBDA_CONFIG_FILE_NAME,
                                      RESOURCES_FILE_NAME, S3_PATH_NAME)
from tests.test_building_meta import TestBuildingMeta


class TestApiGateway(TestBuildingMeta):
    def setUp(self) -> None:
        super().setUp()
        self.resource_name = 'test_api'
        self.main_d_r = {
            self.resource_name: {
                "dependencies": [],
                "resource_type": "api_gateway",
                "authorizers": {},
                "resources": {}
            }
        }
        self.sub_d_r = deepcopy(self.main_d_r)


class TestApiGateWayClusterCacheConfiguration(TestApiGateway):
    def setUp(self) -> None:
        super().setUp()
        self.cluster_cache_configuration = {
            'key': 'value'
        }
        self.main_d_r[self.resource_name]['cluster_cache_configuration'] = \
            self.cluster_cache_configuration
        self.sub_d_r[self.resource_name]['cluster_cache_configuration'] = \
            self.cluster_cache_configuration

    def test_duplicated_cluster_configuration(self):
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        with self.assertRaises(AssertionError) as context:
            self.dispatch(resources_meta={})
        self.assertEqual(str(context.exception),
                         "API '{0}' has duplicated cluster cache "
                         "configurations. Please, remove one cluster cache "
                         "configuration.".format(
                             self.resource_name))

    def test_resolving_cluster_cache_configuration_main(self):
        self.main_d_r[self.resource_name].pop('cluster_cache_configuration')
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertEqual(
            resources_meta[self.resource_name]['cluster_cache_configuration'],
            self.cluster_cache_configuration
        )

    def test_resolving_cluster_cache_configuration_sub(self):
        self.sub_d_r[self.resource_name].pop('cluster_cache_configuration')
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertEqual(
            resources_meta[self.resource_name]['cluster_cache_configuration'],
            self.cluster_cache_configuration
        )


class TestApiGatewayApiMethodResources(TestApiGateway):
    def setUp(self) -> None:
        super().setUp()
        self.api_method_responses = {
            'key': 'value'
        }
        self.main_d_r[self.resource_name]['api_method_responses'] = \
            self.api_method_responses
        self.sub_d_r[self.resource_name]['api_method_responses'] = \
            self.api_method_responses

    def test_duplicated_api_method_resources(self):
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)

        with self.assertRaises(AssertionError) as context:
            self.dispatch(resources_meta={})
        self.assertEqual(str(context.exception),
                         "API '{0}' has duplicated api method responses "
                         "configurations. Please, remove one "
                         "api method responses configuration.".format(
                             self.resource_name))

    def test_resolving_api_method_resources_main(self):
        self.main_d_r[self.resource_name].pop('api_method_responses')
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertEqual(
            resources_meta[self.resource_name]['api_method_responses'],
            self.api_method_responses
        )

    def test_resolving_api_method_resources_sub(self):
        self.sub_d_r[self.resource_name].pop('api_method_responses')
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertEqual(
            resources_meta[self.resource_name]['api_method_responses'],
            self.api_method_responses
        )


class TestApiGatewayApiMethodIntegrationResponse(TestApiGateway):
    def setUp(self) -> None:
        super().setUp()
        self.api_method_integration_responses = {
            'key': 'value'
        }
        self.main_d_r[self.resource_name]['api_method_integration_responses'] = \
            self.api_method_integration_responses
        self.sub_d_r[self.resource_name]['api_method_integration_responses'] = \
            self.api_method_integration_responses

    def test_duplicated_api_method_integration_responses(self):
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)

        with self.assertRaises(AssertionError) as context:
            self.dispatch(resources_meta={})
        self.assertEqual(str(context.exception),
                         "API '{0}' has duplicated api method integration "
                         "responses configurations. Please, remove one "
                         "api method integration responses "
                         "configuration.".format(self.resource_name))

    def test_resolving_api_method_integration_responses_main(self):
        self.main_d_r[self.resource_name].pop(
            'api_method_integration_responses')
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertEqual(
            resources_meta[self.resource_name][
                'api_method_integration_responses'],
            self.api_method_integration_responses
        )

    def test_resolving_api_method_integration_responses_sub(self):
        self.sub_d_r[self.resource_name].pop(
            'api_method_integration_responses')
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertEqual(
            resources_meta[self.resource_name][
                'api_method_integration_responses'],
            self.api_method_integration_responses
        )


class TestApiGatewayJoinDependencies(TestApiGateway):
    def setUp(self) -> None:
        super().setUp()
        self.common_dependency = {
            "resource_name": "test_bucket",
            "resource_type": "s3_bucket"
        }
        self.dependency_main = {
            "resource_name": "test_table_main",
            "resource_type": "dynamodb_table"
        }
        self.dependency_sub = {
            "resource_name": "test_table_sub",
            "resource_type": "dynamodb_table"
        }
        self.dependencies_main = [
            self.common_dependency,
            self.dependency_main
        ]
        self.dependencies_sub = [
            self.common_dependency,
            self.dependency_sub
        ]
        self.main_d_r[self.resource_name]['dependencies'] = \
            self.dependencies_main
        self.sub_d_r[self.resource_name][
            'dependencies'] = self.dependencies_sub

    def test_join_dependencies(self):
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        dependencies = resources_meta[self.resource_name]['dependencies']
        self.assertIn(self.dependency_main, dependencies)
        self.assertIn(self.dependency_sub, dependencies)
        self.assertIn(self.common_dependency, dependencies)


class TestApiGatewayJoinResources(TestApiGateway):
    def setUp(self) -> None:
        super().setUp()
        self.main_path, self.sub_path = '/main', '/sub'
        self.main_resource = {
            "enable_cors": True,
            "POST": {}
        }
        self.sub_resource = {
            "enable_cors": False,
            "DELETE": {}
        }
        self.main_d_r[self.resource_name]['resources'] = {
            self.main_path: self.main_resource,
        }
        self.sub_d_r[self.resource_name]['resources'] = {
            self.sub_path: self.sub_resource,
        }

    def test_duplicated_resources(self):
        common_path = '/common'
        self.common_resource = {
            common_path: {
                "enable_cors": False,
                "GET": {}
            }
        }
        self.main_d_r[self.resource_name]['resources'].update(
            self.common_resource
        )
        self.sub_d_r[self.resource_name]['resources'].update(
            self.common_resource
        )
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)

        with self.assertRaises(AssertionError) as context:
            self.dispatch(resources_meta={})
        self.assertEqual(str(context.exception),
                         "API '{0}' has duplicated resource '{1}'! Please, "
                         "change name of one resource or remove one.".format(
                             self.resource_name, common_path))

    def test_join_resources(self):
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        resources = resources_meta[self.resource_name]['resources']
        self.assertIn(self.main_path, resources)
        self.assertIn(self.sub_path, resources)
        self.assertEqual(resources[self.main_path], self.main_resource)
        self.assertEqual(resources[self.sub_path], self.sub_resource)


class TestApiGatewayDeployStage(TestApiGateway):
    def setUp(self) -> None:
        super().setUp()
        self.main_d_r[self.resource_name]['deploy_stage'] = "main_stage"
        self.sub_d_r[self.resource_name]['deploy_stage'] = "sub_stage"

    def test_resolving_deploy_stage_main(self):
        # compression size must be taken
        # rightly from MAIN deployment_resouces.json
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertEqual(
            resources_meta[self.resource_name]['deploy_stage'], 'main_stage')

    def test_resolving_deploy_stage_main_does_not_exist(self):
        self.main_d_r[self.resource_name].pop('deploy_stage')

        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)

        resource_meta = {}
        self.dispatch(resource_meta)
        self.assertEqual(
            resource_meta[self.resource_name]['deploy_stage'], "sub_stage")

    def test_resolving_deploy_stage_does_not_exist(self):
        self.main_d_r[self.resource_name].pop('deploy_stage')
        self.sub_d_r[self.resource_name].pop('deploy_stage')

        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resource_meta = {}
        self.dispatch(resource_meta)
        self.assertNotIn('deploy_stage', resource_meta[self.resource_name])


class TestApiGatewayCompressionSize(TestApiGateway):
    def setUp(self) -> None:
        super().setUp()
        self.main_d_r[self.resource_name]['minimum_compression_size'] = 400
        self.sub_d_r[self.resource_name]['minimum_compression_size'] = 300

    def test_resolving_compression_size_main(self):
        # compression size must be taken
        # rightly from MAIN deployment_resouces.json
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertEqual(
            resources_meta[self.resource_name]['minimum_compression_size'],
            400)

    def test_resolving_compression_size_main_does_not_exist(self):
        self.main_d_r[self.resource_name].pop('minimum_compression_size')

        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)

        resource_meta = {}
        self.dispatch(resource_meta)
        self.assertEqual(
            resource_meta[self.resource_name]['minimum_compression_size'], 300)

    def test_resolving_compression_size_does_not_exist(self):
        self.main_d_r[self.resource_name].pop('minimum_compression_size')
        self.sub_d_r[self.resource_name].pop('minimum_compression_size')

        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resource_meta = {}
        self.dispatch(resource_meta)
        self.assertNotIn('minimum_compression_size',
                         resource_meta[self.resource_name])


class TestApiGatewayMergeListTypedConfiguration(TestApiGateway):
    def setUp(self) -> None:
        super().setUp()
        self.binary_media_types_main = ['bt_main_1', 'bt_main_2']
        self.binary_media_types_sub = ['bt_sub_1', 'bt_sub_2']
        self.apply_changes_main = ['main_change_1', 'main_change_2']
        self.apply_changes_sub = ['sub_change_1', 'sub_change_2']

    def test_merge_binary_media_types(self):
        self.main_d_r[self.resource_name]['binary_media_types'] = \
            self.binary_media_types_main
        self.sub_d_r[self.resource_name]['binary_media_types'] = \
            self.binary_media_types_sub
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertIn('binary_media_types', resources_meta[self.resource_name])
        self.assertEqual(resources_meta[self.resource_name].get(
            'binary_media_types'),
            self.binary_media_types_main + self.binary_media_types_sub
        )

    def test_merge_apply_changes(self):
        self.main_d_r[self.resource_name]['apply_changes'] = \
            self.apply_changes_main
        self.sub_d_r[self.resource_name]['apply_changes'] = \
            self.apply_changes_sub
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertIn('apply_changes', resources_meta[self.resource_name])
        self.assertEqual(resources_meta[self.resource_name].get(
            'apply_changes'),
            self.apply_changes_main + self.apply_changes_sub
        )


class TestEqualResourcesFound(TestBuildingMeta):
    """It applies to all the resouces types except API_GATEWAY"""

    def setUp(self) -> None:
        super().setUp()
        self.resources_name = 'test_bucket'
        self.main_d_r = {
            self.resources_name: {
                "resource_type": "s3_bucket",
                "cors": []
            }
        }
        self.sub_d_r = deepcopy(self.main_d_r)

    def test_two_equal_resouces_found(self):
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)

        with self.assertRaises(AssertionError) as context:
            self.dispatch(resources_meta={})
        self.assertEqual(str(context.exception),
                         'Warn. Two equals resources descriptions were found! '
                         'Please, remove one of them. Resource name:'
                         ' {0}'.format(self.resources_name))

    def test_two_resouces_with_equal_names_found(self):
        self.sub_d_r[self.resources_name]['location'] = 'eu-west-1'
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)

        with self.assertRaises(AssertionError) as context:
            self.dispatch(resources_meta={})
        self.assertEqual(str(context.exception),
                         "Error! Two resources with equal names were found! "
                         "Name: {0}. Please, rename one of them. First "
                         "resource: {1}. Second resource: {2}".format(
                             self.resources_name,
                             self.main_d_r[self.resources_name],
                             self.sub_d_r[self.resources_name]))


class WrongResourceType(TestBuildingMeta):
    def setUp(self) -> None:
        super().setUp()
        self.resource_name = 'resource_without_type'
        self.main_d_r = {
            self.resource_name: {
                "dependencies": [],
                "authorizers": {},
            }
        }

    def test_resource_type_not_found(self):
        self.write_json_to_tmp(RESOURCES_FILE_NAME, self.main_d_r)

        with self.assertRaises(AssertionError) as context:
            self.dispatch(resources_meta={})
        self.assertEqual(str(context.exception),
                         "There is not 'resource_type' in {0}".format(
                             self.resource_name))

    def test_resource_type_not_in_available_resource_list(self):
        not_available_type = 'not_available'
        self.main_d_r[self.resource_name]['resource_type'] = not_available_type
        self.write_json_to_tmp(RESOURCES_FILE_NAME, self.main_d_r)

        with self.assertRaises(KeyError) as context:
            self.dispatch(resources_meta={})
        self.assertEqual(context.exception.args[0],
                         "You specified new resource type in configuration"
                         " file {0}, but it doesn't have creation function."
                         " Please, add new creation function or change "
                         "resource name with existing one.".format(
                             not_available_type))


class TestBuildingLambdaResource(TestBuildingMeta):
    def setUp(self) -> None:
        super().setUp()
        self.main_d_r = {
            "test_role": {
                "predefined_policies": [],
                "principal_service": "lambda",
                "custom_policies": [],
                "resource_type": "iam_role",
            }
        }
        # java lambda deployment_resources
        self.package_name = 'test_package-1.0.0.jar'
        self.sub_d_r = {
            "second": {
                "name": "second",
                "lambda_path": "",
                "version": "1.0.0",
                "func_name": "com.testproject.Second",
                "deployment_package": self.package_name,
                "resource_type": "lambda",
                "runtime": "java8",
                "iam_role_name": "second-role",
                "memory": 1024,
                "timeout": 300,
                "subnet_ids": [],
                "security_group_ids": [],
                "dependencies": [],
                "event_sources": [],
                "env_variables": {},
                "publish_version": True,
                "alias": "${lambdas_alias_name}"
            }
        }
        self.lambda_name = 'test_lambda'
        self.lambda_config = {
            "version": "2.0",
            "name": self.lambda_name,
            "func_name": "handler.lambda_handler",
            "resource_type": "lambda",
            "iam_role_name": "test_role",
            "runtime": "python3.7",
            "memory": 128,
            "timeout": 100,
            "lambda_path": "",
            "dependencies": [],
            "event_sources": [],
            "env_variables": {},
            "publish_version": True,
            "alias": "${lambdas_alias_name}"
        }

    def test_resolving_lambda_name(self):
        self.write_json_to_tmp(Path('sub_dir', LAMBDA_CONFIG_FILE_NAME),
                               self.lambda_config)
        self.write_json_to_tmp(RESOURCES_FILE_NAME, self.main_d_r)

        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertIn(self.lambda_name, resources_meta)
        resources_meta[self.lambda_name].pop(S3_PATH_NAME)

        self.assertEqual(resources_meta[self.lambda_name], self.lambda_config)
        self.assertIn('test_role', resources_meta)
        self.assertEqual(resources_meta['test_role'],
                         self.main_d_r['test_role'])

    def test_populating_s3_path_python_lambda(self):
        self.write_json_to_tmp(Path('sub_dir', LAMBDA_CONFIG_FILE_NAME),
                               self.lambda_config)
        self.write_json_to_tmp(RESOURCES_FILE_NAME, self.main_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertIn(S3_PATH_NAME, resources_meta[self.lambda_name])
        self.assertEqual(f"{self.bundle_name}/{self.lambda_name}-2.0.zip",
                         resources_meta[self.lambda_name][S3_PATH_NAME])

    def test_population_s3_path_java_lambda(self):
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertIn(S3_PATH_NAME, resources_meta['second'])
        self.assertEqual(f"{self.bundle_name}/{self.package_name}",
                         resources_meta['second'][S3_PATH_NAME])


class TestBuildingMetaSuccess(TestBuildingMeta):
    def setUp(self) -> None:
        super().setUp()
        self.main_d_r = {
            "test_table": {
                "resource_type": 'dynamodb_table',
                "hash_key_name": "id",
                "hash_key_type": "S",
                "read_capacity": 1,
                "write_capacity": 1,
            },

            'test_gateway': {
                "dependencies": [
                    {
                        "resource_name": "test_table",
                        "resource_type": "dynamodb_table"
                    }
                ],
                "resource_type": "api_gateway",
                "authorizers": {},
                "resources": {
                    "/test-1": {
                        "enable_cors": True,
                        "GET": {}
                    }
                }
            }
        }
        self.sub_d_r = {
            'test_bucket': {
                "resource_type": "s3_bucket",
                "cors": []
            },
            'test_gateway': {
                "dependencies": [
                    {
                        "resource_type": "s3_bucket",
                        "resource_name": 'test_bucket'
                    }
                ],
                "resource_type": "api_gateway",
                "authorizers": {},
                "resources": {
                    "/test-2": {
                        "enable_cors": True,
                        "POST": {}
                    }
                }
            }
        }

    def test_building_meta_success(self):
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        expected_result = {
            "test_table": {
                "resource_type": "dynamodb_table",
                "hash_key_name": "id",
                "hash_key_type": "S",
                "read_capacity": 1,
                "write_capacity": 1
            },
            "test_gateway": {
                "dependencies": [
                    {
                        "resource_type": "s3_bucket",
                        "resource_name": "test_bucket"
                    },
                    {
                        "resource_name": "test_table",
                        "resource_type": "dynamodb_table"
                    }
                ],
                "resource_type": "api_gateway",
                "authorizers": {},
                "resources": {
                    "/test-2": {
                        "enable_cors": True,
                        "POST": {}
                    },
                    "/test-1": {
                        "enable_cors": True,
                        "GET": {}
                    }
                },
                "binary_media_types": [],
                "apply_changes": []
            },
            "test_bucket": {
                "resource_type": "s3_bucket",
                "cors": []
            }
        }
        self.assertEqual(resources_meta, expected_result)
