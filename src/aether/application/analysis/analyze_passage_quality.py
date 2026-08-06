"""Per-paragraph size detail for one Article Version."""

from dataclasses import dataclass
from typing import Tuple

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
    """Per-paragraph size detail for the article.

    Summary statistics over these lengths were removed: they described the
    article without suggesting anything an editor could do about it, which is
    the bar every part of the report has to clear.
    """

    article_id: str
    article_version_id: str
    passage_profiles: Tuple[PassageProfile, ...]


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
        return PassageQualityAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            passage_profiles=tuple(
                self._profile(passage) for passage in ordered_passages
            ),
        )

    @staticmethod
    def _profile(passage: Passage) -> PassageProfile:
        return PassageProfile(
            passage_id=passage.passage_id,
            ordinal_position=passage.ordinal_position,
            word_count=len(passage.text.split()),
            character_count=len(passage.text),
        )
