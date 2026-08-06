"""Editor-facing wording for recommendations.

Wording lives in presentation, not in the use case that decides which
recommendation applies. That keeps copy out of the application layer and leaves
room for a Turkish edition of the same recommendation codes.

Two rules govern the language. Say what was observed, never what a model will
do: the product does not predict how any AI system ranks or quotes an article,
so no wording may imply it. Use the words an editor uses -- paragraph, article,
notice -- rather than the vocabulary of the parser.

Content quality wording describes the article itself and makes no claim about
machines. AI visibility wording may describe what a specification asks a
publisher to declare, because that is checkable.
"""

from dataclasses import dataclass
from typing import Dict

from aether.application.analysis.derive_editor_recommendations import (
    EditorRecommendation,
    RecommendationCategory,
    RecommendationCode,
)


@dataclass(frozen=True)
class RecommendationText:
    """One recommendation phrased for an editor."""

    headline: str
    why_it_matters: str
    what_to_do: str


CATEGORY_TITLES: Dict[RecommendationCategory, str] = {
    RecommendationCategory.CONTENT_QUALITY: "Content Quality",
    RecommendationCategory.AI_VISIBILITY: "AI Visibility Recommendations",
}


_TEXT: Dict[RecommendationCode, RecommendationText] = {
    RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY: RecommendationText(
        headline="This paragraph also appears in your other articles",
        why_it_matters=(
            "Repeated text is not part of what makes this article distinct. It "
            "adds length to the article body without adding anything specific "
            "to this story."
        ),
        what_to_do=(
            "If this is a standing notice such as a disclaimer or a byline, "
            "consider publishing it outside the article body."
        ),
    ),
}


def recommendation_text(recommendation: EditorRecommendation) -> RecommendationText:
    """Return the editor-facing wording for one recommendation."""
    return _TEXT[recommendation.code]


def category_title(category: RecommendationCategory) -> str:
    return CATEGORY_TITLES[category]


def repeated_in_phrase(other_article_count: int) -> str:
    """Describe how widely a paragraph is repeated, in plain language."""
    if other_article_count == 1:
        return "Also appears in 1 other article"
    return f"Also appears in {other_article_count} other articles"


def compared_articles_phrase(compared_article_count: int) -> str:
    """State the evidence a reuse finding rests on, always."""
    if compared_article_count == 0:
        return (
            "No other articles from this publisher have been analysed yet, so "
            "repeated text could not be checked."
        )
    if compared_article_count == 1:
        return "Checked against 1 other article from this publisher."
    return (
        f"Checked against {compared_article_count} other articles from this publisher."
    )
