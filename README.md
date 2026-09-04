# Aether

A deterministic SEO and GEO / AI-readiness assistant for publisher articles.

Aether analyses either a published URL or a draft pasted from a CMS or word
processor. Its Turkish-first web interface can be switched to English. It
combines actionable findings with separate, explainable SEO and GEO scores,
all calculated from measurable page or draft signals by fixed rules.

Aether does **not** call OpenAI, Gemini, Anthropic, Ollama, or another large
language model at runtime. It does not predict ChatGPT, Gemini, Perplexity, or
any other system's rankings, citations, visibility, or behaviour. The scores
measure deterministic structural and content readiness; they are not forecasts
of model outcomes.

## What it produces

Published-page analysis provides two 0–100 composite scores with their
dimensions and underlying signal details:

| SEO | GEO / AI readiness |
| --- | --- |
| Entity Coverage | Semantic Completeness |
| Structured Data | Entity Authority |
| Semantic Quality | Structural Richness |
| Technical Access | Discoverability |

Each dimension's details are rendered inside its owning score card, including
the measured inputs and the factors currently limiting the composite score.
Counts, ratios, scores, measurements, and contextual values retain distinct
formats so that supporting context is not presented as a scoring input.

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

Every recommendation names a concrete action and what the gap costs. Where the
underlying analysis identifies relevant article passages, the recommendation
also attributes those passages so the editor can inspect the evidence in
context. None of them says "author is missing" and stops.

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

**Checking a draft.** An editor can paste a draft from a CMS or word processor,
keeping formatting so headings survive, and choose which publisher's
already-checked articles to compare it against. The result includes editor
recommendations and a pre-publication draft GEO preview, labelled in Turkish as
"Yayın Öncesi GEO Önizlemesi". It states what was checked, what can only be
measured after publishing, and why. A check that could not run is never
reported as a failure.

Draft GEO and published-page GEO are **not directly comparable**. A draft has
only the signals measurable from its content before publication; a published
page adds signals from the delivered HTML, metadata, structured data, links,
and technical presentation. Missing post-publication signals remain unmeasured
rather than being treated as failures.

## Quick start

Requires Python 3.9 or newer.

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
uvicorn aether.presentation.web.app:app --reload
```

Open <http://127.0.0.1:8000/> to analyse a published URL or check a draft before
publication.

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

The constraints the code is held to, each recorded in
[`docs/decisions/`](docs/decisions/) with the evidence behind it and the
condition that would reopen it.

| | |
|---|---|
| [Deterministic analysis](docs/decisions/0001-deterministic-rules-without-thresholds.md) | The same input and comparison corpus produce the same measurements; any explicit prototype thresholds are documented |
| [No publisher-specific rules](docs/decisions/0002-no-publisher-specific-rules.md) | Nothing keys on a name, host or URL pattern |
| [Scores measure readiness, not model behaviour](docs/decisions/0011-dual-scoring-supersedes-0003.md) | SEO and GEO scores summarize deterministic signals; they do not forecast rankings, citations, visibility, or answers |
| [Every finding names who can act on it](docs/decisions/0004-every-finding-names-who-can-act.md) | Editor or technical; a finding nobody can act on is not reported |
| [Fail toward silence](docs/decisions/0005-fail-toward-silence.md) | A false positive costs an editor's trust; a missed finding costs less |
| [Separate finding codes from wording](docs/decisions/0007-separate-finding-codes-from-wording.md) | The application emits a code; presentation decides how it reads |

Rejected approaches are written down beside the decision that replaced them —
why `og:type` is reported as evidence but never trusted to classify a page, why
"this article has no subheadings" is not a finding, why matching any title
fragment against any other would let two different headlines agree.

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
decides *how it reads*. That keeps copy out of use cases, and is what makes a
second interface language a lookup table rather than a rewrite.

## Documentation

[`docs/context.md`](docs/context.md) is the index — it says which document
answers which question. In short:

| | |
|---|---|
| [`AGENTS.md`](AGENTS.md) | How to work in this repository: process, git, verification |
| [`docs/handoff.md`](docs/handoff.md) | Current state: released and in-progress work, blockers, next step |
| [`docs/decisions/`](docs/decisions/) | Settled product decisions and the evidence behind them |
| [`docs/product-discovery.md`](docs/product-discovery.md) | What is still unknown, and the questions that would settle it |
| [`docs/architecture.md`](docs/architecture.md) | Layer responsibilities and the package map |

Extraction contracts have their own notes:
[`docs/body-extraction.md`](docs/body-extraction.md) and
[`docs/publication-date-extraction.md`](docs/publication-date-extraction.md).

## Tests

```bash
python -m unittest discover -s tests -v
```

Run on Python 3.9 through 3.13 in CI. Fixtures are reduced captures of real
publisher pages, kept faithful to what those pages actually serve — including
their defects, such as a double-escaped JSON-LD headline and a date-only
`datePublished`.

Some tests run the served page's own script under Node and **skip silently when
Node is absent**, still reporting `OK`. Check the skip count, not just the
result — see [`AGENTS.md`](AGENTS.md) §3 for what counts as verified, and
[`docs/architecture.md`](docs/architecture.md) for the harness's structural
limits.

## Known limits

What this means for someone using the tool. The technical statement of each is
in [`docs/architecture.md`](docs/architecture.md).

- Comparisons across articles hold only for the current process, and only
  within one publisher. Persistence behind the repository port would make them
  durable.
- Findings about a page template are reported per article, so one template fix
  is restated on every article of a property.
- Title comparison has documented edge cases, recorded in
  `application/analysis/declared_text_comparison.py`.
- Only pages carrying article prose are analysed. Audio, video and programme
  pages are reported as such and not assessed —
  [decision 0008](docs/decisions/0008-classify-pages-from-declared-article-nodes.md).

## License

[MIT](LICENSE).
