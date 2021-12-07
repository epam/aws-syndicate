import os
import shutil
import subprocess
import time
import unittest
import uuid
from os import environ, listdir
from os.path import isfile, join
from unittest import TestCase

PATH_TO_CONFIG = "/home/oleksandr_hrechenko/PycharmProjects/aws-syndicate/.syndicate-config-config"


# unittest.TestLoader.sortTestMethodsUsing = None  # this means that tests will run in correct order (first will be first, second - second, etc.)


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
        self.path = "/home/oleksandr_hrechenko/PycharmProjects/aws-syndicate" \
                    "/tests/integration_tests/project_path_for_tests"
        self.project_name = "testing"
        self.path_where_should_be_config = os.path.join(self.path,
                                                        self.project_name)
        self.command = self.generate_command(
            f"syndicate generate project --name {self.project_name} --path"
            f" {self.path}")

    def tearDown(self) -> None:
        if not len(os.listdir(self.path)) == 0:
            """If directory is not empty"""
            self.delete_all_files_in(self.path)

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
    def delete_all_files_in(folder):
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if "__init__.py" in file_path:
                    continue
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

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
