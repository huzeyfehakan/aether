"""In-memory content adapter used for the initial MVP and tests.

It deliberately rejects mutation of stored Article Versions and Passages,
mirroring the immutable source-record requirement of the domain model.
"""

from typing import Dict, Mapping, Optional, Tuple

from aether.domain.common import DomainValidationError
from aether.domain.content import Article, ArticleVersion, Passage
from aether.domain.source_data import ArticleVersionSourceData
from aether.ports.outbound.content_repository import ContentRepository


class InMemoryContentRepository(ContentRepository):
    def __init__(self) -> None:
        self._articles_by_id: Dict[str, Article] = {}
        self._article_ids_by_source: Dict[str, str] = {}
        self._versions: Dict[str, ArticleVersion] = {}
        self._passages: Dict[str, Passage] = {}
        self._source_data: Dict[str, ArticleVersionSourceData] = {}

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

    def all_articles(self) -> Tuple[Article, ...]:
        """Every stored article. Used to offer an editor what to compare against."""
        return tuple(self._articles_by_id.values())

    def count_article_versions_for_publisher(self, publisher: str) -> int:
        return sum(
            1
            for version in self._versions.values()
            if self._publisher_of(version) == publisher
        )

    def find_passage_fingerprint_occurrences(
        self, publisher: str, fingerprints: Tuple[str, ...]
    ) -> Mapping[str, Tuple[str, ...]]:
        wanted = set(fingerprints)
        publisher_version_ids = {
            version_id
            for version_id, version in self._versions.items()
            if self._publisher_of(version) == publisher
        }
        occurrences: Dict[str, set] = {fingerprint: set() for fingerprint in wanted}
        for passage in self._passages.values():
            if (
                passage.content_fingerprint in wanted
                and passage.article_version_id in publisher_version_ids
            ):
                occurrences[passage.content_fingerprint].add(passage.article_version_id)
        return {
            fingerprint: tuple(sorted(version_ids))
            for fingerprint, version_ids in occurrences.items()
        }

    def save_source_data(self, source_data: ArticleVersionSourceData) -> None:
        existing = self._source_data.get(source_data.article_version_id)
        if existing is not None and existing != source_data:
            raise DomainValidationError("article version source data is immutable")
        self._source_data[source_data.article_version_id] = source_data

    def get_source_data(
        self, article_version_id: str
    ) -> Optional[ArticleVersionSourceData]:
        return self._source_data.get(article_version_id)

    def _publisher_of(self, article_version: ArticleVersion) -> Optional[str]:
        article = self._articles_by_id.get(article_version.article_id)
        return article.publisher if article is not None else None

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
