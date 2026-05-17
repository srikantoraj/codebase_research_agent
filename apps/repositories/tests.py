from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings

from apps.repositories.exceptions import InvalidRepositoryURLError
from apps.repositories.models import RepositorySourceType
from apps.repositories.services import RepositoryService


class RepositoryServiceTests(TestCase):
    def test_parse_https_github_url(self):
        data = RepositoryService.parse_github_url("https://github.com/tiangolo/fastapi")

        self.assertEqual(data["owner"], "tiangolo")
        self.assertEqual(data["name"], "fastapi")
        self.assertEqual(data["canonical_url"], "https://github.com/tiangolo/fastapi")
        self.assertEqual(data["clone_url"], "https://github.com/tiangolo/fastapi.git")

    def test_parse_ssh_github_url(self):
        data = RepositoryService.parse_github_url("git@github.com:celery/celery.git")

        self.assertEqual(data["owner"], "celery")
        self.assertEqual(data["name"], "celery")
        self.assertEqual(data["canonical_url"], "https://github.com/celery/celery")

    def test_invalid_repository_url(self):
        with self.assertRaises(InvalidRepositoryURLError):
            RepositoryService.parse_github_url("https://gitlab.com/example/repo")

    def test_create_local_repository(self):
        with TemporaryDirectory() as tmp_dir:
            repo = RepositoryService.get_or_create_from_local_path(tmp_dir)

            self.assertEqual(repo.source_type, RepositorySourceType.LOCAL)
            self.assertEqual(repo.local_path, str(Path(tmp_dir).resolve()))

    def test_count_source_files_ignores_common_generated_dirs(self):
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "app.py").write_text("print('hello')")
            (root / "README.md").write_text("demo")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "ignored.js").write_text("console.log('ignored')")

            self.assertEqual(RepositoryService.count_source_files(root), 2)
