"""Measure deterministic Passage quality and source coverage without scoring."""

from collections import Counter
from dataclasses import dataclass
from statistics import median
from typing import Optional, Tuple

from aether.domain.common import DomainValidationError
from aether.domain.content import Article, ArticleVersion, Passage
from aether.ports.outbound.content_repository import ContentRepository


@dataclass(frozen=True)
class PassageProfile:
    """Raw length metrics for one immutable, citeable Passage."""

    passage_id: str
    ordinal_position: int
    word_count: int
    character_count: int


@dataclass(frozen=True)
class PassageQualityAnalysis:
    """Raw retrieval-readiness facts for future reporting, without a score."""

    article_id: str
    article_version_id: str
    passage_profiles: Tuple[PassageProfile, ...]
    minimum_passage_word_count: Optional[int]
    maximum_passage_word_count: Optional[int]
    median_passage_word_count: Optional[float]
    source_paragraph_count: int
    covered_source_paragraph_count: int
    source_paragraph_coverage_ratio: float
    passage_ordinals_are_contiguous: bool


class AnalyzePassageQuality:
    """Read-only measurement of existing source paragraphs and Passages."""

    def __init__(self, content_repository: ContentRepository) -> None:
        self._content_repository = content_repository

    def execute(self, article: Article, article_version_id: str) -> PassageQualityAnalysis:
        article_version = self._content_repository.get_article_version(article_version_id)
        if article_version.article_id != article.article_id:
            raise DomainValidationError(
                "article version must belong to the article being analyzed"
            )
        passages = self._content_repository.list_passages_for_version(article_version_id)
        if any(
            passage.article_version_id != article_version.article_version_id
            for passage in passages
        ):
            raise DomainValidationError(
                "analysis passages must belong to the analyzed article version"
            )

        ordered_passages = tuple(sorted(passages, key=lambda passage: passage.ordinal_position))
        profiles = tuple(self._profile(passage) for passage in ordered_passages)
        word_counts = tuple(profile.word_count for profile in profiles)
        source_paragraphs = self._source_paragraphs(article_version)
        covered_count = self._covered_paragraph_count(source_paragraphs, ordered_passages)
        source_paragraph_count = len(source_paragraphs)
        return PassageQualityAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            passage_profiles=profiles,
            minimum_passage_word_count=min(word_counts) if word_counts else None,
            maximum_passage_word_count=max(word_counts) if word_counts else None,
            median_passage_word_count=float(median(word_counts)) if word_counts else None,
            source_paragraph_count=source_paragraph_count,
            covered_source_paragraph_count=covered_count,
            source_paragraph_coverage_ratio=(
                covered_count / source_paragraph_count if source_paragraph_count else 0.0
            ),
            passage_ordinals_are_contiguous=tuple(
                passage.ordinal_position for passage in ordered_passages
            )
            == tuple(range(len(ordered_passages))),
        )

    @staticmethod
    def _profile(passage: Passage) -> PassageProfile:
        return PassageProfile(
            passage_id=passage.passage_id,
            ordinal_position=passage.ordinal_position,
            word_count=len(passage.text.split()),
            character_count=len(passage.text),
        )

    @staticmethod
    def _source_paragraphs(article_version: ArticleVersion) -> Tuple[str, ...]:
        return tuple(
            paragraph.strip()
            for paragraph in article_version.body.split("\n\n")
            if paragraph.strip()
        )

    @staticmethod
    def _covered_paragraph_count(
        source_paragraphs: Tuple[str, ...], passages: Tuple[Passage, ...]
    ) -> int:
        remaining_passage_text = Counter(passage.text for passage in passages)
        covered_count = 0
        for paragraph in source_paragraphs:
            if remaining_passage_text[paragraph] > 0:
                remaining_passage_text[paragraph] -= 1
                covered_count += 1
        return covered_count
