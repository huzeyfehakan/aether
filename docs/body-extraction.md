# Body extraction

The primary body source is visible paragraph text in the fetched HTML. Aether
uses article-contained paragraphs first, then main-contained paragraphs, then
other visible paragraphs.

Paragraphs inside `a`, `aside`, `figcaption`, `footer`, `header` and `nav` are
not article text. These are HTML sectioning and link semantics only: no class
name, publisher name or URL pattern is consulted. A paragraph that *contains* a
link is unaffected; only one nested *inside* a link is excluded, which is how
recommendation cards are kept out of the body while inline citations are kept
in.

Headings are collected from the same container as the body, by the same rules,
so a site banner heading is never mistaken for the article's own.

## Reliability Checks

Aether counts the text nodes observed in the page prior to applying sectioning filters (`page_visible_word_count`) and empty block elements inside `<article>`/`<main>` (`empty_body_block_count`). If the extracted text drops the majority of the page's visible words, or if the designated containers are structurally empty but rendered dynamically, Aether flags the body capture as unreliable (`BODY_NOT_SERVER_RENDERED` or `INCOMPLETE_BODY_CAPTURE`).

If body capture is deemed unreliable, Aether suppresses body-dependent GEO and SEO dimension scores (yielding `None`), preventing the silent generation of misleading metrics based on a severely truncated or empty payload.

Some server responses contain no rendered article paragraphs but include a
server-supplied `application/json` hydration payload. Aether deterministically
supports this format when a JSON object, in document order:

1. has `type` equal to `article` (case-insensitive);
2. has a `path` exactly equal to the fetched source URL path; and
3. has a `body` list whose string `value` blocks contain HTML paragraphs.

Only paragraph text inside those body blocks is retained. Images, captions,
scripts, and arbitrary JSON fields are not promoted into article text. This is
framework-payload support, not publisher-specific logic: it does not use a
publisher name, host name, or URL pattern.

If neither visible HTML paragraphs nor a matching payload body exists, ingestion
fails explicitly with `raw article html has no visible paragraphs`.
