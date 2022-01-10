import os
import pathlib
import subprocess
from os import environ, listdir
from os.path import isfile
from unittest import TestCase

from tests.integration_tests.all_syndicate_flow.flow import SyndicateFlow, \
    delete_syndicate_files

PATH_TO_CONFIG = ".syndicate-config-config"
PATH_TO_ROOT = pathlib.Path(__file__).absolute().parent.parent.parent.parent


class TestGenerateLambda(TestCase):
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
                                project_name="dir_for_project")
        path_to_insert_in_file = os.path.join(self.path, "testing-project")
        self.sf.create_config_file(
            content_for_syndicate=f"""project_path: {path_to_insert_in_file}
account_id: 98989
name: some_name_for_java_lambda""")
        self.sf.generate_project()
        self.sf.generate_config()

        self.name_of_lambda = "test-lam-name"
        self.runtime = "python"

        self.command = f"syndicate generate lambda " \
                       f"--name {self.name_of_lambda} " \
                       f"--runtime {self.runtime}".split()

    def tearDown(self) -> None:
        if not len(os.listdir(self.path)) == 0:
            """If directory is not empty"""
            delete_syndicate_files(self.path)

    def test_generate_python_lambda_success(self):
        runtime_list = ["java", "python", "nodejs"]

        for _runtime in runtime_list:
            with self.subTest():
                self.command = f"syndicate generate lambda " \
                               f"--name {self.name_of_lambda} " \
                               f"--runtime {_runtime}".split()

                with subprocess.Popen(self.command,
                                      cwd=self.path,
                                      env=self.envvars,
                                      stdout=subprocess.PIPE,
                                      stdin=subprocess.PIPE,
                                      stderr=subprocess.STDOUT) as proc:
                    output = proc.stdout.read().decode()

                if _runtime == "java":
                    path_to_lam = os.path.join(self.path, "jsrc", "main",
                                               "java", "com", "dirforproject")

                    name_java_file = self.name_of_lambda.replace("_",
                                                                 " " "") \
                                         .replace("-", " ").title().replace(
                        " ", "") + ".java"

                    needed_files = [name_java_file]

                    files_where_lambda = [f for f in listdir(
                        path_to_lam) if isfile(os.path.join(path_to_lam, f))]

                    for file_name in needed_files:
                        self.assertIn(file_name, files_where_lambda)

                elif _runtime == "python":
                    path_where_lambda = os.path.join(self.path, "src",
                                                     "lambdas",
                                                     self.name_of_lambda)
                    path_where_commons = os.path.join(self.path, "src",
                                                      "commons")

                    files_where_lambda = [f for f in listdir(
                        path_where_lambda)
                                          if isfile(
                            os.path.join(path_where_lambda, f))]

                    files_where_common = [f for f in listdir(
                        path_where_commons)
                                          if isfile(
                            os.path.join(path_where_commons, f))]

                    files_where_common.extend(files_where_lambda)

                    needed_files = ['__init__.py', 'abstract_lambda.py',
                                    'exception.py',
                                    "log_helper.py",
                                    "deployment_resources.json",
                                    "handler.py", "lambda_config.json",
                                    "local_requirements.txt",
                                    "requirements.txt"]

                    for file_name in needed_files:
                        self.assertIn(file_name, files_where_common)

                    self.assertIn(
                        f"Lambda {self.name_of_lambda} has been successfully "
                        f"added to the project.", str(output))
                    self.assertIn(_runtime, output)

                elif _runtime == "nodejs":
                    path_to_lam = os.path.join(self.path, "app", "lambdas",
                                               self.name_of_lambda)

                    needed_files = ['index.js',
                                    "deployment_resources.json",
                                    "lambda_config.json",
                                    "package.json",
                                    "package-lock.json",
                                    ]

                    files_where_lambda = [f for f in listdir(
                        path_to_lam) if isfile(os.path.join(path_to_lam, f))]

                    for file_name in needed_files:
                        self.assertIn(file_name, files_where_lambda)

    def test_generate_lambda_with_invalid_permissions(self):

        invalid_path = "Cccc://"

        command = f"syndicate generate lambda " \
                  f"--name {self.name_of_lambda} " \
                  f"--runtime java " \
                  f"--project_path {invalid_path}".split()

        with subprocess.Popen(command,
                              cwd=self.path,
                              env=self.envvars,
                              stdout=subprocess.PIPE,
                              stdin=subprocess.PIPE,
                              stderr=subprocess.STDOUT) as proc:
            output = proc.stdout.read().decode()
        self.assertIn("Incorrect permissions for the provided path '{"
                      "project_path}'", output)

    def test_invalid_runtime(self):

        invalid_runtime = "solidity"

        command = f"syndicate generate lambda " \
                  f"--name {self.name_of_lambda} " \
                  f"--runtime {invalid_runtime}".split()

        with subprocess.Popen(command,
                              cwd=self.path,
                              env=self.envvars,
                              stdout=subprocess.PIPE,
                              stdin=subprocess.PIPE,
                              stderr=subprocess.STDOUT) as proc:
            output = proc.stdout.read().decode()

        self.assertIn(
            f"Invalid value for '--runtime': '{invalid_runtime}' is not one of "
            f"'java', 'nodejs', 'python'", output)
