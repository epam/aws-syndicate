import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from syndicate.core.build.meta_processor import _look_for_configs
from syndicate.core.constants import RESOURCES_FILE_NAME


class TestBuildingMeta(unittest.TestCase):
    MAIN_D_R = None
    SUB_D_R = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.testing_sub_dir = 'syndicate_tests'
        cls.TMP_FOLDER = Path(tempfile.gettempdir(), cls.testing_sub_dir)
        os.makedirs(cls.TMP_FOLDER, exist_ok=True)

    def setUp(self) -> None:
        self.bundle_name = 'bundle_name'

        if not self.MAIN_D_R or \
                not self.SUB_D_R:
            raise AssertionError("MAIN_DEPLOYMENT_RESOURCES and "
                                 "SUB_DEPLOYMENT_RESOURCES must be specified")

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            shutil.rmtree(cls.TMP_FOLDER)
        except OSError:
            pass

    def dispatch(self, resources_meta):
        for path, _, nested_items in os.walk(self.TMP_FOLDER):
            _look_for_configs(nested_items, resources_meta, path,
                              self.bundle_name)

    def write_json_to_tmp(self, filename, data: dict):
        path = Path(self.TMP_FOLDER, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as file:
            json.dump(data, file)

    def write_main_and_sub_deployment_resources(self):
        self.write_json_to_tmp(RESOURCES_FILE_NAME, self.MAIN_D_R)
        self.write_json_to_tmp(Path('sub_path', RESOURCES_FILE_NAME),
                               self.SUB_D_R)
