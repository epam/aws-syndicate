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


class TestApiGatewayDuplicatedResources(TestApiGateway):
    def setUp(self) -> None:
        super().setUp()
        self.path = '/signup'
        self.resources = {
            self.path: {
                "enable_cors": True,
                "GET": {}
            }
        }
        self.main_d_r[self.resource_name]['resources'] = \
            self.resources
        self.sub_d_r[self.resource_name]['resources'] = \
            self.resources

    def test_duplicated_resources(self):
        self.write_main_and_sub_deployment_resources(self.main_d_r,
                                                     self.sub_d_r)

        with self.assertRaises(AssertionError) as context:
            self.dispatch(resources_meta={})
        self.assertEqual(str(context.exception),
                         "API '{0}' has duplicated resource '{1}'! Please, "
                         "change name of one resource or remove one.".format(
                             self.resource_name, self.path))


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
