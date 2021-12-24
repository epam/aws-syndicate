from pathlib import Path

from syndicate.core.generators import _mkdir, _write_content_to_file
from syndicate.core.generators.contents import PYTHON_TESTS_INIT_CONTENT, \
    PYTHON_TESTS_INIT_LAMBDA_TEMPLATE, PYTHON_TESTS_BASIC_TEST_CASE_TEMPLATE
from syndicate.core.helper import string_to_capitalized_camel_case

PYTHON_TESTS_DIR = 'tests'
PYTHON_BASIC_TEST_CASE_FILE = 'test_success.py'


class PythonTestsGenerator:
    def __init__(self, project_path: str, lambda_name: str):
        self.project_path = project_path
        self.lambda_name = lambda_name
        self.processed_name = self.lambda_name.replace("-", "_")
        self.test_lambda_folder = f'test_{self.processed_name.lower()}'
        self.camel_lambda_name = string_to_capitalized_camel_case(
            self.processed_name)

    def generate(self):
        folder_path = Path(self.project_path, PYTHON_TESTS_DIR)
        init_path = Path(folder_path, '__init__.py')
        lambda_folder_path = Path(
            folder_path, self.test_lambda_folder)
        lambda_init_path = Path(lambda_folder_path, '__init__.py')
        lambda_basic_test_case_path = Path(lambda_folder_path,
                                           PYTHON_BASIC_TEST_CASE_FILE)

        _mkdir(folder_path, exist_ok=True)
        if not init_path.exists():
            _write_content_to_file(init_path, PYTHON_TESTS_INIT_CONTENT)
        _mkdir(lambda_folder_path, exist_ok=True)

        _write_content_to_file(
            lambda_init_path,
            PYTHON_TESTS_INIT_LAMBDA_TEMPLATE.format(
                lambda_name=self.lambda_name,
                camel_lambda_name=self.camel_lambda_name))

        _write_content_to_file(
            lambda_basic_test_case_path,
            PYTHON_TESTS_BASIC_TEST_CASE_TEMPLATE.format(
                test_lambda_folder=self.test_lambda_folder,
                camel_lambda_name=self.camel_lambda_name))


def _generate_python_tests(project_path, lambda_name):
    PythonTestsGenerator(project_path, lambda_name).generate()
