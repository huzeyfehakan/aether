"""Produce raw structural metrics for an existing immutable Article Version."""

from dataclasses import dataclass
from typing import Tuple

from aether.domain.common import DomainValidationError
from aether.domain.content import Article, ArticleVersion, Passage
from aether.ports.outbound.content_repository import ContentRepository


@dataclass(frozen=True)
class ArticleStructuralAnalysis:
    """Deterministic size facts for one immutable Article Version.

    Heading structure is deliberately absent rather than reported as unknown.
    The frozen ArticleVersion preserves normalized title and body text but no
    heading tags, so the field could only ever be empty. It can return once
    ingestion retains a heading inventory.
    """

    article_id: str
    article_version_id: str
    total_passage_count: int
    total_word_count: int


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

        return ArticleStructuralAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            total_passage_count=len(passages),
            total_word_count=sum(self._word_count(passage.text) for passage in passages),
        )

    @staticmethod
    def _word_count(text: str) -> int:
        return len(text.split())


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
