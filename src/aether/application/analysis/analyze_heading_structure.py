"""Check whether an article's headings form a usable outline.

Headings are how a reader skims an article and how software finds the part of
it that answers a question. Three faults in an outline can be established from
the markup alone, without judging the writing:

* no top-level heading, so nothing states what the article as a whole is about;
* more than one top-level heading, so which one names the article is ambiguous;
* a level skipped, such as a section heading followed directly by a
  sub-sub-heading, which leaves a gap in the outline.

Rejected: reporting an article that has no subheadings at all.
---------------------------------------------------------------
It is tempting, and TRT World would trigger it: 670 words with no headings of
any level. It was left out because it cannot be stated without a length
threshold. A three-paragraph note needs no subheadings and a long feature does,
and the boundary between them is a judgement about writing, not a fact about
markup. Any threshold chosen here would be arbitrary, would differ per desk and
per language, and would produce a recommendation the product could not defend
when an editor asked why. The absence of a top-level heading is reported
instead, which is a fact rather than an opinion, and which TRT World also
exhibits.
"""

from dataclasses import dataclass
from typing import Tuple

from aether.domain.common import DomainValidationError
from aether.domain.content import Article
from aether.domain.source_data import DeclaredHeading
from aether.ports.outbound.content_repository import ContentRepository


@dataclass(frozen=True)
class SkippedHeadingLevel:
    """A place where the outline jumps past one or more levels."""

    from_level: int
    to_level: int


@dataclass(frozen=True)
class HeadingStructureAnalysis:
    """The outline an article declares, and where it breaks."""

    article_id: str
    article_version_id: str
    headings: Tuple[DeclaredHeading, ...]
    top_level_count: int
    skipped_levels: Tuple[SkippedHeadingLevel, ...]

    @property
    def has_headings(self) -> bool:
        return bool(self.headings)


class AnalyzeHeadingStructure:
    """Read the retained heading inventory for one article version."""

    def __init__(self, content_repository: ContentRepository) -> None:
        self._content_repository = content_repository

    def execute(
        self, article: Article, article_version_id: str
    ) -> HeadingStructureAnalysis:
        article_version = self._content_repository.get_article_version(article_version_id)
        if article_version.article_id != article.article_id:
            raise DomainValidationError(
                "article version must belong to the article being analyzed"
            )
        source_data = self._content_repository.get_source_data(article_version_id)
        headings = source_data.declared_headings if source_data is not None else ()

        return HeadingStructureAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            headings=headings,
            top_level_count=sum(1 for heading in headings if heading.level == 1),
            skipped_levels=self._skipped_levels(headings),
        )

    @staticmethod
    def _skipped_levels(
        headings: Tuple[DeclaredHeading, ...],
    ) -> Tuple[SkippedHeadingLevel, ...]:
        """Places where the outline descends by more than one level at once.

        Only descents are counted. Returning from a sub-heading to a higher
        level closes a section and is ordinary.
        """
        skipped = []
        for previous, current in zip(headings, headings[1:]):
            if current.level > previous.level + 1:
                skipped.append(
                    SkippedHeadingLevel(
                        from_level=previous.level, to_level=current.level
                    )
                )
        return tuple(skipped)
