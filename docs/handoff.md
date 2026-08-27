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

**Topic introduction recommendation.** Implemented as a deterministic
editorial prototype.

- It evaluates title-term coverage in the opening passage.
- It produces an editor recommendation when coverage falls below the
  configured threshold.
- Its usefulness and threshold need evaluation on real publisher articles.

**Turkish interface edition.** Uncommitted, and not ready to land.

- Working: negotiation is `X-Aether-Language` → `Accept-Language` → Turkish;
  every user-facing surface has Turkish wording; the manual TR/EN switcher
  persists to `localStorage` and beats the browser preference.
- Not yet consistent: about half the translations are second lookup tables as
  designed. The rest are inline `if language is TURKISH else` ternaries and
  dicts rebuilt inside function bodies — roughly twenty in the plain-text
  renderer, four in `_report_view`, two helpers in
  `editor_recommendation_text.py`. The four in `_report_view` violate
  [decision 0007](decisions/0007-separate-finding-codes-from-wording.md) and are
  the reason this has not landed.
- The interface language module is not yet part of the committed tree.

## Blockers

No implementation blocker. The prototypes need evaluation on real publisher
articles before retaining or changing their thresholds.

## Verification

| Level                    | Status                                                                      |
| ------------------------ | --------------------------------------------------------------------------- |
| **tests pass**           | Yes — 203 passed, 6 skipped                                                 |
| **served-page verified** | Yes — the score and recommendation behaviours have been verified separately |
| **feature complete**     | No — the merged behaviour still needs integrated browser verification       |

Why a green suite is weaker than it looks — the structural reasons — is
recorded in [`architecture.md`](architecture.md). The vocabulary is in
[`../AGENTS.md`](../AGENTS.md) §3.

## Next actions

1. Verify the merged SEO/GEO score and editor recommendation behaviour together
   on real publisher articles.
2. Evaluate the topic-introduction threshold on those articles.
3. Retain, change, or remove the prototypes based on that evaluation; do not
   add further deterministic editorial recommendations before that review.
