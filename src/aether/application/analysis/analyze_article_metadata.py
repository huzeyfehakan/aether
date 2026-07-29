"""Produce deterministic metadata availability metrics for an Article Version."""

from dataclasses import dataclass

from aether.domain.common import DomainValidationError
from aether.domain.content import Article, ArticleVersion
from aether.ports.outbound.content_repository import ContentRepository


@dataclass(frozen=True)
class MetadataAnalysis:
    """Raw metadata facts available from the frozen source records.

    ``title_length`` is the Unicode character count of the stored, trimmed title.
    """

    article_id: str
    article_version_id: str
    title_available: bool
    title_length: int
    canonical_url_available: bool
    publication_date_available: bool
    last_modified_date_available: bool
    language_available: bool
    author_available: bool
    description_available: bool
    keyword_available: bool


class AnalyzeArticleMetadata:
    """Read-only analysis of metadata already retained in source records."""

    def __init__(self, content_repository: ContentRepository) -> None:
        self._content_repository = content_repository

    def execute(self, article: Article, article_version_id: str) -> MetadataAnalysis:
        article_version = self._content_repository.get_article_version(article_version_id)
        self._validate_article_version(article, article_version)

        title = article_version.title.strip()
        return MetadataAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            title_available=bool(title),
            title_length=len(title),
            canonical_url_available=bool(article.canonical_source.strip()),
            publication_date_available=article_version.source_published_at is not None,
            last_modified_date_available=article_version.source_updated_at is not None,
            language_available=bool(article.original_language.strip()),
            author_available=bool(article_version.author and article_version.author.strip()),
            description_available=bool(
                article_version.description and article_version.description.strip()
            ),
            keyword_available=bool(
                article_version.keywords and article_version.keywords.strip()
            ),
        )

    @staticmethod
    def _validate_article_version(article: Article, article_version: ArticleVersion) -> None:
        if article_version.article_id != article.article_id:
            raise DomainValidationError(
                "article version must belong to the article being analyzed"
            )
