# Product discovery

What we know about TRT and its content, what we only suspect, and what we have
not asked yet. Nothing here is settled. When something *is* settled it moves to
[`decisions/`](decisions/) and leaves this file.

**Read the labels.** They are the point of this document:

| Label | Means |
|---|---|
| **VERIFIED** | Established from the repository, a fixture, or an experiment run against the pipeline |
| **HYPOTHESIS** | A reasonable reading of the verified facts, **not confirmed by TRT** |
| **UNKNOWN** | We do not know, and we are not filling it in |

A hypothesis written as though it were a decision is the specific failure this
document exists to prevent.

---

## 1. What we have verified about TRT content

All of this came from fixtures, shipped code, or experiments against the current
pipeline.

- **VERIFIED** — Four TRT properties appear as captured fixtures, all of them
  article pages: TRT Haber, TRT Avaz, TRT World, TRT Çocuk / Ebeveyn Akademisi.
  Two carry `NewsArticle` JSON-LD; two carry no structured data at all.
- **SETTLED, not a discovery item** — the `og:type` measurement is closed and
  lives in
  [decision 0008](decisions/0008-classify-pages-from-declared-article-nodes.md).
  Listed here only so it is not re-measured.
- **VERIFIED** — Image alt-text is largely present: measured 6/6, 11/15 and
  75/78 across sampled pages. There was no problem to report.
- **VERIFIED** — TRT World: 670 words with no headings of any level.
- **VERIFIED** — Template furniture sits in class-named containers on four of six
  sampled pages (a legal-notice box on Ebeveyn Akademisi, a "Diğer Haberler"
  widget on TRT Avaz), where semantic containment rules cannot see it.
- **VERIFIED** — The repository contains **zero** captured non-article TRT pages.
  Every non-article behaviour in the tests uses synthetic HTML.

## 2. What the current implementation does with non-article content

Measured by running the pipeline, not inferred:

- **VERIFIED** — A podcast-episode-shaped page returns `NO_ARTICLE_TEXT_FOUND`.
  Its `PodcastEpisode`, `PodcastSeries` and `AudioObject` declarations *are*
  captured, and then discarded.
- **VERIFIED** — The same page with **one** promotional paragraph is analysed as
  an article, and is then measured for author, publication date, summary and
  `Article` markup it was never going to have.
- **VERIFIED** — Shipped wording tells the editor that video, listing and
  programme pages "are expected to look like this" and that "nothing is wrong
  and no action is needed".
- **UNKNOWN** — What a real TRT Dinle page actually looks like. Every statement
  above used a synthetic page built to resemble one.

## 3. The duplicate problem

The starting input is a single sentence from the product owner: *"TRT Dinle has
a lot of duplicate content."* We do not know what it means.

### What the current implementation detects

- **VERIFIED** — For each paragraph, whether the exact SHA-256 of its
  whitespace-normalized text appears in a passage of another stored version
  **whose publisher string is identical**, excluding drafts, **within the current
  server process**.
- **VERIFIED** — Whitespace-only variants are caught (ingestion normalizes).
- **VERIFIED** — **One changed word defeats it entirely.**
- **VERIFIED** — Two URLs sharing a canonical are silently collapsed into one
  article and **never reported** as a finding.
- **VERIFIED** — Cross-property duplication is invisible: identical text produced
  an identical fingerprint inside one repository, and nothing was reported,
  because the corpus query filters on publisher.
- The corpus is in-memory and process-scoped — no crawl, no feed, no
  persistence. This is a known property of the design, not a discovery finding;
  it is recorded under **Long-lived technical constraints** in
  [`architecture.md`](architecture.md).

### Candidate meanings — all HYPOTHESES

None of these is evidenced over the others.

| # | Hypothesis | Evidence we have | Evidence missing | Behaviour required if true |
|---|---|---|---|---|
| H1 | Repeated boilerplate — the same series blurb on every episode | Pattern is detectable *if* the text ingests | Whether TRT considers it a problem or normal furniture | Mostly built; needs episode pages to ingest at all |
| H2 | Same content under different URLs | Canonical collapse exists but is silent | Whether TRT sees multiple URLs, and whether canonicals are correct | Report identity collisions; check canonical correctness. Deterministic, cheap |
| H3 | Same underlying work in several representations | No supporting code; **no `Work` concept exists** | Whether TRT calls these duplicates or legitimate variants | A `Work` / `Representation` model. Largest change |
| H4 | Cross-property duplication | Proven blind spot, caused by one query filter | Whether cross-posting is a fault or deliberate syndication | Parameterize the publisher filter. Small change, large consequence |
| H5 | Near-duplicate / lightly rewritten | Proven blind spot; one word defeats detection | Whether TRT's cases are exact or rewritten | **Requires a threshold — conflicts with [decision 0001](decisions/0001-deterministic-rules-without-thresholds.md)** |
| H6 | Duplicate metadata across items | Comparison is within-page only, never across items | Whether editors see this | Cross-item field comparison. Deterministic, moderate |
| H7 | Exact duplicate items | `content_fingerprint` already computes this per version | Whether it occurs | Item-level fingerprint reporting. Nearly free |

- **HYPOTHESIS** — Five of the seven (H2, H3, H4, H6, H7) are *identity*
  problems rather than *similarity* problems, and would be deterministic,
  threshold-free and consistent with existing decisions.
- **HYPOTHESIS** — Only H5 requires abandoning or amending decision 0001.

---

## 4. Questions for TRT

Ordered so that the answers discriminate between H1–H7. If only two can be
asked, ask **Q1** and **Q6**.

### A. Examples

1. **5–10 URLs** you would call duplicates, grouped into sets that duplicate each
   other.
2. For each set, in one sentence: **what is wrong with it?**

### B. About each set

3. Are these the **same underlying content** — one episode, one programme, one
   story — or different content that merely looks similar?
4. Same TRT property, or **different properties** (Dinle, Haber, Avaz, Çocuk,
   World)?
5. Is the duplication the **whole page**, or **one part** — the description, the
   summary, a standing paragraph?
6. Is the repeated text **word-for-word**, or reworded?

### C. About the fix

7. **Who is expected to fix it** — the editor, the CMS team, or nobody?
8. What should **happen** when it is found: a warning before publishing, a report
   over existing content, or a cleanup list?
9. What duplication is **acceptable** — legal notices, standing disclaimers,
   series descriptions that should repeat? We need to know what not to flag
   ([decision 0005](decisions/0005-fail-toward-silence.md)).

### D. Scale and access

10. Roughly **how often** does this happen — a handful of cases, or systematic?
11. Is there an **API, feed or sitemap** for Dinle content, or must we read
    public pages?
12. Can we get a **sample export** (even 100 items) with titles, descriptions,
    URLs and programme/episode identifiers?

### Carried over, still unanswered

13. Do TRT editors control per-article structured data in the CMS, or only
    engineering? Flagged early, never confirmed. If editors control it, several
    findings currently filed as technical belong to them
    ([decision 0004](decisions/0004-every-finding-names-who-can-act.md)).
14. Do editors want a review **before** publishing or **after**? The draft flow
    was built on the assumption that it moves earlier. Unverified.
15. Did TRT understand the engagement as **AI readiness** (a property of the
    page, which this product measures) or **AI visibility** (an outcome in AI
    systems, which [decision 0003](decisions/0003-never-predict-model-behaviour.md)
    puts out of scope)? The workshop material is titled *AI Görünürlüğü* — AI
    Visibility.

---

## 5. Decisions we have not made yet

Recorded so that no one mistakes silence for a settled answer.

| Open question | Blocked on |
|---|---|
| Which duplicate meaning to build for | Q1, Q3–Q6 |
| Whether to amend decision 0001 for near-duplicates | Q6 |
| Whether the central entity stays `Article` or becomes a generic content item | Q1, Q3 |
| Whether "AI Readiness" stays the editor-facing name | Q15 — a stakeholder question, not a design one |
| Whether to keep, redesign or remove the draft feature | Q8, Q14 |
| Whether the dormant claim/knowledge subsystem is dead or deferred | An internal call; see [`handoff.md`](handoff.md) |
| A TRT content taxonomy | Q1, Q12. **Deliberately not invented here** |

## 6. Decisions we can already make

These follow from verified facts alone and depend on no TRT answer. They are
listed here as *proposals*, not as settled decisions — each becomes a record in
[`decisions/`](decisions/) once accepted.

1. **Stop silently analysing non-articles as articles.** A page declaring
   `PodcastEpisode` with one paragraph must not produce article findings. This
   is a live false-positive generator and contradicts
   [decision 0005](decisions/0005-fail-toward-silence.md).
2. **The programme-page wording is now wrong.** Telling a Dinle editor "nothing
   is wrong, no action is needed" contradicts the premise of this discovery.
3. **Keep the `checks_performed` / `checks_unavailable` frame** whatever the
   content model becomes. Stating why a check could not run is what stops
   "nothing found" from being confused with "nothing looked for".
4. **Do not build near-duplicate detection before Q6 is answered.** It is the
   only branch that forces a change to a standing decision.
