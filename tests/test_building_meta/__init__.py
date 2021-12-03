import os
import shutil
import tempfile
import unittest
from pathlib import Path

from syndicate.core.build.meta_processor import _look_for_configs


class TestBuildingMeta(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle_name = 'bundle_name'
        self.testing_sub_dir = 'syndicate_tests'
        self.TMP_FOLDER = Path(tempfile.gettempdir(), self.testing_sub_dir)
        os.makedirs(self.TMP_FOLDER, exist_ok=True)

    def tearDown(self) -> None:
        try:
            shutil.rmtree(self.TMP_FOLDER)
        except OSError:
            pass

    def dispatch(self, resources_meta):
        for path, _, nested_items in os.walk(self.TMP_FOLDER):
            _look_for_configs(nested_items, resources_meta, path,
                              self.bundle_name)
