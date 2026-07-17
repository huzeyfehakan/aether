"""Canonical persistence port for immutable source content."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple

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
    def save_article(self, article: Article) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_article_version(self, article_version: ArticleVersion) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_passages(self, passages: Tuple[Passage, ...]) -> None:
        raise NotImplementedError
