# Decision records

Permanent product decisions and the reasoning behind them. A record here is
settled: it does not change when the repository changes, and it is not a place
for current state.

Every record has the same five parts — **decision**, **why**, **evidence and
context**, **consequences**, and **reopen when**. The last one matters most: a
decision without a stated reopening condition becomes dogma.

## How to use these

- **Before changing analysis behaviour**, read the records that touch it. They
  record what was already tried and measured, so an idea is not re-proposed
  without new evidence.
- **To change a decision**, do not edit history: state the new decision, its
  evidence, and mark the superseded record. Reopening conditions are the
  intended route.
- **Do not record undecided things here.** An open question belongs in
  [`../product-discovery.md`](../product-discovery.md) until it is settled.

## Index

| # | Decision |
|---|---|
| [0001](0001-deterministic-rules-without-thresholds.md) | Deterministic rules, without chosen thresholds |
| [0002](0002-no-publisher-specific-rules.md) | No publisher-specific rules |
| [0003](0003-never-predict-model-behaviour.md) | Never predict model behaviour |
| [0004](0004-every-finding-names-who-can-act.md) | Every finding names who can act on it |
| [0005](0005-fail-toward-silence.md) | Fail toward silence |
| [0006](0006-turkish-is-the-default-interface.md) | Turkish is the default interface language |
| [0007](0007-separate-finding-codes-from-wording.md) | Separate finding codes from their wording |
| [0008](0008-classify-pages-from-declared-article-nodes.md) | Classify pages from declared Article nodes, never from `og:type` |
| [0009](0009-anchor-title-comparison-on-whole-values.md) | Anchor title comparison on whole declared values |
| [0010](0010-dual-scoring-supersedes-0003.md) | Dual Scoring System (SEO and GEO) |

## Rejected ideas, and where they live

Each rejection sits with the decision that replaced it, so the reasoning is
found where the rule is read.

| Rejected | Recorded in |
|---|---|
| "This article has no subheadings" | [0001](0001-deterministic-rules-without-thresholds.md) |
| `skipped_heading_levels` (withdrawn after shipping) | [0005](0005-fail-toward-silence.md) |
| Duplicate titles, image alt-text, FAQ detection | [0005](0005-fail-toward-silence.md) |
| An English-first interface with Turkish as an option | [0006](0006-turkish-is-the-default-interface.md) |
| `og:type` for classifying pages | [0008](0008-classify-pages-from-declared-article-nodes.md) |
| Matching any title fragment against any other | [0009](0009-anchor-title-comparison-on-whole-values.md) |
