"""Measure how clearly the article title is introduced in the opening passage."""

from dataclasses import dataclass
import re
from typing import Tuple

from aether.domain.content import Article
from aether.ports.outbound.content_repository import ContentRepository


_TURKISH_STOP_WORDS = frozenset(
    {
        "ve",
        "veya",
        "ile",
        "bir",
        "bu",
        "şu",
        "için",
        "olan",
        "olarak",
        "de",
        "da",
        "en",
        "çok",
        "daha",
        "gibi",
        "ise",
        "mi",
        "mı",
        "mu",
        "mü",
        "the",
        "a",
        "an",
        "of",
        "to",
        "in",
        "on",
        "for",
    }
)


@dataclass(frozen=True)
class TopicIntroductionAnalysis:
    """Deterministic comparison of title terms against the opening passage."""

    article_id: str
    article_version_id: str
    meaningful_title_terms: Tuple[str, ...]
    matched_title_terms: Tuple[str, ...]
    coverage: float


class AnalyzeTopicIntroduction:
    """Measure whether the opening explicitly reflects the article title."""

    def __init__(self, content_repository: ContentRepository) -> None:
        self._content_repository = content_repository

    def execute(
        self,
        article: Article,
        article_version_id: str,
    ) -> TopicIntroductionAnalysis:
        article_version = self._content_repository.get_article_version(
            article_version_id
        )

        passages = self._content_repository.list_passages_for_version(
            article_version_id
        )

        ordered_passages = tuple(
            sorted(passages, key=lambda passage: passage.ordinal_position)
        )

        title_terms = self._meaningful_terms(article_version.title)

        if not title_terms or not ordered_passages:
            return TopicIntroductionAnalysis(
                article_id=article.article_id,
                article_version_id=article_version_id,
                meaningful_title_terms=title_terms,
                matched_title_terms=(),
                coverage=0.0,
            )

        opening_terms = set(
            self._normalize_tokens(ordered_passages[0].text)
        )

        matched_terms = tuple(
            term for term in title_terms if term in opening_terms
        )

        coverage = len(matched_terms) / len(title_terms)

        return TopicIntroductionAnalysis(
            article_id=article.article_id,
            article_version_id=article_version_id,
            meaningful_title_terms=title_terms,
            matched_title_terms=matched_terms,
            coverage=coverage,
        )

    @classmethod
    def _meaningful_terms(cls, text: str) -> Tuple[str, ...]:
        tokens = cls._normalize_tokens(text)

        return tuple(
            dict.fromkeys(
                token
                for token in tokens
                if len(token) >= 3
                and token not in _TURKISH_STOP_WORDS
            )
        )

    @staticmethod
    def _normalize_tokens(text: str) -> Tuple[str, ...]:
        normalized = text.lower()
        normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
        return tuple(normalized.split())