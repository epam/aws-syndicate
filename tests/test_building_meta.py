import os
import unittest
from syndicate.core.build.meta_processor import _look_for_configs
from syndicate.core.constants import RESOURCES_FILE_NAME
import json
from pathlib import Path
import tempfile


class TestCompressionSize(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle_name = 'bundle_name'
        self.TMP_FOLDER = tempfile.gettempdir()
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


        self.sub_path = Path(self.TMP_FOLDER, 'syndicate_tests')
        os.makedirs(self.sub_path, exist_ok=True)
        with open(Path(self.sub_path, RESOURCES_FILE_NAME), 'w') as file:
            json.dump(self.sub_d_r, file)



    def tearDown(self) -> None:
        try:
            os.remove(Path(self.TMP_FOLDER, RESOURCES_FILE_NAME))
            os.remove(Path(self.sub_path, RESOURCES_FILE_NAME))
        except OSError:
            pass

    def test_resolving_compression_size(self):
        # must be rightly from MAIN deployment_resouces.json
        resources_meta = {}
        _look_for_configs([RESOURCES_FILE_NAME, ], resources_meta, self.TMP_FOLDER, self.bundle_name)
        _look_for_configs([RESOURCES_FILE_NAME, ], resources_meta, str(self.sub_path), self.bundle_name)
        self.assertEqual(resources_meta['test_api']['minimum_compression_size'], 400)
