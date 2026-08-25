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

No implementation blocker. The prototypes need evaluation on real publisher articles before retaining or changing their thresholds.

## Verification

| Level                    | Status                                                                      |
| ------------------------ | --------------------------------------------------------------------------- |
| **tests pass**           | Yes — 231 passed, 6 skipped                                                 |
| **served-page verified** | No — the merged behaviour still needs integrated browser verification       |
| **feature complete**     | Yes — BULGU-0 (Incomplete Body Capture) is fixed, GEO scoring is finalized. |

Why a green suite is weaker than it looks — the structural reasons — is
recorded in [`architecture.md`](architecture.md). The vocabulary is in
[`../AGENTS.md`](../AGENTS.md) §3.

## Next actions

1. Review the integrated SEO/GEO Score implementation on the frontend, ensuring the new `INCOMPLETE_BODY_CAPTURE` recommendation is properly visible.
2. Evaluate the topic-introduction threshold on real publisher articles.
3. Clean up any remaining Turkish language presentation inconsistencies as requested, avoiding ternaries inside presentation components.
