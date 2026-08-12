# 0001 — Deterministic rules, without chosen thresholds

## Decision

Every rule produces the same result for the same input and the same corpus.
Where a rule needs a comparison, it compares two measured quantities against
each other, never against a constant someone chose.

## Why

A threshold is a judgement disguised as a measurement. It cannot be defended
when an editor asks why that number, it differs per desk and per language, and
it makes the report's behaviour depend on a figure nobody can justify.

## Evidence and context

- `ContentDuplicationAnalysis.is_mostly_repeated` compares `repeated_word_count`
  against `unique_word_count`. A body is "mostly boilerplate" when its shared
  words outnumber its own, at any length. A short article of its own writing is
  never reported; a long one padded with standing notices is.
- **Rejected — "this article has no subheadings."** TRT World would trigger it
  (670 words, no headings of any level). It cannot be stated without a length
  threshold: a three-paragraph note needs no subheadings and a long feature
  does, and the boundary between them is a judgement about writing. The absence
  of a *top-level* heading is reported instead, which is a fact about markup.
- **Rejected — a numeric readiness score.** Deliberate from the outset. See
  [0003](0003-never-predict-model-behaviour.md).

## Consequences

- Near-duplicate detection cannot currently be expressed. Every similarity
  measure — shingling, MinHash, cosine, edit distance — ends in "similar enough
  means ≥ k". If near-duplicate detection turns out to be required, this
  decision must be amended explicitly rather than drifted past. See
  [`../product-discovery.md`](../product-discovery.md).
- Determinism holds for a *fixed corpus*. The corpus itself is process-scoped
  and submission-ordered, so the same page analysed first and last in a session
  can yield different cross-article findings. That is a property of the
  in-memory repository, not of the rules.

## Reopen when

A confirmed, editor-evidenced capability cannot be expressed without a
threshold. Reopening requires naming the threshold, its measured basis, and the
sentence shown to an editor who asks why that number.
