# 0010 — Thresholded article-opening prototype

## Decision

As a narrowly bounded prototype, report `WEAK_ARTICLE_OPENING` when an
article has at least 150 words across its passage profiles and its first
passage has 20 words or fewer.

## Why

The product owner requested this deterministic content-structure check for
evaluation on real publisher articles. It identifies only the measured shape
of an article; it does not predict how any AI system will handle it.

## Evidence and context

This is an explicit, limited exception to [decision 0001](0001-deterministic-rules-without-thresholds.md).
The thresholds are supplied for this prototype, not inferred from model
behaviour or represented as a score. The rule reuses existing passage-quality
profiles and errs toward silence below the substantial-article threshold.

## Consequences

The recommendation is deterministic and addressed to an editor. It applies to
both published articles and drafts, because both provide passage profiles. No
new extraction, scoring, or prediction capability is introduced.

## Reopen when

Real publisher-article evaluation establishes that either threshold produces
unhelpful recommendations, or the prototype should be retained, changed, or
removed.
