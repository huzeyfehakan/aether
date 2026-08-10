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
"""

from dataclasses import dataclass
from typing import Optional, Tuple

from aether.application.analysis.build_article_analysis_report import (
    ArticleAnalysisReport,
)
from aether.application.analysis.derive_editor_recommendations import (
    DeriveEditorRecommendations,
    EditorRecommendation,
)

#: Checks that describe the published page. Each is stated with why it has to
#: wait, so an editor reads it as "not yet" rather than "you forgot".
UNAVAILABLE_UNTIL_PUBLISHED = (
    "Publication date, byline and summary, which are set when the article is published",
    "Whether the page states one headline and one summary, which needs the published page",
    "Schema.org structured data, which the site template produces",
)

#: Named separately because it depends on what the editor pasted, not on
#: whether the article is published.
HEADINGS_UNAVAILABLE_WITHOUT_MARKUP = (
    "Heading structure, because the pasted draft carried no formatting"
)


@dataclass(frozen=True)
class DraftReview:
    """What could be established from a draft, and what has to wait."""

    headline: str
    paragraph_count: int
    word_count: int
    compared_article_count: Optional[int]
    recommendations: Tuple[EditorRecommendation, ...]
    checks_performed: Tuple[str, ...]
    checks_unavailable: Tuple[str, ...]

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
        self, report: ArticleAnalysisReport, headline: str, heading_check_available: bool
    ) -> DraftReview:
        structural = report.structural_analysis
        duplication = report.content_duplication_analysis

        performed = ["Paragraph structure"]
        unavailable = list(UNAVAILABLE_UNTIL_PUBLISHED)
        if heading_check_available:
            performed.append("Heading structure")
        else:
            unavailable.insert(0, HEADINGS_UNAVAILABLE_WITHOUT_MARKUP)
        if duplication is not None and duplication.compared_article_count:
            performed.append("Text repeated in your other articles")

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
