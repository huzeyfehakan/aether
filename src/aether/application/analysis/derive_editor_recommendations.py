"""Turn existing analysis facts into recommendations an editor can act on.

This is the one place where a finding becomes advice. Every recommendation
answers a single question: what can the editor improve before publishing this
article?

Recommendations carry a category naming *who can act on them*. An editor can
change what this article says today. Changing how the page is built -- its
markup, its declarations, its template -- needs the CMS or engineering, and
usually fixes every article at once rather than this one. Mixing the two buries
the few things an editor can fix among many things they cannot, which is the
fastest way to make a report ignored.

Only a category, a code and the supporting facts are produced here. The wording
belongs to presentation, which serves editors in their own language; putting
sentences in this layer would fix the report to one language and place
copywriting inside a use case.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

from aether.application.analysis.build_article_analysis_report import (
    ArticleAnalysisReport,
)


class RecommendationCategory(str, Enum):
    """Who can act on a recommendation."""

    EDITOR = "editor"
    TECHNICAL = "technical"


class RecommendationCode(str, Enum):
    """The recommendations this MVP can justify from deterministic facts."""

    REPEATED_TEXT_IN_ARTICLE_BODY = "repeated_text_in_article_body"
    NO_ARTICLE_STRUCTURED_DATA = "no_article_structured_data"
    INCOMPLETE_ARTICLE_STRUCTURED_DATA = "incomplete_article_structured_data"
    TITLE_SOURCES_DISAGREE = "title_sources_disagree"


#: Structured data is declared by the page template, so correcting it is a CMS
#: or engineering change that fixes every article at once.
#:
#: Repeated text is filed under the editor because the editor owns the article
#: body and is the person who sees the paragraph. Whether the remedy is theirs
#: or the CMS team's depends on how the text got there, which the markup does
#: not reveal, so the advice names both paths rather than guessing.
_CATEGORIES = {
    RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY: RecommendationCategory.EDITOR,
    RecommendationCode.TITLE_SOURCES_DISAGREE: RecommendationCategory.EDITOR,
    RecommendationCode.NO_ARTICLE_STRUCTURED_DATA: RecommendationCategory.TECHNICAL,
    RecommendationCode.INCOMPLETE_ARTICLE_STRUCTURED_DATA: (
        RecommendationCategory.TECHNICAL
    ),
}


@dataclass(frozen=True)
class EditorRecommendation:
    """One improvement an editor can make, with the evidence behind it."""

    code: RecommendationCode
    excerpt: str = ""
    passage_ids: Tuple[str, ...] = ()
    other_article_count: int = 0
    missing_properties: Tuple[str, ...] = ()
    declared_values: Tuple[Tuple[str, str], ...] = ()

    @property
    def category(self) -> RecommendationCategory:
        return _CATEGORIES[self.code]


class DeriveEditorRecommendations:
    """Derive editor-facing advice from an existing analysis report."""

    def execute(self, report: ArticleAnalysisReport) -> Tuple[EditorRecommendation, ...]:
        return (
            self._title_consistency(report)
            + self._editor(report)
            + self._technical(report)
        )

    @staticmethod
    def _technical(
        report: ArticleAnalysisReport,
    ) -> Tuple[EditorRecommendation, ...]:
        analysis = report.structured_data_analysis
        if analysis is None:
            return ()
        if not analysis.article_node_present:
            return (
                EditorRecommendation(
                    code=RecommendationCode.NO_ARTICLE_STRUCTURED_DATA,
                ),
            )
        if analysis.missing_article_properties:
            return (
                EditorRecommendation(
                    code=RecommendationCode.INCOMPLETE_ARTICLE_STRUCTURED_DATA,
                    missing_properties=analysis.missing_article_properties,
                ),
            )
        return ()

    @staticmethod
    def _title_consistency(
        report: ArticleAnalysisReport,
    ) -> Tuple[EditorRecommendation, ...]:
        analysis = report.title_consistency_analysis
        if analysis is None or analysis.titles_agree:
            return ()
        return (
            EditorRecommendation(
                code=RecommendationCode.TITLE_SOURCES_DISAGREE,
                declared_values=tuple(
                    (title.source.value, title.value)
                    for title in analysis.declared_titles
                ),
            ),
        )

    @staticmethod
    def _editor(
        report: ArticleAnalysisReport,
    ) -> Tuple[EditorRecommendation, ...]:
        duplication = report.content_duplication_analysis
        if duplication is None:
            return ()
        return tuple(
            EditorRecommendation(
                code=RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY,
                excerpt=repeated.text,
                passage_ids=(repeated.passage_id,),
                other_article_count=repeated.other_article_count,
            )
            for repeated in duplication.repeated_passages
        )
