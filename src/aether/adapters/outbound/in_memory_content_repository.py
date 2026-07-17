"""In-memory content adapter used for the initial MVP and tests.

It deliberately rejects mutation of stored Article Versions and Passages,
mirroring the immutable source-record requirement of the domain model.
"""

from typing import Dict, Optional, Tuple

from aether.domain.common import DomainValidationError
from aether.domain.content import Article, ArticleVersion, Passage
from aether.ports.outbound.content_repository import ContentRepository


class InMemoryContentRepository(ContentRepository):
    def __init__(self) -> None:
        self._articles_by_id: Dict[str, Article] = {}
        self._article_ids_by_source: Dict[str, str] = {}
        self._versions: Dict[str, ArticleVersion] = {}
        self._passages: Dict[str, Passage] = {}

    def find_article_by_canonical_source(self, canonical_source: str) -> Optional[Article]:
        article_id = self._article_ids_by_source.get(canonical_source)
        return self._articles_by_id.get(article_id) if article_id is not None else None

    def get_article_version(self, article_version_id: str) -> ArticleVersion:
        try:
            return self._versions[article_version_id]
        except KeyError as error:
            raise DomainValidationError(
                f"article version {article_version_id} does not exist"
            ) from error

    def list_passages_for_version(self, article_version_id: str) -> Tuple[Passage, ...]:
        return tuple(
            sorted(
                (
                    passage
                    for passage in self._passages.values()
                    if passage.article_version_id == article_version_id
                ),
                key=lambda passage: passage.ordinal_position,
            )
        )

    def save_article(self, article: Article) -> None:
        existing = self._articles_by_id.get(article.article_id)
        if existing is not None and existing.canonical_source != article.canonical_source:
            raise DomainValidationError("article identity cannot change canonical source")
        source_owner = self._article_ids_by_source.get(article.canonical_source)
        if source_owner is not None and source_owner != article.article_id:
            raise DomainValidationError("canonical source already belongs to another article")
        self._articles_by_id[article.article_id] = article
        self._article_ids_by_source[article.canonical_source] = article.article_id

    def save_article_version(self, article_version: ArticleVersion) -> None:
        existing = self._versions.get(article_version.article_version_id)
        if existing is not None and existing != article_version:
            raise DomainValidationError("article version is immutable")
        self._versions[article_version.article_version_id] = article_version

    def save_passages(self, passages: Tuple[Passage, ...]) -> None:
        for passage in passages:
            existing = self._passages.get(passage.passage_id)
            if existing is not None and existing != passage:
                raise DomainValidationError("passage is immutable")
        for passage in passages:
            self._passages[passage.passage_id] = passage
