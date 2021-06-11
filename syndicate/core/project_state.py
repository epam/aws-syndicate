"""
    Copyright 2018 EPAM Systems, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
import os

import yaml

STATE_NAME = 'name'
STATE_LAMBDAS = 'lambdas'

PROJECT_STATE_FILE = '.syndicate'


class ProjectState:

    def __init__(self, project_path):
        self.project_path = project_path
        self.state_path = os.path.join(project_path, PROJECT_STATE_FILE)
        self._dict = self.__load_project_state_file()

    @staticmethod
    def generate(project_path, project_name):
        project_state = dict(name=project_name, path=project_path)
        with open(os.path.join(project_path, PROJECT_STATE_FILE),
                  'w') as state_file:
            yaml.dump(project_state, state_file)
        return ProjectState(project_path=project_path)

    @staticmethod
    def check_if_project_state_exists(project_path):
        return os.path.exists(os.path.join(project_path, PROJECT_STATE_FILE))

    def __load_project_state_file(self):
        if not ProjectState.check_if_project_state_exists(self.project_path):
            raise AssertionError(
                f'There is not .syndicate file in {self.project_path}')
        with open(self.state_path) as state_file:
            return yaml.safe_load(state_file.read())

    def save(self):
        with open(self.state_path, 'w') as state_file:
            yaml.dump(self._dict, state_file)

    @property
    def name(self):
        return self._dict.get(STATE_NAME)

    def set_name(self, name):
        return self._dict.update({STATE_NAME: name})

    @property
    def lambdas(self):
        lambdas = self._dict.get(STATE_LAMBDAS)
        if not lambdas:
            return dict()
        return lambdas

    def add_lambda(self, lambda_name, runtime):
        lambdas = self._dict.get(STATE_LAMBDAS)
        if not lambdas:
            lambdas = dict()
            self._dict.update(STATE_LAMBDAS, lambdas)
        lambdas.update({lambda_name: {'runtime': runtime}})
