"""Check whether an article's headings form a usable outline.

Headings are how a reader skims an article and how software finds the part of
it that answers a question. Three faults in an outline can be established from
the markup alone, without judging the writing:

* no top-level heading, so nothing states what the article as a whole is about;
* more than one top-level heading, so which one names the article is ambiguous.

Withdrawn: reporting a skipped heading level.
---------------------------------------------
A gap in the outline is a real fault and the check was deterministic, but
measured against the TRT estate it almost never found one. What it found was
template furniture: the heading of a legal-notice box on TRT Çocuk Ebeveyn
Akademisi, and a "Diğer Haberler" related-articles widget on TRT Avaz. Both
sit in class-named containers rather than in nav, aside, header or footer, so
the containment rules that keep such boxes out of the body text cannot see
them.

The check therefore asked editors to renumber headings they did not write and
cannot move, on four of six pages. A check that misfires costs more than one
that stays silent, because it teaches an editor to distrust the report. It can
return when furniture can be recognised, for instance once a heading can be
tied to body text already known to be boilerplate.

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
class HeadingStructureAnalysis:
    """The outline an article declares, and where it breaks."""

    article_id: str
    article_version_id: str
    headings: Tuple[DeclaredHeading, ...]
    top_level_count: int
    skipped_heading_levels: bool = False

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

        skipped = False
        if headings:
            if headings[0].level > 2:
                skipped = True
            else:
                for i in range(1, len(headings)):
                    if headings[i].level - headings[i-1].level > 1:
                        skipped = True
                        break

        return HeadingStructureAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            headings=headings,
            top_level_count=sum(1 for heading in headings if heading.level == 1),
            skipped_heading_levels=skipped,
        )

