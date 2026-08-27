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

Plain text is converted deterministically: ATX headings become matching HTML
heading elements and blank-line-separated prose becomes paragraphs. No other
Markdown or inferred heading convention is applied.
"""

from dataclasses import dataclass
import json
import re
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
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
    return re.search(
        r"<(?:p|h[1-6]|div|br|ul|ol|li|blockquote|pre|table|section|article)\b",
        content,
        re.IGNORECASE,
    ) is not None


_CLIPBOARD_FRAGMENT = re.compile(
    r"<!--\s*StartFragment\s*-->(.*?)<!--\s*EndFragment\s*-->",
    re.IGNORECASE | re.DOTALL,
)


class _DraftHtmlSanitizer(HTMLParser):
    """Retain pasted rich text while discarding non-content document data."""

    _DISCARDED_CONTEXTS = {"head", "script", "style", "noscript", "template"}
    _WRAPPERS = {"html", "body"}
    _VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._discard_depth = 0

    def handle_starttag(self, tag, attrs) -> None:
        tag = tag.lower()
        if tag in self._DISCARDED_CONTEXTS:
            self._discard_depth += 1
            return
        if self._discard_depth or tag in {"meta", "link", "base"} or tag in self._WRAPPERS:
            return
        attributes = "".join(
            f' {escape(name, quote=True)}="{escape(value or "", quote=True)}"'
            for name, value in attrs
            if not name.lower().startswith("on")
        )
        self.parts.append(f"<{tag}{attributes}>")

    def handle_startendtag(self, tag, attrs) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag) -> None:
        tag = tag.lower()
        if tag in self._DISCARDED_CONTEXTS:
            self._discard_depth = max(0, self._discard_depth - 1)
            return
        if self._discard_depth or tag in self._WRAPPERS or tag in self._VOID_ELEMENTS:
            return
        self.parts.append(f"</{tag}>")

    def handle_data(self, data) -> None:
        if not self._discard_depth:
            self.parts.append(escape(data))


def _rich_text_fragment(content: str) -> str:
    """Use one clipboard representation and only its selected rich fragment.

    Browsers commonly wrap the selected content in a complete clipboard HTML
    document. The fragment comments, when present, are the source of truth;
    head/style/script data and event-handler attributes are never draft prose.
    """
    fragment = _CLIPBOARD_FRAGMENT.search(content)
    selected = fragment.group(1) if fragment is not None else content
    parser = _DraftHtmlSanitizer()
    parser.feed(selected)
    parser.close()
    return "".join(parser.parts)


_ATX_HEADING = re.compile(r"^(#{1,6})(?:[ \t]+(.*?)[ \t]*|[ \t]*)$")


def _html_from_plain_text(content: str) -> tuple[str, bool]:
    """Convert only ATX headings and blank-line-separated paragraphs.

    A heading also terminates a prose block, so Markdown that omits a blank
    line immediately before a heading still produces the intended structure.
    Embedded newlines inside a paragraph are retained as whitespace for HTML
    ingestion; the Markdown markers themselves never enter article text.
    """
    output = []
    paragraph_lines = []
    has_headings = False

    def flush_paragraph() -> None:
        if paragraph_lines:
            text = "\n".join(paragraph_lines).strip()
            if text:
                output.append(f"<p>{escape(text)}</p>")
            paragraph_lines.clear()

    for line in content.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        heading = _ATX_HEADING.fullmatch(line)
        if heading is not None and heading.group(2):
            flush_paragraph()
            level = len(heading.group(1))
            output.append(f"<h{level}>{escape(heading.group(2).strip())}</h{level}>")
            has_headings = True
        elif not line.strip():
            flush_paragraph()
        else:
            paragraph_lines.append(line)
    flush_paragraph()
    return "".join(output), has_headings


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
    if has_markup:
        body = _rich_text_fragment(content)
    else:
        body, has_markdown_headings = _html_from_plain_text(content)
        has_markup = has_markdown_headings
    if not body.strip():
        raise DraftContentRequired(
            "There is nothing to check yet. Paste your article into the box above."
        )

    from_markup = headline_in_markup(body) if has_markup else None
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
