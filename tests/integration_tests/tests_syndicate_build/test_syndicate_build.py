import os.path
import pathlib
import shutil
import subprocess
from os import environ, listdir
from os.path import isfile
from unittest import TestCase

from tests.integration_tests.all_syndicate_flow.flow import SyndicateFlow
from tests.integration_tests.tests_syndicate_build.fixtures_for_files import \
    BOTO3_INIT, BOTO3_SESSION, BOTO3_DYNAMODB_CONDITIONS

PATH_TO_ROOT = pathlib.Path(__file__).absolute().parent.parent.parent.parent

PATH_TO_SYNDICATE_PROJ = os.path.join(PATH_TO_ROOT, "dir_for_proj")
SDCT_CONF = os.path.join(PATH_TO_SYNDICATE_PROJ, ".syndicate-config-config")
PATH_TO_BOTO3 = os.path.join(PATH_TO_ROOT, "boto3")

NAME_OF_BUCKET_FOR_TESTS = "testing-bucket"


def create_file_boto3():
    """
    Creates needed for mock boto3 files
    """

    os.mkdir(os.path.join(PATH_TO_ROOT, "boto3"))
    os.mkdir(os.path.join(PATH_TO_ROOT, "boto3", "dynamodb"))

    with open(os.path.join(PATH_TO_ROOT, "boto3", "__init__.py"),
              "w") as file:
        file.write(BOTO3_INIT)
    with open(os.path.join(PATH_TO_ROOT, "boto3", "session.py"),
              "w") as file:
        file.write(BOTO3_SESSION)
    with open(os.path.join(PATH_TO_ROOT, "boto3", "dynamodb",
                           "conditions.py"),
              "w") as file:
        file.write(BOTO3_DYNAMODB_CONDITIONS)


def delete_files(folder):
    print(f"will be deleted {folder}")
    _input = input("y/n\n")
    if _input == "y":
        try:
            shutil.rmtree(folder)
        except FileNotFoundError:
            f"Some error with removing {folder}"


def resolve_path_to_zip_and_meta():
    _path = os.path.join(SDCT_CONF, "bundles")

    folder_where_needed_files = listdir(_path)[0]
    return os.path.join(_path, folder_where_needed_files)


class TestBuild(TestCase):

    def setUp(self) -> None:
        """Method creates file boto3.py to mock some calls to AWS"""
        super().setUp()
        self.sf = SyndicateFlow(path_to_proj_dir=PATH_TO_SYNDICATE_PROJ,
                                name_bucket_for_tests="testing-bucket",
                                project_name="dir_for_proj")

        self.sf.syndicate_health_check()
        self.sf.create_config_file()
        self.sf.generate_project()
        self.sf.generate_config()
        self.sf.generate_lambda()

        create_file_boto3()

        my_env = {'PYTHONPATH': PATH_TO_ROOT}

        self.envvars = environ.copy()
        self.envvars.update({
            "SDCT_CONF": SDCT_CONF})

        self.envvars.update(my_env)

        self.command = "syndicate build".split()

    def tearDown(self) -> None:
        delete_files(PATH_TO_SYNDICATE_PROJ)
        delete_files(PATH_TO_BOTO3)

    def test_syndicate_build(self):
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

            self.assertIn("Bundle was uploaded successfully", str(res))

            needed_files = ["build_meta.json", ]

            path_to_zip_and_meta = resolve_path_to_zip_and_meta()

            files_from_created_dir = [f for f in listdir(
                path_to_zip_and_meta) if isfile(
                os.path.join(path_to_zip_and_meta, f))]

            self.assertIn("zip", str(files_from_created_dir))

            for file_name in needed_files:
                self.assertIn(file_name, files_from_created_dir)
