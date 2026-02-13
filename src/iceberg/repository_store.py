"""Repository storage abstraction.

Provides a clean interface for repository metadata operations with
strongly-typed models throughout.
"""

import json
import logging
from pathlib import Path

from iceberg.models import RepositoryMetadata

logger = logging.getLogger(__name__)


def _get_default_cache_dir() -> Path:
    """Get the default cache directory.

    Returns:
        Path to default cache directory
    """
    return Path(__file__).parent.parent.parent / "cache"


class RepositoryStore:
    """Storage abstraction for repository metadata.

    Provides type-safe operations for storing and retrieving repository
    metadata using RepositoryMetadata models.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize the repository store.

        Args:
            cache_dir: Optional cache directory. Uses default if not provided.
        """
        self.cache_dir = cache_dir or _get_default_cache_dir()
        self._repos_dir = self.cache_dir / "repos"

    def save(self, metadata: RepositoryMetadata) -> None:
        """Save repository metadata.

        Args:
            metadata: Repository metadata to save
        """
        repo_dir = self._repos_dir / metadata.owner
        repo_dir.mkdir(parents=True, exist_ok=True)

        repo_file = repo_dir / f"{metadata.name}.json"

        # Convert model to dict for storage
        data = {
            "owner": metadata.owner,
            "name": metadata.name,
            "url": str(metadata.url),
            "description": metadata.description,
            "language": metadata.language,
            "stars": metadata.stars,
            "categories": metadata.categories,
            "last_discovered": metadata.last_discovered,
        }

        repo_file.write_text(json.dumps(data, indent=2))
        logger.debug(f"Saved repository metadata for {metadata.owner}/{metadata.name}")

    def load(self, owner: str, name: str) -> RepositoryMetadata | None:
        """Load repository metadata.

        Args:
            owner: Repository owner
            name: Repository name

        Returns:
            RepositoryMetadata instance or None if not found
        """
        repo_file = self._repos_dir / owner / f"{name}.json"

        if not repo_file.exists():
            return None

        try:
            data = json.loads(repo_file.read_text())
            return RepositoryMetadata(
                name=data["name"],
                owner=data["owner"],
                url=data["url"],
                description=data.get("description"),
                language=data.get("language"),
                stars=data["stars"],
                categories=data.get("categories", {}),
                last_discovered=data["last_discovered"],
            )
        except (json.JSONDecodeError, IOError, KeyError, ValueError, TypeError) as e:
            logger.warning(f"Failed to load repository {owner}/{name}: {e}")
            return None

    def exists(self, owner: str, name: str) -> bool:
        """Check if repository exists in storage.

        Args:
            owner: Repository owner
            name: Repository name

        Returns:
            True if repository exists, False otherwise
        """
        repo_file = self._repos_dir / owner / f"{name}.json"
        return repo_file.exists()

    def list_all(self) -> list[RepositoryMetadata]:
        """List all repositories in storage.

        Returns:
            List of all RepositoryMetadata instances
        """
        if not self._repos_dir.exists():
            return []

        repos = []
        for owner_dir in self._repos_dir.iterdir():
            if not owner_dir.is_dir():
                continue

            for repo_file in owner_dir.glob("*.json"):
                try:
                    data = json.loads(repo_file.read_text())
                    repos.append(
                        RepositoryMetadata(
                            name=data["name"],
                            owner=data["owner"],
                            url=data["url"],
                            description=data.get("description"),
                            language=data.get("language"),
                            stars=data["stars"],
                            categories=data.get("categories", {}),
                            last_discovered=data["last_discovered"],
                        )
                    )
                except (json.JSONDecodeError, IOError, KeyError, ValueError, TypeError) as e:
                    logger.debug(f"Skipping invalid repository file {repo_file}: {e}")
                    continue

        return repos

    def get_by_category(self, category: str) -> list[RepositoryMetadata]:
        """Get all repositories in a specific category.

        Args:
            category: Category to filter by

        Returns:
            List of RepositoryMetadata instances in the category
        """
        all_repos = self.list_all()
        return [repo for repo in all_repos if category in repo.categories]
