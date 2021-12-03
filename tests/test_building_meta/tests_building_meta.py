import json
import os
from pathlib import Path

from syndicate.core.constants import RESOURCES_FILE_NAME
from tests.test_building_meta import TestBuildingMeta


class TestCompressionSize(TestBuildingMeta):
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
        with open(Path(self.TMP_FOLDER, RESOURCES_FILE_NAME), 'w') as file:
            json.dump(self.main_d_r, file)


        self.sub_path = Path(self.TMP_FOLDER, 'sub_path')
        os.makedirs(self.sub_path, exist_ok=True)
        with open(Path(self.sub_path, RESOURCES_FILE_NAME), 'w') as file:
            json.dump(self.sub_d_r, file)

    def test_resolving_compression_size(self):
        # compression size must be taken
        # rightly from MAIN deployment_resouces.json
        resources_meta = {}
        self.dispatch(resources_meta)
        self.assertEqual(
            resources_meta['test_api']['minimum_compression_size'], 400)
