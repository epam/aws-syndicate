import os
import shutil
import tempfile
import unittest
from pathlib import Path


class TestBuildingMeta(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle_name = 'bundle_name'
        self.testing_sub_dir = 'syndicate_tests'
        self.TMP_FOLDER = Path(tempfile.gettempdir(), self.testing_sub_dir)
        os.makedirs(self.TMP_FOLDER, exist_ok=True)

    def tearDown(self) -> None:
        breakpoint()
        try:
            shutil.rmtree(self.TMP_FOLDER)
        except OSError:
            pass
