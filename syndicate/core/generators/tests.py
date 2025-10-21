from pathlib import Path

from syndicate.core.generators import _mkdir, _write_content_to_file
from syndicate.core.generators.contents import PYTHON_TESTS_INIT_CONTENT, \
    PYTHON_TESTS_INIT_LAMBDA_TEMPLATE, PYTHON_TESTS_BASIC_TEST_CASE_TEMPLATE
from syndicate.core.helper import string_to_capitalized_camel_case

PYTHON_TESTS_DIR = 'tests'
PYTHON_BASIC_TEST_CASE_FILE = 'test_success.py'


def _generate_python_tests(
    runtime_abs_path: str, 
    lambda_name: str
) -> None:
    """
    Generate Python test files for a lambda function.
    
    :parameter runtime_abs_path: Path to the runtime root directory
    :parameter lambda_name: Name of the lambda function
    """
    processed_name = lambda_name.replace("-", "_")
    test_lambda_folder = f'test_{processed_name.lower()}'
    camel_lambda_name = string_to_capitalized_camel_case(processed_name)
    
    _mkdir(runtime_abs_path, exist_ok=True)

    tests_folder_path = Path(runtime_abs_path, PYTHON_TESTS_DIR)
    init_path = Path(tests_folder_path, '__init__.py')
    lambda_folder_path = Path(tests_folder_path, test_lambda_folder)
    lambda_init_path = Path(lambda_folder_path, '__init__.py')
    lambda_basic_test_case_path = Path(lambda_folder_path, PYTHON_BASIC_TEST_CASE_FILE)

    _mkdir(tests_folder_path, exist_ok=True)
    if not init_path.exists():
        _write_content_to_file(init_path, PYTHON_TESTS_INIT_CONTENT)
    _mkdir(lambda_folder_path, exist_ok=True)

    _write_content_to_file(
        lambda_init_path,
        PYTHON_TESTS_INIT_LAMBDA_TEMPLATE.format(
            lambda_name=lambda_name,
            camel_lambda_name=camel_lambda_name
        )
    )

    _write_content_to_file(
        lambda_basic_test_case_path,
        PYTHON_TESTS_BASIC_TEST_CASE_TEMPLATE.format(
            test_lambda_folder=test_lambda_folder,
            camel_lambda_name=camel_lambda_name
        )
    )
