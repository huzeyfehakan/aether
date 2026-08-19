"""Per-paragraph size detail for one Article Version."""

from dataclasses import dataclass
from typing import Tuple

from aether.domain.common import DomainValidationError
from aether.domain.content import Article, Passage
from aether.ports.outbound.content_repository import ContentRepository


import re

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
        
        # Calculate passage balance ratio
        if not profiles:
            balance_ratio = 1.0
            stuffing_ratio = 0.0
        else:
            word_counts = [p.word_count for p in profiles]
            avg_word_count = sum(word_counts) / len(word_counts)
            max_word_count = max(word_counts) if max(word_counts) > 0 else 1
            balance_ratio = avg_word_count / max_word_count
            
            # Simple keyword stuffing check: most frequent bigram ratio
            stuffing_ratio = self._calculate_stuffing_ratio(ordered_passages)

        return PassageQualityAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            passage_profiles=profiles,
            passage_balance_ratio=balance_ratio,
            keyword_stuffing_ratio=stuffing_ratio,
        )

    @staticmethod
    def _calculate_stuffing_ratio(passages: Tuple[Passage, ...]) -> float:
        from collections import Counter
        bigrams = []
        for p in passages:
            words = [w.lower() for w in re.findall(r'\b\w+\b', p.text)]
            for i in range(len(words) - 1):
                bigrams.append((words[i], words[i+1]))
        if not bigrams:
            return 0.0
        most_common = Counter(bigrams).most_common(1)
        if most_common:
            return most_common[0][1] / len(bigrams)
        return 0.0

    @staticmethod
    def _profile(passage: Passage) -> PassageProfile:
        text = passage.text
        # Matches numbers, percentages, years like 202x, and currencies ($, €, £, ₺)
        has_stats = bool(re.search(r'\d+%|\b(?:19|20)\d{2}\b|[$€£₺]\d+|\b\d+(?:\.\d+)?\b', text))
        # Matches academic citations like [1] or [12]
        has_citation = bool(re.search(r'\[\d+\]', text))
        
        return PassageProfile(
            passage_id=passage.passage_id,
            ordinal_position=passage.ordinal_position,
            word_count=len(text.split()),
            character_count=len(text),
            contains_statistics=has_stats,
            contains_citation=has_citation,
        )
