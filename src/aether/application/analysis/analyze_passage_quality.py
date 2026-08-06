"""Measure the retrieval shape of stored Passages without scoring."""

from dataclasses import dataclass
from statistics import median
from typing import Optional, Tuple

from aether.domain.common import DomainValidationError
from aether.domain.content import Article, Passage
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
    """How the article divides into the units an AI system would retrieve.

    Coverage of the stored body is deliberately absent. Passages are produced
    by splitting that body, so any comparison between the two could only ever
    report full coverage. It measured the pipeline against itself rather than
    the article against its source, and editors read it as a promise that the
    whole article had been captured.
    """

    article_id: str
    article_version_id: str
    passage_profiles: Tuple[PassageProfile, ...]
    minimum_passage_word_count: Optional[int]
    maximum_passage_word_count: Optional[int]
    median_passage_word_count: Optional[float]


class AnalyzePassageQuality:
    """Read-only measurement of the passages stored for one article version."""

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

        ordered_passages = tuple(
            sorted(passages, key=lambda passage: passage.ordinal_position)
        )
        profiles = tuple(self._profile(passage) for passage in ordered_passages)
        word_counts = tuple(profile.word_count for profile in profiles)
        return PassageQualityAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            passage_profiles=profiles,
            minimum_passage_word_count=min(word_counts) if word_counts else None,
            maximum_passage_word_count=max(word_counts) if word_counts else None,
            median_passage_word_count=float(median(word_counts)) if word_counts else None,
        )

    @staticmethod
    def _profile(passage: Passage) -> PassageProfile:
        return PassageProfile(
            passage_id=passage.passage_id,
            ordinal_position=passage.ordinal_position,
            word_count=len(passage.text.split()),
            character_count=len(passage.text),
        )
