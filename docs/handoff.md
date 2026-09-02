# Handoff — current state

Volatile state only: what is being worked on, what is blocking it, what is
verified right now, and what to do next. Anything that outlives the current
piece of work belongs elsewhere.

- **How to work** → [`../AGENTS.md`](../AGENTS.md)
- **Which file to read when** → [`context.md`](context.md)
- **Why it works this way** → [`decisions/`](decisions/)
- **What we do not know yet** → [`product-discovery.md`](product-discovery.md)
- **How the code is arranged, and its long-lived constraints** →
  [`architecture.md`](architecture.md)

## Current task

The current work combines two deterministic prototypes:

**Topic introduction recommendation.** A deterministic editor recommendation
checks whether the article's main topic is sufficiently represented in the
opening passage.

**Proportional Dual Scoring (SEO/GEO).** Separate SEO and GEO visibility
scores are calculated using deterministic rule-based metrics and presented in
the article report.

Both features are being evaluated on real publisher articles before further
product work is finalized.

## Released

Latest release: `v2.0.1`. See [`../README.md`](../README.md) for shipped
capabilities.

## In progress

**Draft Markdown structure and SEO/GEO previews.** Implemented and intentionally
left uncommitted because the requester prohibited git add/commit/push. ATX
H1-H6 headings and blank-line paragraphs now enter normal HTML structural
analysis, and draft results expose preview scores with source-only dimensions
left unmeasured. Clipboard fragment precedence and shared delegated score-detail
toggles now cover the draft result path. The full Python/server suite passes
(313 tests, 14 skipped);
browser JavaScript verification remains outstanding because Node is unavailable.

**Published passage details.** Implemented and intentionally uncommitted. The
published report now exposes each final production `PassageProfile` text and
its existing `word_count` in production order, behind the shared accessible
Details toggle. The TRT regression remains 11 passages / 343 words; headings
and metadata remain outside the passage list and totals. Draft passage details
are intentionally out of scope because the draft review model does not retain
the production passage profiles.

**Check a draft before publishing.** Implemented, unreleased. Its usefulness is
under review rather than settled — the checks are thinner than the reporting
frame around them. See [`product-discovery.md`](product-discovery.md).

**Proportional Dual Scoring (SEO/GEO).** Implemented, unreleased.

- Dual scores (`seo_score` and `geo_score`) are calculated using deterministic
  rule-based metrics.
- Ingestion, analysis, presentation renderers, and the `index.html` template
  support both scores and gracefully represent unmeasured dimensions as
  `null` (`Optional[float]`).
- [Decision 0011](decisions/0011-dual-scoring-supersedes-0003.md) records the
  rationale and supersedes decision 0003.
- The implementation is being evaluated before release.

- **Discontinuity note**: Discoverability scores (and thus total GEO scores) generated before this change are not comparable to new scores due to the formula shift from body/outgoing ratio to paragraph density.

**Topic introduction recommendation.** Implemented as a deterministic
editorial prototype.

- It evaluates title-term coverage in the opening passage.
- It produces an editor recommendation when coverage falls below the
  configured threshold.
- Its usefulness and threshold need evaluation on real publisher articles.

**Turkish interface edition.** Implemented and intentionally left uncommitted
because the requester prohibited git add/commit/push. Turkish is the static,
missing-preference, and invalid-preference default. The accessible TR/EN
switcher persists valid choices in `localStorage` and rerenders retained report
data without fetching or repeating analysis. Recommendation, draft-check, and
non-article outcome wording remains owned by Python presentation modules; the
web payload carries both supported renderings while source excerpts and numeric
results remain unchanged. Score-dimension detail panels are now rendered inside
their owning cards with independent accessible toggles and localized open/close
labels. Browser JavaScript verification is outstanding because Node is
unavailable.

## Blockers

No implementation blocker. The prototypes need evaluation on real publisher
articles before retaining or changing their thresholds.

## Verification

| Level                    | Status                                                                      |
| ------------------------ | --------------------------------------------------------------------------- |
| **tests pass**           | Yes — 345 passed, 19 skipped                                                |
| **served-page verified** | Unverified — breakdown type formatting and new discoverability score need browser verification |
| **feature complete**     | No — breakdown item separation and format changes completed but need full manual verification       |

Why a green suite is weaker than it looks — the structural reasons — is
recorded in [`architecture.md`](architecture.md). The vocabulary is in
[`../AGENTS.md`](../AGENTS.md) §3.

## Next actions

1. Run browser verification on the breakdown formatting (SCORE/COUNT/RATIO/MEASUREMENT separation) and new context visual dimming.
2. Evaluate the topic-introduction threshold on real publisher articles.
3. Retain, change, or remove the prototypes based on that evaluation; do not add further deterministic editorial recommendations before that review.
