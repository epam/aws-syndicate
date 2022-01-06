import os
import pathlib
import subprocess
import uuid
from os import environ, listdir
from unittest import TestCase

from tests.integration_tests.all_syndicate_flow.flow import \
    delete_syndicate_files

PATH_TO_CONFIG = "/.syndicate-config-config"
PATH_TO_TESTS = pathlib.Path().absolute().parent


class TestGenerateProject(TestCase):
    """
    Testing flow of creating config files using subprocess module
    Must be set upped next:
    1. venv
    2. Installed syndicate (pip install -e .)
    """

    def setUp(self) -> None:
        super().setUp()
        self.envvars = environ.copy()
        self.path = os.path.join(PATH_TO_TESTS, "project_path_for_tests")
        self.project_name = "testing"
        self.path_where_should_be_config = os.path.join(self.path,
                                                        self.project_name)
        self.command = self.generate_command(
            f"syndicate generate project --name {self.project_name} --path"
            f" {self.path}")

    def tearDown(self) -> None:
        if not len(os.listdir(self.path)) == 0:
            """If directory is not empty"""
            delete_syndicate_files(self.path)
            """Creates directory for tests file for future"""
            os.mkdir(self.path)
            with open(os.path.join(self.path, "__init__.py"), "w") as file:
                file.write("")

    def testing_generate_project_empty(self):
        """
        Generate config in empty folder
        """

        with subprocess.Popen(self.command,
                              env=self.envvars,
                              stdout=subprocess.PIPE,
                              stdin=subprocess.PIPE,
                              stderr=subprocess.STDOUT) as proc:
            print("Output when run testing_generate_project_empty - ",
                  proc.stdout.read())
            proc.stdout.close()

            files = self.get_all_from(self.path_where_should_be_config)

            required_files = ['.gitignore', 'CHANGELOG.md',
                              'deployment_resources.json', '.syndicate',
                              'README.md']
            for file in files:
                self.assertIn(file, required_files)

    def test_generate_config_non_empty_not_changed(self):
        """
        Testing generate config when not empty and not override
        1. Create command that will generate config
        2.
        """
        param_to_overwrite = b"n"

        path_to_file = os.path.join(self.path_where_should_be_config,
                                    'deployment_resources.json')

        with subprocess.Popen(self.command, env=self.envvars):
            pass

        with open(path_to_file, "w") as file:
            string_to_test = str(uuid.uuid4())
            file.write(string_to_test)

        content_of_file_1 = self.get_file_content(path_to_file)

        with subprocess.Popen(self.command,
                              env=self.envvars,
                              stdout=subprocess.PIPE,
                              stdin=subprocess.PIPE,
                              stderr=subprocess.STDOUT) as proc:
            proc.stdin.write(param_to_overwrite)
            proc.stdin.close()

        content_of_file_2 = self.get_file_content(path_to_file)

        self.assertEqual(content_of_file_2, content_of_file_1)

    def test_generate_config_non_empty_changed(self):
        """
        Testing generate config when not empty and not override
        1. Create command that will generate config
        2.
        """
        param_to_overwrite = b"y"

        path_to_file = os.path.join(self.path_where_should_be_config,
                                    'deployment_resources.json')

        with subprocess.Popen(self.command, env=self.envvars):
            pass

        with open(path_to_file, "w") as file:
            string_to_test = str(uuid.uuid4())
            file.write(string_to_test)

        content_of_file_1 = self.get_file_content(path_to_file)

        with subprocess.Popen(self.command,
                              env=self.envvars,
                              stdout=subprocess.PIPE,
                              stdin=subprocess.PIPE,
                              stderr=subprocess.STDOUT) as proc:
            proc.communicate(param_to_overwrite)

        content_of_file_2 = self.get_file_content(path_to_file)

        self.assertNotEqual(content_of_file_2, content_of_file_1)

    @staticmethod
    def generate_command(param):
        command = param.split()
        return command

    @staticmethod
    def get_all_from(folder):
        return [f for f in listdir(folder)]

    @staticmethod
    def get_file_content(path_to_file):
        with open(path_to_file, 'r+') as file:
            content = file.read()
        return content
