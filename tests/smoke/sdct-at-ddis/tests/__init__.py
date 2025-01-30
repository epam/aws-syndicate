import sys
from pathlib import Path

SOURCE_FOLDER = 'src'


class ImportFromSourceContext:
    """Context object to import lambdas and packages. It's necessary because
    root path is not the path to the syndicate project but the path where
    lambdas are accumulated - SOURCE_FOLDER """

    def __init__(self, source_folder=SOURCE_FOLDER):
        self.source_folder = source_folder
        self.assert_source_path_exists()

    @property
    def project_path(self) -> Path:
        return Path(__file__).parent.parent

    @property
    def source_path(self) -> Path:
        return Path(self.project_path, self.source_folder)

    def assert_source_path_exists(self):
        source_path = self.source_path
        if not source_path.exists():
            print(f'Source path "{source_path}" does not exist.',
                  file=sys.stderr)
            sys.exit(1)

    def _add_source_to_path(self):
        source_path = str(self.source_path)
        if source_path not in sys.path:
            sys.path.append(source_path)

    def _remove_source_from_path(self):
        source_path = str(self.source_path)
        if source_path in sys.path:
            sys.path.remove(source_path)

    def __enter__(self):
        self._add_source_to_path()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._remove_source_from_path()

