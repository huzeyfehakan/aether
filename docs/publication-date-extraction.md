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
as an ISO-8601 date or datetime. A valid datetime without a timezone is
parseable but is not trusted as a source timestamp, so the field is unavailable
(`None`). A date-only value retains the existing midnight-UTC normalization;
timezone-aware values retain their declared offset. A missing, blank, or
malformed selected value produces an explicit validation error. An unusable
selected value does not silently activate a lower-priority value.

The same timezone semantics apply to a selected JSON-LD `dateModified` and its
lower-priority metadata sources. No timezone is inferred from the publisher,
host name, country-code domain, browser locale, or system locale.

This is publisher-agnostic. It uses HTML and Schema.org semantics only, not
publisher names, domains, or URL patterns.
