"""Turn what an editor pastes into something ingestion can accept.

A draft is not a page. It has no address, no language attribute, no title
element and, when the clipboard offers only plain text, no markup at all.
Ingestion needs all of those, so this fills exactly the gaps and nothing more.

What is supplied here is recorded, never guessed:

* the address is synthetic, under the reserved ``.invalid`` domain, so a draft
  can never be mistaken for a published page;
* the headline comes from the editor, because a pasted body often begins at the
  first paragraph;
* the language comes from the editor, because a clipboard fragment carries no
  language attribute and inferring one from the text would be a guess.

Plain text is wrapped one paragraph per blank-line-separated block, which is
the same rule ingestion already uses to split a stored body into passages. No
heading is inferred from a line's length, position or capitalisation: if the
clipboard offered no markup, the draft has no headings and the report says the
heading check could not run.
"""

from dataclasses import dataclass
import json
import re
from hashlib import sha256
from html import escape
from typing import Optional


@dataclass(frozen=True)
class PreparedDraft:
    """A draft expressed as the HTML ingestion expects, plus its provenance."""

    html: str
    source_url: str
    has_markup: bool
    headline: str
    headline_from_markup: bool

    @property
    def heading_check_available(self) -> bool:
        """Headings can only be checked when the clipboard carried markup."""
        return self.has_markup


def _looks_like_markup(content: str) -> bool:
    """Whether the clipboard gave HTML rather than plain text.

    Clipboard data is typed: a rich editor offers ``text/html`` alongside
    ``text/plain``. The caller passes whichever it received, so this only has
    to tell a fragment of markup from a block of text.
    """
    stripped = content.strip().lower()
    return "<p" in stripped or "<h1" in stripped or "<div" in stripped or "<br" in stripped


def _paragraphs_from_plain_text(content: str) -> str:
    """One paragraph per blank-line-separated block, as stored bodies split."""
    blocks = [block.strip() for block in content.split("\n\n")]
    return "".join(f"<p>{escape(block)}</p>" for block in blocks if block)


_TOP_LEVEL_HEADING = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)


def headline_in_markup(content: str) -> Optional[str]:
    """The draft's own top-level heading, if the paste carried one.

    Only a real heading element counts. A first paragraph is never treated as
    a headline: an editor who pastes a body without its headline has not
    written one here, and inventing it would put words in the report that the
    draft does not contain.
    """
    match = _TOP_LEVEL_HEADING.search(content)
    if match is None:
        return None
    text = " ".join(re.sub(r"<[^>]+>", " ", match.group(1)).split())
    return text or None


class DraftHeadlineRequired(ValueError):
    """Raised when a draft carries no heading and none was supplied."""


class DraftContentRequired(ValueError):
    """Raised when nothing was pasted.

    Caught here rather than left to ingestion, whose message describes
    paragraph markup and would reach an editor as parser language.
    """


def prepare_draft(
    content: str,
    headline: str,
    language: str,
    publisher: str = "",
    source_url: Optional[str] = None,
) -> PreparedDraft:
    """Express a pasted draft as a document ingestion can read.

    The draft's own heading wins when it has one, and no second heading is
    added, because injecting one would make every such draft appear to have
    two competing main headings.

    A draft is identified by its text *and* the publisher it is being checked
    against. Identity was the text alone, so the same draft checked twice was
    one record, and the publisher chosen the first time was the one it kept:
    an editor who checked a draft before choosing a publisher had that draft
    permanently compared against nothing, with no way to see why.
    """
    if not content or not content.strip():
        raise DraftContentRequired(
            "There is nothing to check yet. Paste your article into the box above."
        )
    has_markup = _looks_like_markup(content)
    body = content if has_markup else _paragraphs_from_plain_text(content)
    if not body.strip():
        raise DraftContentRequired(
            "There is nothing to check yet. Paste your article into the box above."
        )

    from_markup = headline_in_markup(content) if has_markup else None
    if from_markup:
        resolved, heading, headline_from_markup = from_markup, "", True
    elif headline.strip():
        resolved = headline.strip()
        heading = f"<h1>{escape(resolved)}</h1>"
        headline_from_markup = False
    else:
        raise DraftHeadlineRequired(
            "This draft has no heading. Please enter the headline you plan to publish."
        )

    html = (
        f'<html lang="{escape(language.strip())}"><body><main>'
        f"{heading}{body}</main></body></html>"
    )
    # The publisher is part of what is hashed, not appended to the address, so
    # two publishers cannot collide on a shared prefix and the address itself
    # continues to disclose nothing about either.
    identity = json.dumps([publisher, html], ensure_ascii=False, separators=(",", ":"))
    identifier = sha256(identity.encode("utf-8")).hexdigest()[:16]
    return PreparedDraft(
        html=html,
        source_url=source_url or f"https://draft.invalid/{identifier}",
        has_markup=has_markup,
        headline=resolved,
        headline_from_markup=headline_from_markup,
    )
