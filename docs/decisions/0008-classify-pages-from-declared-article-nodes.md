# 0008 — Classify pages from declared Article nodes, never from `og:type`

## Decision

A page is analysed as an article when article text can be read from it. When no
text can be read, a declared Schema.org `Article` / `NewsArticle` node is the
only signal trusted to say the page *should* have had text. `og:type` is
reported to the reader as evidence and is never used to classify.

## Why

`og:type` was measured wrong in **both** directions on the TRT estate: a video
page declares `article`, and a news article declares `website`. Reading it would
produce confident wrong answers, which is the most expensive kind
([0005](0005-fail-toward-silence.md)).

## Evidence and context

`assess_page_content.py` produces three outcomes:

| Outcome | Meaning |
|---|---|
| `ARTICLE_ANALYZED` | Text was read; analysis proceeds |
| `ARTICLE_TEXT_UNREADABLE` | Declares `Article`, serves no text — a real fault someone must fix |
| `NO_ARTICLE_TEXT_FOUND` | Genuinely ambiguous; the outcome says so rather than guessing |

## Consequences

Measured directly against the current pipeline:

- A page with no prose in `<p>` is not analysed. A podcast episode page returns
  `NO_ARTICLE_TEXT_FOUND`, with `PodcastEpisode`, `PodcastSeries` and
  `AudioObject` correctly captured in the declared inventory and then discarded.
- A page carrying **any single `<p>`** is analysed as an article regardless of
  what it declares. The same episode page plus one promotional paragraph is
  analysed as an article, and is then measured for author, publication date and
  `Article` markup it was never going to have.
- The shipped wording tells an editor that video, listing and **programme** pages
  are expected to look like this and that nothing is wrong.

The second and third consequences are open problems, not settled behaviour. They
are recorded in [`../product-discovery.md`](../product-discovery.md).

## Reopen when

The content model stops being article-only. This decision is scoped to a product
that analyses articles; it does not survive a generic content model unchanged.
The `og:type` finding, however, survives any model: it was measured, and it
holds regardless of what the central entity becomes.
