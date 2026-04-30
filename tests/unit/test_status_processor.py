import unittest
from unittest.mock import patch

from syndicate.core.project_state.status_processor import (
    _group_by_type,
    _collect_deployed_resource_names,
    process_resources_view,
    DEPLOYED_MARKER,
    UNDEPLOYED_MARKER,
)


class TestGroupByType(unittest.TestCase):

    def test_groups_correctly(self):
        resources = {
            'func1': {'resource_type': 'lambda', 'runtime': 'python3.10'},
            'func2': {'resource_type': 'lambda', 'runtime': 'python3.10'},
            'my-api': {'resource_type': 'api_gateway'},
            'my-table': {'resource_type': 'dynamodb_table'},
        }
        grouped = _group_by_type(resources)

        self.assertEqual(len(grouped['lambda']), 2)
        self.assertEqual(len(grouped['api_gateway']), 1)
        self.assertEqual(len(grouped['dynamodb_table']), 1)

    def test_empty_resources(self):
        self.assertEqual(_group_by_type({}), {})


class TestCollectDeployedResources(unittest.TestCase):

    @patch('syndicate.core.project_state.status_processor'
           '.load_latest_deploy_output')
    def test_extracts_names_from_output(self, mock_load):
        mock_load.return_value = (True, {
            'arn:aws:lambda:us-east-1:123:function:func1': {
                'resource_name': 'func1',
                'resource_meta': {'resource_type': 'lambda'}
            },
            'arn:aws:apigateway:us-east-1::/restapis/abc': {
                'resource_name': 'my-api',
                'resource_meta': {'resource_type': 'api_gateway'}
            },
        })

        result = _collect_deployed_resource_names()
        self.assertEqual(result, {'func1', 'my-api'})

    @patch('syndicate.core.project_state.status_processor'
           '.load_latest_deploy_output')
    def test_no_deploy_output(self, mock_load):
        mock_load.return_value = (None, False)
        result = _collect_deployed_resource_names()
        self.assertEqual(result, set())


class TestProcessResourcesView(unittest.TestCase):

    @patch('syndicate.core.project_state.status_processor'
           '._collect_deployed_resource_names')
    @patch('syndicate.core.project_state.status_processor'
           '._collect_project_resources')
    @patch('syndicate.core.PROJECT_STATE')
    def test_marks_deployed_resources(self, mock_state,
                                      mock_collect, mock_deployed):
        mock_state.name = 'test-project'
        mock_collect.return_value = {
            'func1': {'resource_type': 'lambda',
                      'runtime': 'python3.10'},
            'func2': {'resource_type': 'lambda',
                      'runtime': 'python3.10'},
        }
        mock_deployed.return_value = {'func1'}

        result = process_resources_view()

        self.assertIn('func1', result)
        self.assertIn(DEPLOYED_MARKER, result)
        self.assertIn('func2', result)
        self.assertIn(UNDEPLOYED_MARKER, result)
        self.assertIn('1/2', result)

    @patch('syndicate.core.project_state.status_processor'
           '._collect_deployed_resource_names')
    @patch('syndicate.core.project_state.status_processor'
           '._collect_project_resources')
    @patch('syndicate.core.PROJECT_STATE')
    def test_deployed_only_filter(self, mock_state,
                                  mock_collect, mock_deployed):
        mock_state.name = 'test-project'
        mock_collect.return_value = {
            'func1': {'resource_type': 'lambda',
                      'runtime': 'python3.10'},
            'func2': {'resource_type': 'lambda',
                      'runtime': 'python3.10'},
        }
        mock_deployed.return_value = {'func1'}

        result = process_resources_view(deployed_only=True)

        self.assertIn('func1', result)
        self.assertNotIn('func2', result)

    @patch('syndicate.core.project_state.status_processor'
           '._collect_deployed_resource_names')
    @patch('syndicate.core.project_state.status_processor'
           '._collect_project_resources')
    @patch('syndicate.core.PROJECT_STATE')
    def test_no_resources(self, mock_state, mock_collect,
                          mock_deployed):
        mock_state.name = 'test-project'
        mock_collect.return_value = {}
        mock_deployed.return_value = set()

        result = process_resources_view()
        self.assertIn('No resources found', result)


if __name__ == '__main__':
    unittest.main()
