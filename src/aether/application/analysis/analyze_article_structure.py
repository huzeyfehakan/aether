"""Produce raw structural metrics for an existing immutable Article Version."""

import re
from dataclasses import dataclass
from typing import Optional, Tuple

from aether.domain.common import DomainValidationError
from aether.domain.content import Article, ArticleVersion, Passage
from aether.ports.outbound.content_repository import ContentRepository


@dataclass(frozen=True)
class ArticleStructuralAnalysis:
    """Deterministic size facts for one immutable Article Version."""

    article_id: str
    article_version_id: str
    total_passage_count: int
    total_word_count: int
    table_word_count: int
    list_word_count: int
    blockquote_word_count: int
    answered_question_heading_count: int
    unanswered_question_heading_count: int
    heading_passage_overlap_ratio: float = 0.0
    definitive_stance_ratio: float = 0.0
    #: None when no paragraph names an entity: there is no population to take
    #: the ratio over, and 0.0 read as "every entity is supported".
    unsupported_entity_ratio: Optional[float] = None


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

        source_data = self._content_repository.get_source_data(article_version_id)
        if source_data is None:
            raise DomainValidationError("source data must exist for structural analysis")

        # Niche Entity / Evidence Logic
        entity_regex = re.compile(r'\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)+\b')
        evidence_regex = re.compile(r'\d+%|\b(?:19|20)\d{2}\b|[$€£₺]\d+|\[\s*[a-zA-Z0-9]+\s*\]')

        entity_paragraphs = 0
        unsupported_entity_paragraphs = 0

        for passage in passages:
            text = passage.text
            if entity_regex.search(text):
                entity_paragraphs += 1
                if not evidence_regex.search(text):
                    unsupported_entity_paragraphs += 1

        unsupported_ratio = None
        if entity_paragraphs > 0:
            unsupported_ratio = unsupported_entity_paragraphs / entity_paragraphs

        return ArticleStructuralAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            total_passage_count=len(passages),
            total_word_count=sum(self._word_count(passage.text) for passage in passages),
            table_word_count=source_data.table_word_count,
            list_word_count=source_data.list_word_count,
            blockquote_word_count=source_data.blockquote_word_count,
            answered_question_heading_count=source_data.answered_question_heading_count,
            unanswered_question_heading_count=source_data.unanswered_question_heading_count,
            heading_passage_overlap_ratio=source_data.heading_passage_overlap_ratio,
            definitive_stance_ratio=source_data.definitive_stance_ratio,
            unsupported_entity_ratio=unsupported_ratio,
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
