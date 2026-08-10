"""Editor-facing wording for what a draft review did and did not check.

These sentences were built in the use case that decides which checks apply,
which fixed the report to one language and put copywriting inside application
logic. They live here for the same reason recommendation wording does.

Two rules govern the language. A check that could not run is stated with its
reason and never as something missing: an editor reads "not yet", not "you
forgot". And the reason is the real one -- waiting for the page to exist,
having no formatting to read, or having nothing chosen to compare against are
three different situations and are never worded alike.
"""

from typing import Dict

from aether.application.analysis.build_draft_review import (
    DraftCheck,
    UnavailableCheck,
)

PERFORMED_TEXT: Dict[DraftCheck, str] = {
    DraftCheck.PARAGRAPH_STRUCTURE: "Paragraph structure",
    DraftCheck.HEADING_STRUCTURE: "Heading structure",
    DraftCheck.REPEATED_TEXT: "Text repeated in your other articles",
}

UNAVAILABLE_TEXT: Dict[UnavailableCheck, str] = {
    UnavailableCheck.PUBLISHED_METADATA: (
        "Publication date, byline and summary, which are set when the article "
        "is published"
    ),
    UnavailableCheck.DECLARED_CONSISTENCY: (
        "Whether the page states one headline and one summary, which needs the "
        "published page"
    ),
    UnavailableCheck.STRUCTURED_DATA: (
        "Schema.org structured data, which the site template produces"
    ),
    UnavailableCheck.HEADING_STRUCTURE_WITHOUT_MARKUP: (
        "Heading structure, because the pasted draft carried no formatting"
    ),
    UnavailableCheck.REPEATED_TEXT_NO_PUBLISHER: (
        "Text repeated in your other articles, because no publisher was chosen "
        "to compare this draft against"
    ),
    UnavailableCheck.REPEATED_TEXT_NO_ARTICLES: (
        "Text repeated in your other articles, because no articles from that "
        "publisher have been checked yet"
    ),
}


def performed_check_text(check: DraftCheck) -> str:
    return PERFORMED_TEXT[check]


def unavailable_check_text(check: UnavailableCheck) -> str:
    return UNAVAILABLE_TEXT[check]
