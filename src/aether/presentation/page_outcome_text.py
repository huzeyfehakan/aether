"""Editor-facing wording for the outcome of an analysis attempt.

An editor is never shown why the parser stopped. They are told what was found,
what it most likely means, and what to do next, in the same voice as every
other recommendation.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from aether.application.ingestion.assess_page_content import (
    PageAssessment,
    PageOutcome,
)


@dataclass(frozen=True)
class OutcomeText:
    """One analysis outcome phrased for an editor."""

    headline: str
    what_happened: str
    what_to_do: str


_TEXT: Dict[PageOutcome, OutcomeText] = {
    PageOutcome.ARTICLE_TEXT_UNREADABLE: OutcomeText(
        headline="This page says it is an article, but its text could not be read",
        what_happened=(
            "The page declares itself an article to software, yet none of its "
            "article text is present in the page it serves. Anything reading "
            "the page, rather than viewing it in a browser, finds a headline "
            "with no story beneath it."
        ),
        what_to_do=(
            "Share this with whoever maintains the site. The article text is "
            "most likely assembled in the browser after the page loads, which "
            "means it is not in what software receives. It needs to be present "
            "in the page as delivered."
        ),
    ),
    PageOutcome.NO_ARTICLE_TEXT_FOUND: OutcomeText(
        headline="No article text was found on this page",
        what_happened=(
            "No article text could be read from this page, and the page does "
            "not declare itself an article. Pages such as video, listing and "
            "programme pages are expected to look like this: Aether analyses "
            "articles, so there is nothing here for it to assess."
        ),
        what_to_do=(
            "If this is not an article, nothing is wrong and no action is "
            "needed. If it is an article, share it with whoever maintains the "
            "site: its text is most likely assembled in the browser after the "
            "page loads, so it is not in what software receives."
        ),
    ),
}


def outcome_text(outcome: PageOutcome) -> OutcomeText:
    return _TEXT[outcome]


def declared_evidence(assessment: PageAssessment) -> Tuple[str, ...]:
    """What the page says about itself, shown so the reader can judge.

    The page's own declaration is reported and never used to classify. Across
    the TRT estate it is wrong in both directions, so presenting it as evidence
    is honest where trusting it would not be.
    """
    evidence = []
    if assessment.declared_page_type:
        evidence.append(
            f"The page describes itself as “{assessment.declared_page_type}”."
        )
    if assessment.declared_types:
        evidence.append(
            "Structured data on the page describes: "
            + ", ".join(assessment.declared_types)
            + "."
        )
    else:
        evidence.append("The page publishes no structured data.")
    return tuple(evidence)


def outcome_view(assessment: PageAssessment) -> Optional[Dict[str, object]]:
    """Shape a non-analysable outcome for display, or nothing if it analysed."""
    if assessment.is_analyzable:
        return None
    text = outcome_text(assessment.outcome)
    return {
        "outcome": assessment.outcome.value,
        "headline": text.headline,
        "what_happened": text.what_happened,
        "what_to_do": text.what_to_do,
        "evidence": list(declared_evidence(assessment)),
    }
