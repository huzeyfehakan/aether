# 0002 — No publisher-specific rules

## Decision

Nothing keys on a publisher name, hostname, or URL pattern.

## Why

A rule that recognises TRT stops working for the next publisher and hides its
own assumptions. It also cannot be validated: a finding that only fires for one
estate cannot be tested against another.

## Evidence and context

- A site name appended to a title is recognised structurally — a
  separator-delimited segment that another declaration lacks — not from a list
  of publishers. See `declared_text_comparison.py` and
  [0009](0009-anchor-title-comparison-on-whole-values.md).
- Body extraction excludes HTML sectioning elements (`a`, `aside`,
  `figcaption`, `footer`, `header`, `nav`) by specification, never by class
  name, publisher, or URL pattern.

## Consequences

- Some real TRT template furniture is invisible, because it sits in class-named
  containers rather than semantic ones. This is the direct cause of the
  withdrawal recorded in [0005](0005-fail-toward-silence.md).
- `Article.publisher` is a free-text grouping key, defaulted to the hostname
  with `www.` removed when the caller supplies none. It is not an entity, has no
  hierarchy, and does not model TRT's properties.

## Reopen when

Not for convenience. Only if the product's scope narrows to a single publisher
by an explicit product decision — which would also invalidate the
cross-publisher comparison design.
