# Aether

A deterministic AI Publishing Assistant for publisher articles.

Aether reads a published article and tells an editor what to improve before it
goes out — whether the page names its author, whether it states one headline or
several, whether its body is mostly boilerplate, whether it tells machines what
it is. Every finding is derived from the page itself by fixed rules. Nothing is
inferred by a language model, and no finding depends on a threshold someone
chose.

It deliberately does **not** predict how any AI system will rank, quote or
answer from an article. It reports what is on the page and what that costs.

## What it produces

Findings are separated by who can act on them. An editor can change what an
article says today; markup and templates need the CMS or engineering, and
usually fix every article at once.

```
Editor Recommendations
Things you can change in this article now.
Compared against previously analyzed articles from this publisher (2 articles).

Most of this article is text that appears in your other articles
  36 of 61 words in this article also appear in your other articles
  Why it matters: More of this article's words are shared with your other
  articles than are its own. Anything reading the page to learn what this
  piece says finds mostly text it has already seen elsewhere.
  What to do: Check that the article's own text is reaching the published
  page. If standing notices such as a disclaimer or a byline make up most
  of the body, they belong outside it.

Technical AI Readiness
Things that need a change to the page template or the CMS.

Your article markup leaves some details undeclared
  Not declared: language
```

Every recommendation names a concrete action and what the gap costs. None of
them says "author is missing" and stops.

## What it checks

| Finding | Audience |
| --- | --- |
| No publication date, byline or summary | Editor |
| The page states more than one headline, or more than one summary | Editor |
| A paragraph that also appears in the publisher's other articles | Editor |
| A body that is mostly such text | Editor |
| No main heading, or more than one | Editor |
| No last-modified date | Technical |
| No Schema.org `Article` markup, or an incomplete one | Technical |

A URL that yields no article text is not an error. Aether says what it found
and what each case implies, separating a page that declares itself an article
but serves no text — a real fault — from a video or listing page, where
nothing is wrong.

## Quick start

Requires Python 3.9 or newer.

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
uvicorn aether.presentation.web.app:app --reload
```

Open <http://127.0.0.1:8000/> and analyse a URL, or upload a saved HTML file.

From Python:

```python
from aether.presentation.web.app import AIReadinessPipeline

pipeline = AIReadinessPipeline()
result = pipeline.analyze_report(
    html=open("article.html", encoding="utf-8").read(),
    source_url="https://publisher.example/article",
    publisher="Publisher",
    article_type="news_report",
)
```

`analyze_report` returns a finished report, or a `PageAssessment` explaining
why the page could not be analysed. Renderers for plain text, JSON and
Markdown live in `aether.presentation.ai_readiness_report_renderers`.

Findings that compare articles — repeated text, and a body that is mostly
repeated text — need more than one article from the same publisher. Analyse a
few, and the report states how many it compared against.

## Design rules

These are the constraints the code is held to, and the reason it looks the way
it does.

**Deterministic, with no thresholds.** The same page and the same corpus always
produce the same report. Where a rule needs a comparison it compares two
measured quantities rather than a constant: an article body is reported as
mostly boilerplate when its shared words outnumber its own, never when it falls
under a chosen length.

**No publisher-specific rules.** Nothing keys on a publisher name, host or URL
pattern. A site name in a title is recognised by being a separator-delimited
segment another declaration lacks, not by a list of publishers.

**Rejected approaches are written down.** Where an obvious heuristic was
considered and refused, the reasoning sits beside the rule that replaced it —
why `og:type` is reported as evidence but never trusted to classify a page, why
"this article has no subheadings" is not a finding, why matching any title
fragment against any other would let two different headlines agree.

**Findings are addressed to someone.** A recommendation an editor cannot act on
belongs in the technical section, and one nobody can act on does not belong in
the report. Several measurements were deleted for failing that test.

## Architecture

A small ports-and-adapters design. Dependencies point inward: the domain knows
nothing of FastAPI, HTTP or HTML.

```text
src/aether/
├── domain/              Immutable records and their invariants
├── application/
│   ├── ingestion/       Raw HTML to an immutable article version
│   └── analysis/        Measurements, and the advice derived from them
├── ports/outbound/      Repository contracts
├── adapters/outbound/   HTTP fetching, in-memory repositories
└── presentation/        Renderers, editor-facing wording, FastAPI app
```

One rule is worth stating here because it shapes the code: the application
layer decides *which* recommendation applies and emits a code; presentation
decides *how it reads*. That keeps copy out of use cases and leaves room for a
Turkish edition of the same findings.

[`docs/handoff.md`](docs/handoff.md) records the design principles, the ideas
deliberately rejected, and the questions to ask when editor feedback arrives.

See [`docs/architecture.md`](docs/architecture.md) for layer responsibilities,
and [`docs/body-extraction.md`](docs/body-extraction.md) and
[`docs/publication-date-extraction.md`](docs/publication-date-extraction.md)
for the extraction contracts.

## Tests

```bash
python -m unittest discover -s tests -v
```

169 tests, run on Python 3.9 through 3.13 in CI. Fixtures are reduced captures
of real publisher pages, kept faithful to what those pages actually serve —
including their defects, such as a double-escaped JSON-LD headline and a
date-only `datePublished`.

## Known limits

- Comparisons across articles hold only for the current process. Persistence
  behind the repository port would make them durable.
- Findings about a page template are reported per article, so one template fix
  is restated on every article of a property.
- Title comparison has documented edge cases, recorded in
  `application/analysis/declared_text_comparison.py`.

## License

[MIT](LICENSE).
