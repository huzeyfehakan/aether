"""Decide whether two declared titles carry the same headline.

A page states its title in several places and they rarely match character for
character. One is entity-escaped, another is not; one carries the site name,
another does not. Comparing them literally would report a disagreement on
almost every page, which is useless. Comparing them loosely would miss a page
that genuinely states two different headlines.

The comparison is therefore staged. Values are first normalized for
differences that carry no meaning: character references are decoded,
whitespace is collapsed, padded separators are written one way, and case is
folded. Two normalized values then agree if either

1. they are equal, or
2. one value, whole, equals the other with a single leading or trailing
   separator-delimited segment removed.

Nothing here knows any publisher's name. A site name is recognised only by
being a separator-delimited segment that the other declaration does not have,
so the same rule handles a suffix, a prefix, or neither, with no list of
publishers and no length threshold.

The second test is anchored on one *whole* value deliberately. Matching any
fragment against any fragment would let two different headlines agree merely
by sharing a site name, in either position: "Story - Site" against
"Other - Site", or "Site - Story" against "Site - Other".

Known limitation: a headline that itself contains a padded separator, such as
"Erdogan - Putin meeting", also yields fragments, so two titles can agree that
a person would call different. That failure is towards silence rather than
towards a false accusation, which is the safer direction for a report an
editor is asked to trust.
"""

from html import unescape
from typing import Iterable, Optional, Set

#: Separators publishers pad with spaces when appending a site name. The
#: padding is required: an unpadded hyphen or colon is ordinary punctuation
#: inside a headline. All are written as the first form before comparison, so
#: a page that punctuates the same headline two ways still agrees with itself.
_CANONICAL_SEPARATOR = " - "
_SEPARATORS = (" - ", " – ", " — ", " | ", " · ")


def normalize_title(value: str) -> str:
    """Reduce a declared title to its comparable form.

    Character references are decoded because structured data lives inside a
    script element, where the HTML parser leaves them raw while every other
    source arrives decoded. Case is folded rather than lowercased so the
    result does not depend on the machine's locale.

    Folding a dotted capital I leaves a combining dot behind, which never
    appears in typed text, so it is dropped. The dotless Turkish i is a
    genuine limit rather than an artifact: folding maps both I and ı towards
    i only under a Turkish locale, and applying that rule would corrupt every
    other language. A title declared in one place in capitals and elsewhere in
    lower case may therefore be reported as different.
    """
    normalized = " ".join(unescape(value).split()).casefold()
    normalized = normalized.replace("̇", "")
    for separator in _SEPARATORS:
        normalized = normalized.replace(separator, _CANONICAL_SEPARATOR)
    return normalized


def _without_trailing_segment(normalized: str) -> Optional[str]:
    """The value with its last separator-delimited segment removed."""
    head = normalized.rpartition(_CANONICAL_SEPARATOR)[0].strip()
    return head or None


def _without_leading_segment(normalized: str) -> Optional[str]:
    """The value with its first separator-delimited segment removed."""
    tail = normalized.partition(_CANONICAL_SEPARATOR)[2].strip()
    return tail or None


def _forms(normalized: str) -> Set[str]:
    """The whole value plus each single-segment reduction of it."""
    forms = {normalized}
    for reduced in (
        _without_trailing_segment(normalized),
        _without_leading_segment(normalized),
    ):
        if reduced:
            forms.add(reduced)
    return forms


def all_titles_agree(values: Iterable[str]) -> bool:
    """Whether every declared title states the same headline.

    Declarations are compared together rather than in pairs. A page may put
    the site name at the end of one title and the front of another, so no two
    of them match while all three still carry one headline; comparing pairwise
    would call that a disagreement.

    A headline is a form shared by every declaration that is also, on its own,
    one of the declarations. Requiring the shared form to stand alone somewhere
    is what stops a site name from passing as the headline: "Story - Site" and
    "Other - Site" share the form "site", but neither page ever declares "site"
    by itself, so they disagree.
    """
    declared = [normalize_title(value) for value in values]
    declared = [value for value in declared if value]
    if len(declared) < 2:
        return True
    shared = set.intersection(*(_forms(value) for value in declared))
    return bool(shared & set(declared))


def titles_agree(first: str, second: str) -> bool:
    """Whether two declared titles state the same headline."""
    return all_titles_agree((first, second))
