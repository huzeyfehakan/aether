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
    total_word_count: int = 0

    @property
    def repeated_passage_count(self) -> int:
        return len(self.repeated_passages)

    @property
    def repeated_word_count(self) -> int:
        return sum(passage.word_count for passage in self.repeated_passages)

    @property
    def unique_word_count(self) -> int:
        return max(0, self.total_word_count - self.repeated_word_count)

    @property
    def is_mostly_repeated(self) -> bool:
        """Whether more of the body is shared text than is the article's own.

        Two measured quantities are compared against each other. No length is
        judged and no constant is chosen: an article is reported only when the
        words it shares with its publisher's other articles outweigh the words
        that are its own. A short article made entirely of its own writing is
        never reported, and a long one padded with standing notices is.
        """
        return bool(self.repeated_passages) and (
            self.repeated_word_count > self.unique_word_count
        )


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

        # Name the version to leave out rather than subtracting one from the
        # total. A draft is already absent from the corpus it is compared
        # against, so subtracting it again discounted a real article: with one
        # published article a draft reported nothing to compare against, and
        # the review then listed repeated text as a check it had not run,
        # while the comparison had in fact run and found matches.
        compared_article_count = (
            self._content_repository.count_article_versions_for_publisher(
                article.publisher, excluding=article_version_id
            )
        )
        return ContentDuplicationAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            compared_article_count=compared_article_count,
            total_passage_count=len(passages),
            # Most-repeated first, then document order, so the ordering is
            # stable and the clearest boilerplate surfaces first.
            total_word_count=sum(
                len(passage.text.split()) for passage in passages
            ),
            repeated_passages=tuple(
                sorted(
                    repeated,
                    key=lambda item: (-item.other_article_count, item.ordinal_position),
                )
            ),
        )
