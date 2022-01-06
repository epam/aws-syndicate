import os.path
import pathlib
import shutil
import subprocess
from os import environ
from unittest import TestCase

import yaml

from all_syndicate_flow.flow import SyndicateFlow
from tests.integration_tests.tests_create_deploy_target_bucket.fixtures_for_files import \
    BOTO3_INIT, BOTO3_SESSION, BOTO3_DYNAMODB_CONDITIONS, SDCT_CONFIG

PATH_TO_ROOT = pathlib.Path().absolute().parent.parent.parent
PATH_TO_SYNDICATE = os.path.join(PATH_TO_ROOT, "dir_for_proj")
SDCT_CONF = os.path.join(PATH_TO_SYNDICATE, ".syndicate-config-config")

NAME_OF_BUCKET_FOR_TESTS = "testing-bucket"


def create_file_boto3():
    """
    Creates needed for mock boto3 files
    """

    os.mkdir(os.path.join(PATH_TO_SYNDICATE, "boto3"))
    os.mkdir(os.path.join(PATH_TO_SYNDICATE, "boto3", "dynamodb"))

    with open(os.path.join(PATH_TO_SYNDICATE, "boto3", "__init__.py"),
              "w") as file:
        file.write(BOTO3_INIT)
    with open(os.path.join(PATH_TO_SYNDICATE, "boto3", "session.py"),
              "w") as file:
        file.write(BOTO3_SESSION)
    with open(os.path.join(PATH_TO_SYNDICATE, "boto3", "dynamodb",
                           "conditions.py"),
              "w") as file:
        file.write(BOTO3_DYNAMODB_CONDITIONS)


def generate_config():
    with open(os.path.join(SDCT_CONF, "sdct.conf"), 'w') as file:
        path_to_proj = f"project_path={PATH_TO_SYNDICATE}"
        bucket = f"deploy_target_bucket={NAME_OF_BUCKET_FOR_TESTS}"
        content = SDCT_CONFIG
        content += f"\n{path_to_proj}\n{bucket}"
        file.write(content)


def delete_files(folder):
    print(f"will be deleted {folder}")
    _input = input("y/n\n")
    if _input == "y":
        try:
            shutil.rmtree(folder)
        except FileNotFoundError:
            f"Some error with removing {folder}"


class TestGenerateProject(TestCase):

    def setUp(self) -> None:
        """Method creates file boto3.py to mock some calls to AWS"""
        super().setUp()
        self.sf = SyndicateFlow(path_to_proj_dir=PATH_TO_SYNDICATE,
                                name_bucket_for_tests="testing-bucket",
                                project_name="dir_for_proj")

        self.sf.syndicate_health_check()
        self.sf.create_config_file()
        self.sf.generate_project()
        self.sf.generate_config()

        create_file_boto3()

        self.envvars = environ.copy()
        self.envvars.update({
            "SDCT_CONF": SDCT_CONF})
        self.command = "syndicate create_deploy_target_bucket".split()

    def tearDown(self) -> None:
        delete_files(PATH_TO_SYNDICATE)

    def test_create_bucket(self):
        """
        1. Mocked boto3 lib (created directory with mocked classes in
        PATH_TO_SYNDICATE)
        2. Run subprocess with self.command
        3. Get output from subprocess
        4. Check that needed keys were provided in request to boto3
        """

        with subprocess.Popen(self.command,
                              env=self.envvars,
                              stdout=subprocess.PIPE,
                              stdin=subprocess.PIPE,
                              stderr=subprocess.STDOUT) as proc:
            res = proc.stdout.read().decode()
            name_of_bucket = self.get_name_of_bucket()
            sp_res = res.split("\n")

            for call in sp_res:
                if "mock().meta.client" in call and "create_bucket" in call:
                    self.assertIn("LocationConstraint", call)
                    self.assertIn(name_of_bucket, call)
                    self.assertIn("Bucket", call)

    @staticmethod
    def get_name_of_bucket():
        with open(os.path.join(SDCT_CONF, "syndicate.yml"), "r") as file:
            dict_file = yaml.safe_load(file)
            return dict_file.get("deploy_target_bucket")
