import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.utils import ensure_directory
from apps.repositories.exceptions import (
    InvalidLocalRepositoryPathError,
    InvalidRepositoryURLError,
    RepositorySyncError,
)
from apps.repositories.models import (
    Repository,
    RepositorySourceType,
    RepositorySyncStatus,
)


class RepositoryService:
    """Service layer for repository validation, persistence, and sync."""

    GITHUB_HTTPS_RE = re.compile(
        r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<name>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
    )
    GITHUB_SSH_RE = re.compile(
        r"^git@github\.com:(?P<owner>[A-Za-z0-9_.-]+)/(?P<name>[A-Za-z0-9_.-]+?)(?:\.git)?$"
    )

    SOURCE_EXTENSIONS = {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".go",
        ".rs",
        ".php",
        ".rb",
        ".cs",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".swift",
        ".kt",
        ".sql",
        ".md",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".env.example",
    }

    IGNORED_DIRS = {
        ".git",
        "node_modules",
        "venv",
        ".venv",
        "env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        "coverage",
        ".next",
        ".turbo",
    }

    @classmethod
    def get_or_create_from_input(cls, repo_url=None, local_path=None, sync=True):
        """
        Create or retrieve a Repository from either GitHub URL or local path.
        Only one of repo_url/local_path should be supplied.
        """
        if repo_url and local_path:
            raise InvalidRepositoryURLError("Provide either repo_url or local_path, not both.")

        if repo_url:
            repository = cls.get_or_create_from_url(repo_url)
        elif local_path:
            repository = cls.get_or_create_from_local_path(local_path)
        else:
            raise InvalidRepositoryURLError("Either repo_url or local_path is required.")

        if sync:
            cls.sync(repository)

        return repository

    @classmethod
    def parse_github_url(cls, repo_url):
        """
        Parse a GitHub HTTPS or SSH repository URL and return normalized metadata.

        Supported examples:
        - https://github.com/tiangolo/fastapi
        - https://github.com/tiangolo/fastapi.git
        - git@github.com:tiangolo/fastapi.git
        """
        if not repo_url:
            raise InvalidRepositoryURLError("Repository URL is required.")

        value = repo_url.strip()
        match = cls.GITHUB_HTTPS_RE.match(value) or cls.GITHUB_SSH_RE.match(value)
        if not match:
            raise InvalidRepositoryURLError(
                "Only public GitHub repository URLs are supported. "
                "Example: https://github.com/owner/repo"
            )

        owner = match.group("owner")
        name = match.group("name")
        canonical_url = "https://github.com/%s/%s" % (owner, name)
        clone_url = canonical_url + ".git"

        return {
            "owner": owner,
            "name": name,
            "canonical_url": canonical_url,
            "clone_url": clone_url,
        }

    @classmethod
    @transaction.atomic
    def get_or_create_from_url(cls, repo_url):
        metadata = cls.parse_github_url(repo_url)

        repository, created = Repository.objects.get_or_create(
            canonical_url=metadata["canonical_url"],
            defaults={
                "source_type": RepositorySourceType.GITHUB,
                "url": metadata["clone_url"],
                "owner": metadata["owner"],
                "name": metadata["name"],
                "sync_status": RepositorySyncStatus.NOT_SYNCED,
            },
        )

        changed_fields = []
        for field, value in {
            "source_type": RepositorySourceType.GITHUB,
            "url": metadata["clone_url"],
            "owner": metadata["owner"],
            "name": metadata["name"],
        }.items():
            if getattr(repository, field) != value:
                setattr(repository, field, value)
                changed_fields.append(field)

        if changed_fields:
            changed_fields.append("updated_at")
            repository.save(update_fields=changed_fields)

        return repository

    @classmethod
    @transaction.atomic
    def get_or_create_from_local_path(cls, local_path):
        path = Path(local_path).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            raise InvalidLocalRepositoryPathError("Local path does not exist or is not a directory.")

        repository, created = Repository.objects.get_or_create(
            source_type=RepositorySourceType.LOCAL,
            local_path=str(path),
            defaults={
                "name": path.name,
                "sync_status": RepositorySyncStatus.NOT_SYNCED,
            },
        )

        if repository.name != path.name:
            repository.name = path.name
            repository.save(update_fields=["name", "updated_at"])

        return repository

    @classmethod
    def sync(cls, repository):
        """Synchronize repository files and metadata."""
        repository.sync_status = RepositorySyncStatus.SYNCING
        repository.sync_error = ""
        repository.save(update_fields=["sync_status", "sync_error", "updated_at"])

        try:
            if repository.source_type == RepositorySourceType.GITHUB:
                local_path = cls.clone_or_update_github_repository(repository)
            else:
                local_path = cls.validate_local_repository(repository)

            branch = cls.get_current_branch(local_path)
            commit_hash = cls.get_current_commit_hash(local_path)
            file_count = cls.count_source_files(local_path)

            repository.local_path = str(local_path)
            repository.current_branch = branch
            repository.default_branch = repository.default_branch or branch
            repository.current_commit_hash = commit_hash
            repository.source_file_count = file_count
            repository.sync_status = RepositorySyncStatus.SYNCED
            repository.sync_error = ""
            repository.last_synced_at = timezone.now()
            repository.save(
                update_fields=[
                    "local_path",
                    "current_branch",
                    "default_branch",
                    "current_commit_hash",
                    "source_file_count",
                    "sync_status",
                    "sync_error",
                    "last_synced_at",
                    "updated_at",
                ]
            )
            return repository

        except Exception as exc:
            repository.sync_status = RepositorySyncStatus.FAILED
            repository.sync_error = str(exc)
            repository.save(update_fields=["sync_status", "sync_error", "updated_at"])
            raise RepositorySyncError(str(exc))

    @classmethod
    def clone_or_update_github_repository(cls, repository):
        if not repository.url:
            raise RepositorySyncError("Repository clone URL is missing.")

        root = cls.get_repository_storage_root()
        local_path = cls.get_safe_repository_path(repository, root)

        if local_path.exists() and (local_path / ".git").exists():
            cls.run_git_command(["git", "fetch", "--all", "--prune"], cwd=local_path)
            cls.run_git_command(["git", "pull", "--ff-only"], cwd=local_path)
        else:
            if local_path.exists():
                shutil.rmtree(str(local_path))
            cls.run_git_command(["git", "clone", "--depth", "1", repository.url, str(local_path)])

        return local_path

    @classmethod
    def validate_local_repository(cls, repository):
        if not repository.local_path:
            raise InvalidLocalRepositoryPathError("Local path is missing.")
        path = Path(repository.local_path).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            raise InvalidLocalRepositoryPathError("Local repository path does not exist.")
        return path

    @classmethod
    def get_repository_storage_root(cls):
        configured = getattr(settings, "REPOSITORY_STORAGE_ROOT", None)
        if configured:
            return ensure_directory(configured)
        return ensure_directory(Path(settings.BASE_DIR) / "storage" / "repos")

    @classmethod
    def get_safe_repository_path(cls, repository, root):
        slug_source = repository.canonical_url or repository.local_path or repository.name
        digest = hashlib.sha1(slug_source.encode("utf-8")).hexdigest()[:10]
        safe_owner = cls.safe_slug(repository.owner or "local")
        safe_name = cls.safe_slug(repository.name)

        folder_name = f"{safe_owner}__{safe_name}__{digest}"
        return Path(root) / folder_name

    @classmethod
    def safe_slug(cls, value):
        value = value or "repo"
        return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-_.") or "repo"

    @classmethod
    def run_git_command(cls, command, cwd=None):
        try:
            result = subprocess.run(
                command,
                cwd=str(cwd) if cwd else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            raise RepositorySyncError("Git is not installed or not available in PATH.")

        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip() or "Git command failed."
            raise RepositorySyncError(message)

        return result.stdout.strip()

    @classmethod
    def get_current_branch(cls, local_path):
        try:
            return cls.run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=local_path)
        except RepositorySyncError:
            return ""

    @classmethod
    def get_current_commit_hash(cls, local_path):
        try:
            return cls.run_git_command(["git", "rev-parse", "HEAD"], cwd=local_path)
        except RepositorySyncError:
            return ""

    @classmethod
    def count_source_files(cls, local_path):
        count = 0
        root = Path(local_path)
        for current_root, dirs, files in os.walk(str(root)):
            dirs[:] = [d for d in dirs if d not in cls.IGNORED_DIRS]
            for filename in files:
                path = Path(current_root) / filename
                if cls.is_supported_source_file(path):
                    count += 1
        return count

    @classmethod
    def is_supported_source_file(cls, path):
        if path.name == ".env":
            return False
        if path.suffix in cls.SOURCE_EXTENSIONS:
            return True
        if path.name in {"Dockerfile", "Makefile", "README", "LICENSE"}:
            return True
        return False
