"""Say what happened when a page yields no article text.

Failing with a parser message told an editor nothing. Two very different
situations produce it: a URL that was never an article, which is an expected
outcome, and an article whose text cannot be read, which is a problem someone
has to fix.

Only one of the two can be established from the page itself. A Schema.org
Article node is a deliberate machine-readable claim by the publisher that this
page *is* an article; if one is present and no article text can be read, the
page contradicts itself and the fault is real.

Nothing else on the page is trustworthy enough to decide the other direction.
Measured against the TRT estate, ``og:type`` is wrong in both directions: a
video page declares ``article`` while a genuine news article declares
``website``. Reading it would produce confident wrong answers, so it is
reported as evidence and never used to classify.

When no Article node is declared the situation is genuinely ambiguous, and the
outcome says so rather than guessing. The editor submitted the URL and knows
whether they meant to; the report's job is to state what was found and what
each case implies.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class PageOutcome(str, Enum):
    """What became of an attempt to analyse a page."""

    ARTICLE_ANALYZED = "article_analyzed"
    ARTICLE_TEXT_UNREADABLE = "article_text_unreadable"
    NO_ARTICLE_TEXT_FOUND = "no_article_text_found"


@dataclass(frozen=True)
class PageAssessment:
    """The outcome of an analysis attempt, with the evidence behind it."""

    outcome: PageOutcome
    declares_article: bool
    declared_types: Tuple[str, ...] = ()
    declared_page_type: Optional[str] = None

    @property
    def is_analyzable(self) -> bool:
        return self.outcome is PageOutcome.ARTICLE_ANALYZED


class AssessPageContent:
    """Decide, before ingestion, whether a page can be analysed as an article."""

    def execute(self, html: str) -> PageAssessment:
        # Imported here: the collector is an ingestion detail, and importing it
        # at module level would make this module part of that import cycle.
        from aether.application.ingestion.register_raw_html_article import (
            HtmlArticleNormalizer,
            _ArticleHtmlCollector,
        )

        collector = _ArticleHtmlCollector()
        collector.feed(html)
        collector.close()

        nodes = HtmlArticleNormalizer._structured_data_nodes(
            collector.json_ld_documents
        )
        declared_types = tuple(sorted({node.node_type for node in nodes}))
        declares_article = any(
            node_type.lower() in ("article", "newsarticle")
            for node_type in declared_types
        )
        page_type = collector.metadata.get("og:type") or None

        has_text = bool(collector.paragraphs) or bool(
            HtmlArticleNormalizer._body_from_application_json(
                collector.application_json_documents, ""
            )
        )
        if has_text:
            outcome = PageOutcome.ARTICLE_ANALYZED
        elif declares_article:
            outcome = PageOutcome.ARTICLE_TEXT_UNREADABLE
        else:
            outcome = PageOutcome.NO_ARTICLE_TEXT_FOUND

        return PageAssessment(
            outcome=outcome,
            declares_article=declares_article,
            declared_types=declared_types,
            declared_page_type=page_type,
        )
