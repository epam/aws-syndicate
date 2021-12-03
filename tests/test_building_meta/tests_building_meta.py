from copy import deepcopy

from tests.test_building_meta import TestBuildingMeta


class TestApiGateway(TestBuildingMeta):
    def setUp(self) -> None:
        super().setUp()
        self.resource_name = 'test_api'
        self.main_d_r = {
            self.resource_name: {
                "dependencies": [],
                "resource_type": "api_gateway",
                "deploy_stage": "test",
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
            resources_meta['test_api']['minimum_compression_size'], 400)

    def test_resolving_compression_size_main_does_not_exist(self):
        self.main_d_r[self.resource_name].pop('minimum_compression_size')

        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)

        resource_meta = {}
        self.dispatch(resource_meta)
        self.assertEqual(
            resource_meta['test_api']['minimum_compression_size'], 300)

    def test_resolving_compression_size_does_not_exist(self):
        self.main_d_r[self.resource_name].pop('minimum_compression_size')
        self.sub_d_r[self.resource_name].pop('minimum_compression_size')

        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)
        resource_meta = {}
        self.dispatch(resource_meta)
        self.assertNotIn('minimum_compression_size',
                         resource_meta['test_api'])


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
