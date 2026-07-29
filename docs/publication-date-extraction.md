# Publication-date extraction

Aether extracts a publication date from raw publisher HTML using this fixed,
deterministic precedence order:

1. `datePublished` on a JSON-LD `Article` or `NewsArticle` object.
2. `<meta property="article:published_time">`.
3. `<meta name="datePublished">` or `<meta itemprop="datePublished">`.
4. The first generic `<time datetime="…">` in document order.
5. The explicitly supplied `fallback_published_at` input.
6. No value (`None`).

JSON-LD scripts and JSON objects are considered in document order. A
malformed JSON-LD script is not a parseable Article candidate. Once an
Article/NewsArticle exposes `datePublished`, that selected value is validated
as an aware ISO-8601 datetime. A missing, blank, malformed, or timezone-naive
selected value produces an explicit validation error; Aether does not silently
use a lower-priority value.

This is publisher-agnostic. It uses HTML and Schema.org semantics only, not
publisher names, domains, or URL patterns.
