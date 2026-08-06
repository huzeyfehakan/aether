"""Find article text that also appears in a publisher's other articles."""

from dataclasses import dataclass
from typing import Tuple

from aether.domain.common import DomainValidationError
from aether.domain.content import Article
from aether.ports.outbound.content_repository import ContentRepository


@dataclass(frozen=True)
class RepeatedPassage:
    """One paragraph of this article that also appears in other articles."""

    passage_id: str
    ordinal_position: int
    text: str
    word_count: int
    other_article_count: int


@dataclass(frozen=True)
class ContentDuplicationAnalysis:
    """Text this article shares with other articles from the same publisher.

    ``compared_article_count`` is the number of *other* stored article versions
    the comparison could draw on. It is always reported, because a finding drawn
    from two articles deserves less confidence than one drawn from two hundred,
    and a count of zero means nothing could be checked at all.

    Repetition is established by exact passage fingerprints, which the domain
    already computes. No similarity measure, threshold, or judgement about what
    the repeated text means is applied here.
    """

    article_id: str
    article_version_id: str
    compared_article_count: int
    total_passage_count: int
    repeated_passages: Tuple[RepeatedPassage, ...]

    @property
    def repeated_passage_count(self) -> int:
        return len(self.repeated_passages)


class AnalyzeContentDuplication:
    """Compare one article version against its publisher's other articles."""

    def __init__(self, content_repository: ContentRepository) -> None:
        self._content_repository = content_repository

    def execute(
        self, article: Article, article_version_id: str
    ) -> ContentDuplicationAnalysis:
        article_version = self._content_repository.get_article_version(article_version_id)
        if article_version.article_id != article.article_id:
            raise DomainValidationError(
                "article version must belong to the article being analyzed"
            )
        passages = self._content_repository.list_passages_for_version(article_version_id)
        occurrences = self._content_repository.find_passage_fingerprint_occurrences(
            article.publisher,
            tuple(passage.content_fingerprint for passage in passages),
        )

        repeated = []
        for passage in passages:
            other_version_ids = {
                version_id
                for version_id in occurrences.get(passage.content_fingerprint, ())
                if version_id != article_version_id
            }
            if other_version_ids:
                repeated.append(
                    RepeatedPassage(
                        passage_id=passage.passage_id,
                        ordinal_position=passage.ordinal_position,
                        text=passage.text,
                        word_count=len(passage.text.split()),
                        other_article_count=len(other_version_ids),
                    )
                )

        stored_versions = self._content_repository.count_article_versions_for_publisher(
            article.publisher
        )
        return ContentDuplicationAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            compared_article_count=max(0, stored_versions - 1),
            total_passage_count=len(passages),
            # Most-repeated first, then document order, so the ordering is
            # stable and the clearest boilerplate surfaces first.
            repeated_passages=tuple(
                sorted(
                    repeated,
                    key=lambda item: (-item.other_article_count, item.ordinal_position),
                )
            ),
        )
