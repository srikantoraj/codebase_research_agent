from apps.repositories.models import Repository


class RepositorySelector:
    """Read-only database access for repositories."""

    @staticmethod
    def list_repositories():
        return Repository.objects.all().order_by("-updated_at")

    @staticmethod
    def get_repository(repository_id):
        return Repository.objects.get(id=repository_id)

    @staticmethod
    def get_by_canonical_url(canonical_url):
        return Repository.objects.filter(canonical_url=canonical_url).first()

    @staticmethod
    def get_by_local_path(local_path):
        return Repository.objects.filter(local_path=local_path).first()
