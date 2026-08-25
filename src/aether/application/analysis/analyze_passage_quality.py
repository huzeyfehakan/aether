"""Per-paragraph size detail for one Article Version."""

from collections import Counter
from dataclasses import dataclass
import re
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
    contains_statistics: bool
    contains_citation: bool


@dataclass(frozen=True)
class PassageQualityAnalysis:
    """Per-paragraph size detail for the article."""

    article_id: str
    article_version_id: str
    passage_profiles: Tuple[PassageProfile, ...]
    passage_balance_ratio: float
    keyword_stuffing_ratio: float
    oversized_passage_rate_128: Optional[float] = None
    oversized_passage_rate_256: Optional[float] = None
    oversized_passage_rate_512: Optional[float] = None


class AnalyzePassageQuality:
    """Read-only measurement of the passages stored for one article version."""

    def __init__(self, content_repository: ContentRepository) -> None:
        self._content_repository = content_repository

    def execute(
        self,
        article: Article,
        article_version_id: str,
    ) -> PassageQualityAnalysis:
        article_version = self._content_repository.get_article_version(
            article_version_id
        )

        if article_version.article_id != article.article_id:
            raise DomainValidationError(
                "article version must belong to the article being analyzed"
            )
        passages = self._content_repository.list_passages_for_version(
            article_version_id
        )

        if any(
            passage.article_version_id != article_version.article_version_id
            for passage in passages
        ):
            raise DomainValidationError(
                "analysis passages must belong to the analyzed article version"
            )

        ordered_passages = tuple(
            sorted(
                passages,
                key=lambda passage: passage.ordinal_position,
            )
        )

        profiles = tuple(
            self._profile(passage)
            for passage in ordered_passages
        )
        oversized_rates = self._calculate_oversized_rates(profiles)
        if not profiles:
            balance_ratio = 1.0
            stuffing_ratio = 0.0
        else:
            word_counts = [
                profile.word_count
                for profile in profiles
            ]

            avg_word_count = (
                sum(word_counts) / len(word_counts)
            )

            max_word_count = (
                max(word_counts)
                if max(word_counts) > 0
                else 1
            )

            balance_ratio = (
                avg_word_count / max_word_count
            )

            stuffing_ratio = self._calculate_stuffing_ratio(
                ordered_passages
            )
        return PassageQualityAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            passage_profiles=profiles,
            passage_balance_ratio=balance_ratio,
            keyword_stuffing_ratio=stuffing_ratio,
            oversized_passage_rate_128=oversized_rates[0],
            oversized_passage_rate_256=oversized_rates[1],
            oversized_passage_rate_512=oversized_rates[2],
        )

    @staticmethod
    def _calculate_oversized_rates(
        profiles: Tuple[PassageProfile, ...],
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        if not profiles:
            return (None, None, None)
        passage_count = len(profiles)
        return tuple(
            sum(profile.word_count > bound for profile in profiles) / passage_count
            for bound in (128, 256, 512)
        )

    @staticmethod
    def _calculate_stuffing_ratio(
        passages: Tuple[Passage, ...],
    ) -> float:
        bigrams = []

        for passage in passages:
            words = [
                word.lower()
                for word in re.findall(
                    r"\b\w+\b",
                    passage.text,
                )
            ]

            for index in range(len(words) - 1):
                bigrams.append(
                    (words[index], words[index + 1])
                )

        if not bigrams:
            return 0.0

        most_common = Counter(
            bigrams
        ).most_common(1)

        if most_common:
            return (
                most_common[0][1]
                / len(bigrams)
            )

        return 0.0

    @staticmethod
    def _profile(
        passage: Passage,
    ) -> PassageProfile:
        text = passage.text

        # Citation markers such as [1] or [12] are evidence markers,
        # not statistical claims. Remove them before detecting numbers.
        text_without_citations = re.sub(
            r"\[\s*[a-zA-Z0-9]+\s*\]",
            " ",
            text,
        )

        # Detect percentages, years, currencies and numeric values.
        has_stats = bool(
            re.search(
                r"\d+%"
                r"|\b(?:19|20)\d{2}\b"
                r"|[$€£₺]\s?\d+(?:[.,]\d+)?"
                r"|\b\d+(?:[.,]\d+)?\b",
                text_without_citations,
            )
        )

        # Detect academic-style citations such as [1] or [12].
        has_citation = bool(
            re.search(
                r"\[\s*[a-zA-Z0-9]+\s*\]",
                text,
            )
        )

        return PassageProfile(
            passage_id=passage.passage_id,
            ordinal_position=passage.ordinal_position,
            word_count=len(text.split()),
            character_count=len(text),
            contains_statistics=has_stats,
            contains_citation=has_citation,
        )
