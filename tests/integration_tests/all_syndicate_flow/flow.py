import os
import pathlib
import shutil
import subprocess
import sys
from pathlib import Path

from tests.integration_tests.tests_create_deploy_target_bucket \
    .fixtures_for_files import \
    SDCT_CONFIG

PATH_TO_ROOT = pathlib.Path().absolute().parent.parent.parent


class SyndicateFlow:

    def __init__(self, path_to_proj_dir,
                 name_bucket_for_tests, project_name,
                 lambda_name="lambda_for_tests", runtime_lambda="python"):
        self.sdct_conf_dir = os.path.join(path_to_proj_dir,
                                          ".syndicate-config-config")
        self.path_to_proj_dir = path_to_proj_dir
        self.name_bucket_for_tests = name_bucket_for_tests
        self.project_name = project_name
        self.lambda_name = lambda_name
        self.runtime_lambda = runtime_lambda

        self.env_vars = os.environ
        self.env_vars.update({"SDCT_CONF": self.sdct_conf_dir})

    @staticmethod
    def syndicate_health_check():
        command = "syndicate --help".split()
        with subprocess.Popen(command,
                              stdout=subprocess.PIPE,
                              stdin=subprocess.PIPE,
                              stderr=subprocess.STDOUT) as proc:
            return proc.stdout.read().decode()

    def create_config_file(self, content_for_syndicate=""):
        try:
            Path(self.sdct_conf_dir).mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            print(f"{self.sdct_conf_dir} dir is already exist. Are you "
                  f"confirm that it count be overwritten?")
            _input = input("y/n\n")
            if _input.lower() == "n" or _input.lower() == "no":
                sys.exit()
        with open(os.path.join(self.sdct_conf_dir, "sdct.conf"),
                  'w') as file:
            path_to_proj = f"project_path={self.path_to_proj_dir}"
            bucket = f"deploy_target_bucket={self.name_bucket_for_tests}"
            content = SDCT_CONFIG
            content += f"\n{path_to_proj}\n{bucket}"
            file.write(content)
            print("success creating sdct.conf")
        with open(os.path.join(self.path_to_proj_dir, ".syndicate"),
                  'w') as file:
            file.write(content_for_syndicate)

    def generate_project(self):
        pp = PATH_TO_ROOT
        p2 = self.project_name
        command = f"syndicate generate project --name {p2} " \
                  f"--path {pp}".split()

        with subprocess.Popen(command,
                              env=self.env_vars,
                              stdout=subprocess.PIPE,
                              stdin=subprocess.PIPE,
                              stderr=subprocess.STDOUT) as proc:
            res = proc.communicate(b"n")
            print(res[0].decode())

    def generate_config(self):
        command = f"syndicate generate config --name config " \
                  f"--region eu-central-1 " \
                  f"--bundle_bucket_name {self.name_bucket_for_tests} " \
                  f"--project_path {self.path_to_proj_dir}".split()

        with subprocess.Popen(command,
                              cwd=self.path_to_proj_dir,
                              env=self.env_vars,
                              stdout=subprocess.PIPE,
                              stdin=subprocess.PIPE,
                              stderr=subprocess.STDOUT) as proc:
            print(proc.stdout.read().decode())

    def delete_files(self):
        delete_syndicate_files(self.path_to_proj_dir)

    def generate_lambda(self):
        _runtime = self.runtime_lambda
        _project_path = self.path_to_proj_dir
        _lambda_name = self.lambda_name

        command = f"syndicate generate lambda --name {_lambda_name} " \
                  f"--runtime {_runtime} " \
                  f"--project_path {_project_path}".split()

        with subprocess.Popen(command,
                              cwd=self.path_to_proj_dir,
                              env=self.env_vars,
                              stdout=subprocess.PIPE,
                              stdin=subprocess.PIPE,
                              stderr=subprocess.STDOUT) as proc:
            print(proc.stdout.read().decode())


def delete_file(path_to_file):
    os.remove(path_to_file)


def delete_syndicate_files(folder):
    print(f"will be deleted {folder}")
    _input = input("y/n\n")
    if _input == "y":
        try:
            shutil.rmtree(folder)
        except FileNotFoundError:
            f"Some error with removing {folder}"
