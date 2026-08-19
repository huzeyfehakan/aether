"""Sentence-level rules for reading a passage on its own.

A retrieval system does not read an article. It reads a fragment of one, pulled
out of order and shown without the paragraphs around it. Two questions follow,
and this module answers only the observable half of each.

**Does a passage open by defining something?** A definition-shaped opening is a
fact about the sentence's construction: it asks *what X is*, it predicates X
with a copula, or it names the act of defining. Each rule below matches a
construction, and each match reports which construction it was.

**Can a sentence be read alone?** This one cannot be measured, and the module
does not claim to. Whether a sentence carries its meaning without its neighbours
is a judgement about writing, and no rule here is entitled to make it.

What *can* be established is the opposite: a sentence that opens with an
anaphoric or deictic marker -- *bu*, *o*, *söz konusu*, *this*, *such* -- points
at something outside itself, and that pointing is present in the text. So the
rules run in that direction. A sentence carrying such a marker is reported as
context-dependent, together with the marker that established it. A sentence
carrying none is reported as an anchor *candidate*: nothing was found that ties
it to its neighbours, which is weaker than saying it stands alone, and the name
says so.

This is decision 0005 applied to a linguistic rule. Reporting "this sentence is
self-contained" would be a claim the module cannot defend when it is wrong.
Reporting "this sentence begins with *bu*" is a fact an editor can check in one
glance.

Rejected: scoring or ranking anchor candidates
----------------------------------------------
An obvious next step is to rate candidates -- by length, by whether they carry a
named entity, by how many markers they lack. Every version of it needs a
threshold to say which rating is good enough, which decision 0001 forbids, and
every version reads as a prediction about what a retrieval system will select,
which decision 0003 forbids. The signals are reported per sentence and left
uncombined.

Rejected: a curated abbreviation list for sentence splitting
-------------------------------------------------------------
Splitting on terminal punctuation divides ``Dr. Ahmet geldi.`` into two
sentences. The fix is a list of abbreviations, which is a per-language editorial
artefact that grows without end and differs per desk. The splitter instead
requires whitespace after the terminator, which already keeps ``12.05.2026`` and
``%12.5`` whole, and the residual over-splitting is reported honestly: an
over-split fragment simply appears as its own sentence, and a fragment beginning
with a name carries no context marker, so it becomes a candidate rather than a
false context-dependency. The error direction was chosen deliberately.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple


#: Terminal punctuation followed by whitespace. The lookbehind keeps the
#: punctuation with the sentence it ends, and the required whitespace is what
#: keeps decimal numbers, dotted dates and ellipses inside a sentence intact.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?\u2026])\s+")


def split_sentences(text: str) -> Tuple[str, ...]:
    """Split passage text into sentences on terminal punctuation.

    Whitespace is normalized first so that a passage stored with line breaks
    yields the same sentences as one stored on a single line.
    """
    normalized = " ".join(text.split())
    if not normalized:
        return ()
    return tuple(
        fragment for fragment in _SENTENCE_BOUNDARY.split(normalized) if fragment
    )


def primary_language_subtag(language: str) -> str:
    """Return the lowercase primary subtag of a BCP 47 language tag.

    ``tr``, ``tr-TR`` and ``TR_tr`` all resolve to ``tr``. A tag this module
    has no rules for resolves to itself and simply matches nothing, which is
    the silent direction (decision 0005).
    """
    return language.strip().lower().replace("_", "-").split("-", 1)[0]


@dataclass(frozen=True)
class DefinitionOpening:
    """The definition-shaped construction a passage opened with."""

    #: Which rule matched: ``question_form``, ``copular_predicate`` or
    #: ``explicit_definition``. The name is a code, not wording; presentation
    #: owns how it reads (decision 0007).
    construction: str
    #: The sentence the construction was found in, so a reader can check it.
    sentence: str


@dataclass(frozen=True)
class SentenceSignal:
    """One sentence of a passage, and what was found in it."""

    ordinal: int
    text: str
    #: Sentence-initial markers pointing outside the sentence. Empty means no
    #: marker was found -- not that the sentence was judged self-contained.
    context_markers: Tuple[str, ...] = ()

    @property
    def is_context_dependent(self) -> bool:
        """Whether a marker tying this sentence to its neighbours was found."""
        return bool(self.context_markers)

    @property
    def is_anchor_candidate(self) -> bool:
        """Whether nothing was found tying this sentence to its neighbours.

        A candidate, deliberately. The absence of a marker is evidence that no
        dependency was detected, not evidence that none exists.
        """
        return not self.context_markers


# --------------------------------------------------------------------------
# Context markers
#
# Sentence-initial anaphora, deixis and discourse connectives. Every entry
# points at something the sentence does not itself contain: a referent named
# earlier, or a preceding proposition the connective relates to.
#
# Matched at the start of a sentence only. A pronoun in the middle of a
# sentence usually refers to a subject the same sentence introduced, so
# matching everywhere would report dependencies that are not there.
# --------------------------------------------------------------------------

_CONTEXT_MARKERS = {
    "tr": (
        # Demonstratives and their inflections
        "bu", "bunu", "bunun", "buna", "bundan", "bunda", "bunlar", "bunları",
        "bunların", "bunlara", "bunlardan", "şu", "şunu", "şunun", "şunlar",
        "o", "onu", "onun", "ona", "ondan", "onlar", "onları", "onların",
        # Deictic noun phrases
        "söz konusu", "ilgili", "aynı", "böyle", "böylesi", "bu durumda",
        "bu nedenle", "bu yüzden", "bu sayede", "bu bağlamda", "bu süreçte",
        "bu arada", "o dönemde", "o tarihte", "aynı şekilde", "aynı dönemde",
        # Discourse connectives relating to a preceding proposition
        "ancak", "fakat", "ama", "ayrıca", "üstelik", "dolayısıyla",
        "böylece", "buna karşın", "buna rağmen", "bununla birlikte",
        "öte yandan", "oysa", "oysaki", "nitekim", "yine de", "yine",
        "sonuç olarak", "kısacası", "özetle", "daha sonra", "sonrasında",
        "ardından", "önceki", "yukarıda", "aksi halde", "aksine",
    ),
    "en": (
        "this", "that", "these", "those", "it", "its", "they", "them",
        "their", "he", "she", "his", "her", "such", "the former",
        "the latter", "the same", "however", "therefore", "thus", "hence",
        "also", "moreover", "furthermore", "additionally", "meanwhile",
        "instead", "consequently", "besides", "nevertheless", "nonetheless",
        "afterwards", "then", "there", "in contrast", "on the other hand",
        "as a result", "in this case", "at the time",
    ),
}


def _marker_pattern(markers: Tuple[str, ...]) -> "re.Pattern[str]":
    """Anchor the markers at a sentence start, longest alternative first.

    Ordering by descending length is what makes ``bu nedenle`` match as itself
    rather than as ``bu``: Python's alternation takes the first alternative
    that matches, not the longest.
    """
    ordered = sorted(markers, key=len, reverse=True)
    alternatives = "|".join(re.escape(marker) for marker in ordered)
    return re.compile(r"^(?:%s)(?![\w'\u2019])" % alternatives, re.IGNORECASE)


_MARKER_PATTERNS = {
    language: _marker_pattern(markers)
    for language, markers in _CONTEXT_MARKERS.items()
}

#: Leading punctuation and quotation marks a sentence may open with. Stripped
#: before marker matching so that a quoted sentence is read like any other.
_LEADING_NOISE = re.compile(r"^[\s\"'\u2018\u2019\u201c\u201d\u00ab\u00bb\(\[\u2014\u2013-]+")


def context_markers_in(sentence: str, language: str) -> Tuple[str, ...]:
    """Return the sentence-initial context markers found, lowercased.

    At most one marker is reported: the construction at the start of the
    sentence is a single thing, and reporting a marker's own prefix alongside
    it would double-count one observation. The return type stays a tuple so a
    later rule may report more than one without changing every reader.
    """
    pattern = _MARKER_PATTERNS.get(primary_language_subtag(language))
    if pattern is None:
        return ()
    stripped = _LEADING_NOISE.sub("", sentence)
    match = pattern.match(stripped)
    if match is None:
        return ()
    return (match.group(0).lower(),)


# --------------------------------------------------------------------------
# Definition-shaped openings
#
# Three constructions, each a fact about the sentence rather than about its
# subject matter. A sentence may satisfy more than one; the first in this
# order is reported, so the same sentence always yields the same construction.
# --------------------------------------------------------------------------

_DEFINITION_RULES = {
    "tr": (
        (
            "question_form",
            re.compile(
                r"\b(nedir|ne demek|ne demektir|kimdir|nelerdir|neresidir|"
                r"nasıl tanımlanır|ne anlama gelir)\b\s*[?？]?",
                re.IGNORECASE,
            ),
        ),
        (
            "explicit_definition",
            re.compile(
                r"\b(olarak tanımlan\w*|şeklinde tanımlan\w*|olarak adlandırıl\w*|"
                r"olarak bilin\w*|olarak ifade edil\w*|anlamına gel\w*|"
                r"demektir|tanımı şudur|olarak geçer)\b",
                re.IGNORECASE,
            ),
        ),
        (
            # "X, ... bir Y'dir." -- a subject set off by a comma and closed by
            # the copular suffix. The comma is required: without it the pattern
            # matches almost any Turkish declarative sentence, since -dir is not
            # restricted to definitions.
            "copular_predicate",
            re.compile(
                r"^[^,]{1,120},\s.*(dır|dir|dur|dür|tır|tir|tur|tür)\s*[.!]?$",
                re.IGNORECASE,
            ),
        ),
    ),
    "en": (
        (
            "question_form",
            re.compile(r"^what\s+(is|are|was|were)\b.*\?$", re.IGNORECASE),
        ),
        (
            "explicit_definition",
            re.compile(
                r"\b(is defined as|are defined as|is known as|are known as|"
                r"refers to|refer to|is called|are called|means that|"
                r"is the term for)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "copular_predicate",
            re.compile(
                r"^[A-Z\u00c0-\u00dc][^.!?]{0,120}?\s(is|are)\s+(a|an|the)\s",
            ),
        ),
    ),
}


def definition_opening(sentence: str, language: str) -> Optional[DefinitionOpening]:
    """Return the definition construction this sentence opens with, if any.

    Only the sentence handed in is examined. Callers pass a passage's *first*
    sentence, because the signal asked for is a passage that *begins* by
    defining something -- a definition buried in the middle of a paragraph does
    not give a retrieved fragment its subject.
    """
    rules = _DEFINITION_RULES.get(primary_language_subtag(language))
    if not rules:
        return None
    normalized = " ".join(sentence.split())
    if not normalized:
        return None
    for construction, pattern in rules:
        if pattern.search(normalized):
            return DefinitionOpening(construction=construction, sentence=normalized)
    return None
