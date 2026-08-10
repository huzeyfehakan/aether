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
from hashlib import sha256
from html import escape
from typing import Optional


@dataclass(frozen=True)
class PreparedDraft:
    """A draft expressed as the HTML ingestion expects, plus its provenance."""

    html: str
    source_url: str
    has_markup: bool

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


def prepare_draft(
    content: str, headline: str, language: str, source_url: Optional[str] = None
) -> PreparedDraft:
    """Express a pasted draft as a document ingestion can read."""
    has_markup = _looks_like_markup(content)
    body = content if has_markup else _paragraphs_from_plain_text(content)
    heading = f"<h1>{escape(headline.strip())}</h1>" if headline.strip() else ""
    html = (
        f'<html lang="{escape(language.strip())}"><body><main>'
        f"{heading}{body}</main></body></html>"
    )
    identifier = sha256(html.encode("utf-8")).hexdigest()[:16]
    return PreparedDraft(
        html=html,
        source_url=source_url or f"https://draft.invalid/{identifier}",
        has_markup=has_markup,
    )
