"""Project a draft's analyses into a result of its own.

A draft is not a page. It has no address, no template, no publication date and
no structured data, because none of that exists until it is published. Passing
a draft through the published-article report meant carrying fields that could
only ever read as absent, and an editor was shown their unpublished draft with
a metadata completeness of "missing".

Hiding those fields in the interface would not have been enough. This is a
separate result type so that a draft has no place to put them: the leak is
prevented by the shape of the data rather than by remembering to filter it.

Checks that need the published page are named here as unavailable, with the
reason. They are not failures and are never reported as missing.

Which checks ran, and why the others could not, is stated as codes. This layer
decides whether a check applies; how that reads to an editor, and in which
language, belongs to presentation -- the same rule that already separates a
recommendation from its wording.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from aether.application.analysis.build_article_analysis_report import (
    ArticleAnalysisReport,
)
from aether.application.analysis.derive_editor_recommendations import (
    DeriveEditorRecommendations,
    EditorRecommendation,
)

class DraftCheck(str, Enum):
    """A check a draft's own text can answer."""

    PARAGRAPH_STRUCTURE = "paragraph_structure"
    HEADING_STRUCTURE = "heading_structure"
    REPEATED_TEXT = "repeated_text"


class UnavailableCheck(str, Enum):
    """A check that could not run, named together with why.

    Each carries its own reason rather than a shared one, because the reasons
    are not alike: three wait for the page to exist, one depends on what the
    clipboard offered, and two on what the editor chose to compare against.
    An editor reads these as "not yet", never as something they failed to do.

    A comparison that did not happen is always stated. Leaving it out made
    "nothing to change" mean both "nothing was found" and "nothing was looked
    for", which cannot be told apart.
    """

    PUBLISHED_METADATA = "published_metadata"
    DECLARED_CONSISTENCY = "declared_consistency"
    STRUCTURED_DATA = "structured_data"
    HEADING_STRUCTURE_WITHOUT_MARKUP = "heading_structure_without_markup"
    REPEATED_TEXT_NO_PUBLISHER = "repeated_text_no_publisher"
    REPEATED_TEXT_NO_ARTICLES = "repeated_text_no_articles"


#: Checks that describe the published page, in the order they are reported.
UNAVAILABLE_UNTIL_PUBLISHED = (
    UnavailableCheck.PUBLISHED_METADATA,
    UnavailableCheck.DECLARED_CONSISTENCY,
    UnavailableCheck.STRUCTURED_DATA,
)


@dataclass(frozen=True)
class DraftReview:
    """What could be established from a draft, and what has to wait."""

    headline: str
    paragraph_count: int
    word_count: int
    compared_article_count: Optional[int]
    recommendations: Tuple[EditorRecommendation, ...]
    checks_performed: Tuple[DraftCheck, ...]
    checks_unavailable: Tuple[UnavailableCheck, ...]

    @property
    def has_findings(self) -> bool:
        return bool(self.recommendations)


class BuildDraftReview:
    """Compose a draft review from the analyses a draft can support."""

    def __init__(
        self, recommendations: Optional[DeriveEditorRecommendations] = None
    ) -> None:
        self._recommendations = recommendations or DeriveEditorRecommendations()

    def execute(
        self,
        report: ArticleAnalysisReport,
        headline: str,
        heading_check_available: bool,
        comparison_requested: bool = True,
    ) -> DraftReview:
        structural = report.structural_analysis
        duplication = report.content_duplication_analysis

        performed = [DraftCheck.PARAGRAPH_STRUCTURE]
        unavailable = list(UNAVAILABLE_UNTIL_PUBLISHED)
        if heading_check_available:
            performed.append(DraftCheck.HEADING_STRUCTURE)
        else:
            unavailable.insert(0, UnavailableCheck.HEADING_STRUCTURE_WITHOUT_MARKUP)

        compared = duplication.compared_article_count if duplication is not None else 0
        if not comparison_requested:
            unavailable.insert(0, UnavailableCheck.REPEATED_TEXT_NO_PUBLISHER)
        elif compared:
            performed.append(DraftCheck.REPEATED_TEXT)
        else:
            unavailable.insert(0, UnavailableCheck.REPEATED_TEXT_NO_ARTICLES)

        return DraftReview(
            headline=headline,
            paragraph_count=structural.total_passage_count,
            word_count=structural.total_word_count,
            compared_article_count=(
                duplication.compared_article_count if duplication is not None else None
            ),
            recommendations=self._recommendations.execute(report),
            checks_performed=tuple(performed),
            checks_unavailable=tuple(unavailable),
        )
