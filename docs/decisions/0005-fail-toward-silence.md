# 0005 — Fail toward silence

## Decision

Where a rule could err, it errs toward reporting nothing. A false positive costs
an editor's trust; a missed finding costs less. Which way each rule errs is
documented beside it.

## Why

A report that misfires teaches an editor to distrust every finding in it,
including the correct ones. Trust is the product's scarcest resource and cannot
be restored one finding at a time.

## Evidence and context

- **Withdrawn after shipping — `skipped_heading_levels`.** Deterministic, and a
  gap in an outline is a real fault in principle. But measured against the TRT
  estate it found template furniture rather than outline faults on **four of six
  pages**: the heading of a legal-notice box on TRT Çocuk Ebeveyn Akademisi, and
  a "Diğer Haberler" related-articles widget on TRT Avaz. Both sit in
  class-named containers, which the containment rules cannot see
  ([0002](0002-no-publisher-specific-rules.md)). The check asked editors to
  renumber headings they did not write and cannot move.
- **Rejected for lack of evidence** — duplicate titles, image alt-text, FAQ
  detection. No occurrence to report, or no recommendation produced. TRT
  alt-text measured 6/6, 11/15 and 75/78 present.

## Documented exception

Title and description comparison deliberately errs the *other* way. Its module
docstring states the reasoning: a false positive asks an editor to look at a
headline that turns out to be fine, while a false negative leaves a real
mismatch on the site. See [0009](0009-anchor-title-comparison-on-whole-values.md).

This exception is local and stated, not a precedent. Any new rule that wants it
must argue for it in the same terms.

## Consequences

A check that cannot distinguish a real fault from template furniture is
withdrawn rather than tuned. Coverage is deliberately lower than it could be.

## Reopen when

A withdrawn check becomes distinguishable from furniture. `skipped_heading_levels`
can return once a heading can be tied to body text already known to be
boilerplate.
