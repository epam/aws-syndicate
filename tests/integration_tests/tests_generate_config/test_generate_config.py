import os
import pathlib
import subprocess
from os import environ, listdir
from os.path import isfile, join
from unittest import TestCase

from tests.integration_tests.all_syndicate_flow.flow import \
    delete_syndicate_files, SyndicateFlow

PATH_TO_CONFIG = ".syndicate-config-config"
PATH_TO_ROOT = pathlib.Path(__file__).absolute().parent.parent.parent.parent


class TestGenerateProject(TestCase):
    """
    Testing flow of creating files and configs using subprocess module
    Must be set upped next:
    1. venv
    2. Installed syndicate (pip install -e .)
    """

    def setUp(self) -> None:
        super().setUp()
        self.envvars = environ.copy()
        self.path = os.path.join(PATH_TO_ROOT, "dir_for_project")
        self.project_name = "testing"
        self.path_where_should_be_config = os.path.join(self.path,
                                                        PATH_TO_CONFIG)
        self.command = f"syndicate generate project --name " \
                       f"{self.project_name} --path {self.path}".split()
        self.name_bucket_for_tests = "name-bucket-for-tests"

        self.sf = SyndicateFlow(path_to_proj_dir=self.path,
                                name_bucket_for_tests="testing-bucket",
                                project_name="testing-project")
        self.sf.create_config_file()

        self.command = f"syndicate generate config --name config " \
                       f"--region eu-central-1 " \
                       f"--bundle_bucket_name {self.name_bucket_for_tests} " \
                       f"--project_path {self.path}".split()

    def tearDown(self) -> None:
        if not len(os.listdir(self.path)) == 0:
            """If directory is not empty"""
            delete_syndicate_files(self.path)
            """Creates directory for tests file for future"""

    def test_generate_config_success(self):
        with subprocess.Popen(self.command,
                              cwd=self.path,
                              env=self.envvars,
                              stdout=subprocess.PIPE,
                              stdin=subprocess.PIPE,
                              stderr=subprocess.STDOUT) as proc:
            print(proc.stdout.read().decode())
        only_files = [f for f in listdir(self.path_where_should_be_config)
                      if isfile(join(self.path_where_should_be_config, f))]

        needed_files = ['syndicate_aliases.yml', 'sdct.conf', 'syndicate.yml']
        for file_name in needed_files:
            self.assertIn(file_name, only_files)

    def test_generate_config_failed_of_wrong_bucket_name(self):
        wrong_bucket_name = "wrong__________name"

        wrong_command = f"syndicate generate config --name config " \
                        f"--region eu-central-1 " \
                        f"--bundle_bucket_name {wrong_bucket_name} " \
                        f"--project_path {self.path}".split()

        with subprocess.Popen(wrong_command,
                              cwd=self.path,
                              env=self.envvars,
                              stdout=subprocess.PIPE,
                              stdin=subprocess.PIPE,
                              stderr=subprocess.STDOUT) as proc:
            res = (proc.stdout.read().decode())

        self.assertIn(
            "Invalid value for '--bundle_bucket_name': Bucket name contains "
            "invalid characters:",
            res)
