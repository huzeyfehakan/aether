"""Produce raw structural metrics for an existing immutable Article Version."""

from dataclasses import dataclass
from typing import Optional, Tuple

from aether.domain.common import DomainValidationError
from aether.domain.content import Article, ArticleVersion, Passage
from aether.ports.outbound.content_repository import ContentRepository


@dataclass(frozen=True)
class ArticleStructuralAnalysis:
    """Raw, deterministic inputs for a future AI Readiness scoring layer.

    ``heading_count`` is optional because the frozen ArticleVersion model
    preserves normalized title/body text but not HTML heading-tag structure.
    This use case intentionally reports that absence instead of inferring it.
    """

    article_id: str
    article_version_id: str
    total_passage_count: int
    total_word_count: int
    average_passage_length: float
    heading_count: Optional[int]
    paragraph_count: int
    publication_date_available: bool
    canonical_url_available: bool
    language_available: bool


class AnalyzeArticleStructure:
    """Read existing source records and calculate only structural metrics."""

    def __init__(self, content_repository: ContentRepository) -> None:
        self._content_repository = content_repository

    def execute(
        self, article: Article, article_version_id: str
    ) -> ArticleStructuralAnalysis:
        article_version = self._content_repository.get_article_version(article_version_id)
        if article_version.article_id != article.article_id:
            raise DomainValidationError(
                "article version must belong to the article being analyzed"
            )
        passages = self._content_repository.list_passages_for_version(article_version_id)
        self._validate_passages(article_version, passages)

        total_passage_count = len(passages)
        total_word_count = sum(self._word_count(passage.text) for passage in passages)
        average_passage_length = (
            total_word_count / total_passage_count if total_passage_count else 0.0
        )
        return ArticleStructuralAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            total_passage_count=total_passage_count,
            total_word_count=total_word_count,
            average_passage_length=average_passage_length,
            heading_count=None,
            paragraph_count=self._paragraph_count(article_version.body),
            publication_date_available=article_version.source_published_at is not None,
            canonical_url_available=bool(article.canonical_source.strip()),
            language_available=bool(article.original_language.strip()),
        )

    @staticmethod
    def _word_count(text: str) -> int:
        return len(text.split())

    @staticmethod
    def _paragraph_count(body: str) -> int:
        return len(tuple(paragraph for paragraph in body.split("\n\n") if paragraph.strip()))

    @staticmethod
    def _validate_passages(
        article_version: ArticleVersion, passages: Tuple[Passage, ...]
    ) -> None:
        if any(
            passage.article_version_id != article_version.article_version_id
            for passage in passages
        ):
            raise DomainValidationError(
                "analysis passages must belong to the analyzed article version"
            )
