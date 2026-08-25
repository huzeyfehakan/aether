# 0004 — Every finding names who can act on it

## Decision

Every finding carries a category naming who can act on it: **editor** or
**technical**. A finding nobody can act on is not reported at all.

## Why

An editor can change what an article says today. Changing how the page is built
— its markup, its declarations, its template — needs the CMS or engineering, and
usually fixes every article at once. Mixing the two buries the few things an
editor can fix among many things they cannot, which is the fastest way to make a
report ignored.

## Evidence and context

- `RecommendationCategory` is `EDITOR | TECHNICAL`, assigned per code in
  `_CATEGORIES` in `derive_editor_recommendations.py`.
- Structured data is **technical**: it is declared by the page template, so the
  fix lands once for every article.
- Repeated text is **editor**: the editor owns the body and is the person who
  sees the paragraph. Whether the remedy is theirs or the CMS team's depends on
  how the text got there, which the markup does not reveal, so the wording names
  both paths rather than guessing.
- Measurements deleted for producing no action: summary statistics over passage
  lengths (`analyze_passage_quality.py`); and title, canonical URL and language
  availability, which the domain makes impossible to miss, so reporting them
  could only ever say "yes".

## Consequences

Adding a measurement is not sufficient to add a finding. A finding must name a
concrete action and an owner, or it does not ship.

## Reopen when

Editors report that the split is wrong for a specific finding — "that is not my
job". That is evidence the audience assignment is wrong for that finding, not
that the finding is wrong.

One unresolved input: whether TRT editors control per-article structured data in
the CMS, or only engineering. If editors do control it, several findings
currently filed under technical belong to them. Recorded as an open question in
[`../product-discovery.md`](../product-discovery.md).
