import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from syndicate.core.generators.project import generate_project_structure


class TestProjectGenerator(unittest.TestCase):

    def test_python_standard_template_creates_agent_ready_project(self):
        with tempfile.TemporaryDirectory() as parent:
            generate_project_structure(
                project_name='Orders API',
                project_path=parent,
                template='python-standard',
            )

            project = Path(parent) / 'Orders API'
            expected_files = (
                'AGENTS.md',
                'README.md',
                'CHANGELOG.md',
                'pyproject.toml',
                '.python-version',
                'docs/architecture.md',
                'skills/verify-project/SKILL.md',
                'tests/unit/test_scaffold.py',
            )

            for relative_path in expected_files:
                with self.subTest(relative_path=relative_path):
                    self.assertTrue((project / relative_path).is_file())

            self.assertIn(
                '# Orders API',
                (project / 'README.md').read_text(encoding='utf-8'),
            )
            self.assertIn(
                'name = "orders-api"',
                (project / 'pyproject.toml').read_text(encoding='utf-8'),
            )
            self.assertTrue((project / 'lambdas').is_dir())
            self.assertTrue((project / 'commons').is_dir())

    def test_legacy_template_remains_the_default(self):
        with tempfile.TemporaryDirectory() as parent:
            generate_project_structure(
                project_name='legacy-project',
                project_path=parent,
            )

            project = Path(parent) / 'legacy-project'
            self.assertTrue((project / 'README.md').is_file())
            self.assertTrue((project / 'deployment_resources.json').is_file())
            self.assertFalse((project / 'AGENTS.md').exists())

    def test_declining_overwrite_does_not_modify_existing_project(self):
        with tempfile.TemporaryDirectory() as parent:
            project = Path(parent) / 'existing-project'
            project.mkdir()
            readme = project / 'README.md'
            readme.write_text('keep this content', encoding='utf-8')

            with patch('builtins.input', return_value='n'):
                result = generate_project_structure(
                    project_name='existing-project',
                    project_path=parent,
                )

            self.assertEqual(result, 2)
            self.assertEqual(
                readme.read_text(encoding='utf-8'),
                'keep this content',
            )
            self.assertFalse((project / 'deployment_resources.json').exists())


if __name__ == '__main__':
    unittest.main()
