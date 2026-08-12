# 0009 — Anchor title comparison on whole declared values

## Decision

Two declared values agree when, after normalization, they are equal, or one
value *whole* equals the other with a single leading or trailing
separator-delimited segment removed. A form shared by every declaration must
itself stand alone as one of the declarations.

## Why

Comparing declarations literally would report a disagreement on almost every
page: one is entity-escaped, another is not; one carries the site name, another
does not.

**Rejected — matching any title fragment against any other.** It would let two
different headlines agree merely by sharing a site name, in either position:
"Story - Site" against "Other - Site", or "Site - Story" against "Site - Other".
Requiring the shared form to stand alone somewhere is what prevents this.

## Evidence and context

`declared_text_comparison.py`. Normalization decodes character references,
collapses whitespace, writes padded separators one way, and case-folds. The
module documents its measured limitations rather than hiding them:

- **False positives:** breadcrumb titles (only one segment is removed, so
  "Site - Section - Headline" never reduces to "Headline"); typographic
  variants; unpadded separators; truncated declarations; zero-width characters;
  the Turkish dotless i.
- **False negatives:** a headline that itself contains a padded separator; a page
  declaring only one title, which cannot disagree with itself.

## Consequences

A publisher using two-level breadcrumb titles is flagged on every article, and a
clean third declaration does not rescue it. This is the documented exception to
[0005](0005-fail-toward-silence.md): the module deliberately errs toward the
false positive, on the stated grounds that a real mismatch left on the site
costs more than an editor looking at a headline that turns out to be fine.

## Reopen when

Editors report breadcrumb false positives in practice, or a normalization exists
that resolves the Turkish dotless i without corrupting other languages.
