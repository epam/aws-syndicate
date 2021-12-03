import json
import os
from pathlib import Path

from syndicate.core.constants import RESOURCES_FILE_NAME
from tests.test_building_meta import TestBuildingMeta


class TestApiGatewayCompressionSize(TestBuildingMeta):
    def setUp(self) -> None:
        super().setUp()
        self.main_d_r = {
            "test_api": {
                "resource_name": "test_api",
                "dependencies": [],
                "resource_type": "api_gateway",
                "deploy_stage": "test",
                "authorizers": {},
                "resources": {},
                "minimum_compression_size": 400
            }
        }
        self.sub_d_r = {
            "test_api": {
                "resource_name": "test_api",
                "dependencies": [],
                "resource_type": "api_gateway",
                "deploy_stage": "test",
                "authorizers": {},
                "resources": {},
                "minimum_compression_size": 300
            }
        }

    def test_resolving_compression_size_main(self):
        # compression size must be taken
        # rightly from MAIN deployment_resouces.json
        self.write_json_to_tmp(RESOURCES_FILE_NAME, self.main_d_r)
        self.write_json_to_tmp(Path('sub_path', RESOURCES_FILE_NAME),
                               self.sub_d_r)
        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertEqual(
            resources_meta['test_api']['minimum_compression_size'], 400)

    def test_resolving_compression_size_main_does_not_exist(self):
        self.main_d_r["test_api"].pop('minimum_compression_size')

        self.write_json_to_tmp(RESOURCES_FILE_NAME, self.main_d_r)
        self.write_json_to_tmp(Path('sub_path', RESOURCES_FILE_NAME),
                               self.sub_d_r)

        resource_meta = {}
        self.dispatch(resource_meta)
        self.assertEqual(
            resource_meta['test_api']['minimum_compression_size'], 300)

    def test_resolving_compression_size_does_not_exist(self):
        self.main_d_r['test_api'].pop('minimum_compression_size')
        self.sub_d_r['test_api'].pop('minimum_compression_size')

        self.write_json_to_tmp(RESOURCES_FILE_NAME, self.main_d_r)
        self.write_json_to_tmp(Path('sub_path', RESOURCES_FILE_NAME),
                               self.sub_d_r)
        resource_meta = {}
        self.dispatch(resource_meta)
        self.assertNotIn('minimum_compression_size',
                         resource_meta['test_api'])
