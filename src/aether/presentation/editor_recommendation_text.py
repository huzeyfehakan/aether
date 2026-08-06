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
    RecommendationCode.NO_ARTICLE_STRUCTURED_DATA: RecommendationText(
        headline="This page does not identify itself as an article",
        why_it_matters=(
            "Schema.org is the shared vocabulary publishers use to tell "
            "software what a page is. Without it, anything reading this page "
            "has to infer from the layout that it is an article, who wrote it "
            "and when it was published."
        ),
        what_to_do=(
            "Add Schema.org Article markup to the page, declaring at least the "
            "headline, publication date, author and publisher."
        ),
    ),
    RecommendationCode.INCOMPLETE_ARTICLE_STRUCTURED_DATA: RecommendationText(
        headline="Your article markup leaves some details undeclared",
        why_it_matters=(
            "The page identifies itself as an article, but does not declare "
            "everything Schema.org provides for. Each undeclared detail is one "
            "an AI system has to guess at from the page text instead of "
            "reading it directly."
        ),
        what_to_do="Add the missing properties to the Article markup.",
    ),
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


#: Editor-facing names for the Schema.org properties this report checks.
_PROPERTY_LABELS = {
    "headline": "headline",
    "description": "summary",
    "datePublished": "publication date",
    "dateModified": "last updated date",
    "author": "author",
    "publisher": "publisher",
    "image": "image",
    "inLanguage": "language",
}


def missing_properties_phrase(missing_properties) -> str:
    """Name the undeclared details in words an editor recognises."""
    labels = [_PROPERTY_LABELS.get(name, name) for name in missing_properties]
    if len(labels) == 1:
        return f"Not declared: {labels[0]}"
    return "Not declared: " + ", ".join(labels[:-1]) + f" and {labels[-1]}"


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
