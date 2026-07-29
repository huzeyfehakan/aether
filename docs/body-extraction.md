# Body extraction

The primary body source is visible paragraph text in the fetched HTML. Aether
uses article-contained paragraphs first, then main-contained paragraphs, then
other visible paragraphs.

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
