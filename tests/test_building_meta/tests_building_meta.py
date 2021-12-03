from copy import deepcopy

from tests.test_building_meta import TestBuildingMeta


class TestApiGateway(TestBuildingMeta):
    RESOURCE_NAME = 'test_api'
    MAIN_D_R = {
        RESOURCE_NAME: {
            "dependencies": [],
            "resource_type": "api_gateway",
            "deploy_stage": "test",
            "authorizers": {},
            "resources": {}
        }
    }
    SUB_D_R = deepcopy(MAIN_D_R)


class TestApiGatewayDuplicatedResources(TestApiGateway):
    def setUp(self) -> None:
        super().setUp()
        self.resources = {
            '/signup': {
                "enable_cors": True,
                "GET": {}
            }
        }
        self.MAIN_D_R[self.RESOURCE_NAME]['resources'] = \
            self.resources
        self.SUB_D_R[self.RESOURCE_NAME]['resources'] = \
            self.resources

    def test_duplicated_resources(self):
        self.write_main_and_sub_deployment_resources()

        with self.assertRaises(AssertionError) as context:
            self.dispatch(resources_meta={})
        self.assertEqual(str(context.exception),
                         "API '{0}' has duplicated resource '{1}'! Please, "
                         "change name of one resource or remove one.".format(
                             self.RESOURCE_NAME, '/signup')
                         )


class TestApiGatewayCompressionSize(TestApiGateway):
    def setUp(self) -> None:
        super().setUp()
        self.MAIN_D_R[self.RESOURCE_NAME]['minimum_compression_size'] = 400
        self.SUB_D_R[self.RESOURCE_NAME]['minimum_compression_size'] = 300

    def test_resolving_compression_size_main(self):
        # compression size must be taken
        # rightly from MAIN deployment_resouces.json
        self.write_main_and_sub_deployment_resources()
        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertEqual(
            resources_meta['test_api']['minimum_compression_size'], 400)

    def test_resolving_compression_size_main_does_not_exist(self):
        self.MAIN_D_R[self.RESOURCE_NAME].pop('minimum_compression_size')

        self.write_main_and_sub_deployment_resources()

        resource_meta = {}
        self.dispatch(resource_meta)
        self.assertEqual(
            resource_meta['test_api']['minimum_compression_size'], 300)

    def test_resolving_compression_size_does_not_exist(self):
        self.MAIN_D_R[self.RESOURCE_NAME].pop('minimum_compression_size')
        self.SUB_D_R[self.RESOURCE_NAME].pop('minimum_compression_size')

        self.write_main_and_sub_deployment_resources()
        resource_meta = {}
        self.dispatch(resource_meta)
        self.assertNotIn('minimum_compression_size',
                         resource_meta['test_api'])


class TestEqualResourcesFound(TestBuildingMeta):
    """It applies to all the resouces types except API_GATEWAY"""
    RESOURCE_NAME = 'test_bucket'
    MAIN_D_R = {
            RESOURCE_NAME: {
                "resource_type": "s3_bucket",
                "cors": []
            }
        }
    SUB_D_R = deepcopy(MAIN_D_R)

    def test_two_equal_resouces_found(self):
        self.write_main_and_sub_deployment_resources()

        with self.assertRaises(AssertionError) as context:
            self.dispatch(resources_meta={})
        self.assertEqual(str(context.exception),
                         'Warn. Two equals resources descriptions were found! '
                         'Please, remove one of them. Resource name:'
                         ' {0}'.format(self.RESOURCE_NAME))

    def test_two_resouces_with_equal_names_found(self):
        self.SUB_D_R[self.RESOURCE_NAME]['location'] = 'eu-west-1'
        self.write_main_and_sub_deployment_resources()

        with self.assertRaises(AssertionError) as context:
            self.dispatch(resources_meta={})
        self.assertEqual(str(context.exception),
                         "Error! Two resources with equal names were found! "
                         "Name: {0}. Please, rename one of them. First "
                         "resource: {1}. Second resource: {2}".format(
                             self.RESOURCE_NAME,
                             self.MAIN_D_R[self.RESOURCE_NAME],
                             self.SUB_D_R[self.RESOURCE_NAME]))
