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

The first deterministic `WEAK_ARTICLE_OPENING` editor recommendation is
implemented. It reports an article or draft with at least 150 total
passage-profile words when its first passage has 20 words or fewer.

## Released

Latest release: `v2.0.1`. See [`../README.md`](../README.md) for shipped
capabilities.

## In progress

No other product work is in progress.

## Blockers

No implementation blocker. The prototype needs evaluation on real publisher
articles before retaining or changing its thresholds; see
[decision 0010](decisions/0010-thresholded-article-opening-prototype.md).

## Verification

| Level | Status |
|---|---|
| **tests pass** | Yes — 209 tests, 6 skipped |
| **served-page verified** | Not needed — no UI or browser code changed |
| **feature complete** | Yes — the recommendation is derived and uses the existing presentation flow |

## Next actions

1. Evaluate the weak-opening thresholds on real publisher articles.
2. Retain, change, or remove the prototype based on that evaluation; do not add
   further deterministic editorial recommendations before that review.
