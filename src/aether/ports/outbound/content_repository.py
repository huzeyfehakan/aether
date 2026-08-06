"""Canonical persistence port for immutable source content."""

from abc import ABC, abstractmethod
from typing import Mapping, Optional, Tuple

from aether.domain.content import Article, ArticleVersion, Passage


class ContentRepository(ABC):
    @abstractmethod
    def find_article_by_canonical_source(self, canonical_source: str) -> Optional[Article]:
        raise NotImplementedError

    @abstractmethod
    def get_article_version(self, article_version_id: str) -> ArticleVersion:
        raise NotImplementedError

    @abstractmethod
    def list_passages_for_version(self, article_version_id: str) -> Tuple[Passage, ...]:
        raise NotImplementedError

    @abstractmethod
    def count_article_versions_for_publisher(self, publisher: str) -> int:
        """Number of stored article versions belonging to one publisher.

        Comparisons across articles are only as trustworthy as the number of
        articles available, so callers report this alongside any finding.
        """
        raise NotImplementedError

    @abstractmethod
    def find_passage_fingerprint_occurrences(
        self, publisher: str, fingerprints: Tuple[str, ...]
    ) -> Mapping[str, Tuple[str, ...]]:
        """Article version ids containing each fingerprint, within one publisher.

        Every requested fingerprint appears in the result. Version ids are
        sorted so that callers observe a stable order.
        """
        raise NotImplementedError

    @abstractmethod
    def save_article(self, article: Article) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_article_version(self, article_version: ArticleVersion) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_passages(self, passages: Tuple[Passage, ...]) -> None:
        raise NotImplementedError
