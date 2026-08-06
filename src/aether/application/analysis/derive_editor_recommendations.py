"""Turn existing analysis facts into recommendations an editor can act on.

This is the one place where a finding becomes advice. Every recommendation
answers a single question: what can the editor improve before publishing this
article?

Recommendations carry a category, because not every improvement is the same
kind of improvement. Content quality describes the article itself and rests on
what was measured in the text. AI visibility describes what the article
declares to machines, and rests on a published specification that says what the
declaration should contain. Keeping them apart stops a measured content fact
from being presented as a claim about how an AI system behaves.

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
    """What kind of improvement a recommendation describes."""

    CONTENT_QUALITY = "content_quality"
    AI_VISIBILITY = "ai_visibility"


class RecommendationCode(str, Enum):
    """The recommendations this MVP can justify from deterministic facts."""

    REPEATED_TEXT_IN_ARTICLE_BODY = "repeated_text_in_article_body"


_CATEGORIES = {
    RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY: (
        RecommendationCategory.CONTENT_QUALITY
    ),
}


@dataclass(frozen=True)
class EditorRecommendation:
    """One improvement an editor can make, with the evidence behind it."""

    code: RecommendationCode
    excerpt: str
    passage_ids: Tuple[str, ...]
    other_article_count: int

    @property
    def category(self) -> RecommendationCategory:
        return _CATEGORIES[self.code]


class DeriveEditorRecommendations:
    """Derive editor-facing advice from an existing analysis report."""

    def execute(self, report: ArticleAnalysisReport) -> Tuple[EditorRecommendation, ...]:
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
