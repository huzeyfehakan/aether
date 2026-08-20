"""Measure deterministic fluency signals for one article version."""

from dataclasses import dataclass
import re
from statistics import mean, pstdev
from typing import Tuple

from aether.domain.common import DomainValidationError
from aether.domain.content import Article
from aether.ports.outbound.content_repository import ContentRepository


@dataclass(frozen=True)
class FluencyAnalysis:
    """Deterministic fluency metrics for one immutable article version."""

    article_id: str
    article_version_id: str
    sentence_count: int
    average_sentence_word_count: float
    sentence_length_variation: float
    sentence_balance_ratio: float
    structural_variety_ratio: float


class AnalyzeFluency:
    """Measure deterministic fluency signals from stored article content."""

    def __init__(self, content_repository: ContentRepository) -> None:
        self._content_repository = content_repository

    def execute(
        self,
        article: Article,
        article_version_id: str,
    ) -> FluencyAnalysis:
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

        source_data = self._content_repository.get_source_data(article_version_id)

        if source_data is None:
            raise DomainValidationError(
                "source data must exist for fluency analysis"
            )

        ordered_passages = tuple(
            sorted(passages, key=lambda passage: passage.ordinal_position)
        )

        sentence_lengths = self._sentence_lengths(ordered_passages)

        if not sentence_lengths:
            return FluencyAnalysis(
                article_id=article.article_id,
                article_version_id=article_version.article_version_id,
                sentence_count=0,
                average_sentence_word_count=0.0,
                sentence_length_variation=0.0,
                sentence_balance_ratio=1.0,
                structural_variety_ratio=0.0,
            )

        average_sentence_word_count = mean(sentence_lengths)

        if average_sentence_word_count == 0:
            variation = 0.0
            balance_ratio = 1.0
        else:
            variation = pstdev(sentence_lengths) / average_sentence_word_count
            balance_ratio = 1.0 / (1.0 + variation)

        total_words = sum(
            len(self._word_tokens(passage.text))
            for passage in ordered_passages
        )

        structural_variety_ratio = self._structural_variety_ratio(
            source_data,
            total_words,
        )

        return FluencyAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            sentence_count=len(sentence_lengths),
            average_sentence_word_count=average_sentence_word_count,
            sentence_length_variation=variation,
            sentence_balance_ratio=balance_ratio,
            structural_variety_ratio=structural_variety_ratio,
        )

    @classmethod
    def _sentence_lengths(cls, passages) -> Tuple[int, ...]:
        lengths = []

        for passage in passages:
            sentences = re.split(
                r"(?<=[.!?])\s+",
                passage.text.strip(),
            )

            for sentence in sentences:
                words = cls._word_tokens(sentence)

                if words:
                    lengths.append(len(words))

        return tuple(lengths)

    @staticmethod
    def _word_tokens(text: str) -> Tuple[str, ...]:
        return tuple(
            re.findall(
                r"\b\w+\b",
                text,
                flags=re.UNICODE,
            )
        )

    @classmethod
    def _structural_variety_ratio(
        cls,
        source_data,
        total_words: int,
    ) -> float:
        """Measure the share of article words represented by structure."""

        if total_words <= 0:
            return 0.0

        heading_words = sum(
            len(cls._word_tokens(heading.text))
            for heading in source_data.declared_headings
        )

        structural_words = (
            source_data.list_word_count
            + source_data.blockquote_word_count
            + heading_words
        )

        return min(structural_words / total_words, 1.0)