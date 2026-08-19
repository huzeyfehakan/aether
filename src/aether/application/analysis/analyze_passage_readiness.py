"""How an article divides, and what each division states on its own.

A retrieval system reads fragments. It takes a piece of an article, out of
order and without the paragraphs around it, and decides from that piece alone
whether the article answers a question. This analysis reports what those
fragments look like.

It reports and stops. There is no score, no combined signal, and no
classification of a passage or a section as good or bad. Every field is a
measurement or a located quotation, and each one names the text it came from so
that an editor can check it in one glance.

What it composes rather than recomputes
---------------------------------------
Section membership needs the article's outline and its paragraph lengths, and
both are already measured. ``AnalyzeHeadingStructure`` supplies the declared
outline; ``AnalyzePassageQuality`` supplies the per-paragraph word counts. This
use case executes both and joins their results, so a change to how a heading is
selected or a word counted lands here without being restated.

What it reads directly is passage *text*, which neither result carries, and
which the sentence rules need.

How sections are established
----------------------------
Each declared heading carries the number of body paragraphs that preceded it
(``DeclaredHeading.body_position``). Sections follow from that ordering and
nothing else: a heading owns the passages between its own position and the next
heading's.

Two cases are reported rather than smoothed over, because both are facts about
the markup:

* Paragraphs before the first heading form a section with no heading. This is
  ordinary -- most articles open with prose -- and is not a fault.
* Two headings declaring the same position leave the earlier one owning no
  passages. In markup that is two consecutive headings with nothing between
  them. In a snapshot assembled without positional information it is instead an
  artefact of the missing positions, and the empty sections say so plainly.

Deliberately not decided here
-----------------------------
**Whether the headings divide the article well.** The task this analysis serves
asks whether headings "really split the content into meaningful sections", and
the honest answer is that meaningfulness is not established from markup. What is
established -- how many passages and words each section holds, which sections
hold none, and how many passages precede any heading -- is reported per section,
and the judgement is left to the reader.

That restraint is not caution for its own sake. ``skipped_heading_levels``
shipped as a heading-quality rule and was withdrawn: measured against the TRT
estate it found template furniture rather than outline faults on four of six
pages (decision 0005). A rule about heading quality that cannot see template
furniture will misfire the same way, and nothing here can see it yet.

**Whether any of this becomes a finding.** Turning a measurement into advice
happens in ``derive_editor_recommendations.py`` and nowhere else, and only once
a measurement has an owner and an action (decision 0004). None of these signals
has been through that test.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from aether.application.analysis.analyze_heading_structure import (
    AnalyzeHeadingStructure,
    HeadingStructureAnalysis,
)
from aether.application.analysis.analyze_passage_quality import (
    AnalyzePassageQuality,
    PassageQualityAnalysis,
)
from aether.application.analysis.passage_sentence_rules import (
    DefinitionOpening,
    SentenceSignal,
    context_markers_in,
    definition_opening,
    split_sentences,
)
from aether.domain.common import DomainValidationError
from aether.domain.content import Article, Passage
from aether.domain.source_data import DeclaredHeading
from aether.ports.outbound.content_repository import ContentRepository


@dataclass(frozen=True)
class PassageReadinessProfile:
    """One passage, as a retrieval system would receive it: on its own."""

    passage_id: str
    ordinal_position: int
    #: The section this passage belongs to, by ordinal. Always resolves: a
    #: passage before the first heading belongs to the untitled leading section.
    section_ordinal: int
    word_count: int
    #: The passage text, retained so every signal below can be traced to it.
    text: str
    sentences: Tuple[SentenceSignal, ...]
    #: The definition-shaped construction the passage opened with, if any.
    definition_opening: Optional[DefinitionOpening] = None

    @property
    def opens_with_definition(self) -> bool:
        return self.definition_opening is not None

    @property
    def anchor_candidate_sentences(self) -> Tuple[SentenceSignal, ...]:
        """Sentences in which no tie to neighbouring text was found."""
        return tuple(
            sentence for sentence in self.sentences if sentence.is_anchor_candidate
        )

    @property
    def context_dependent_sentences(self) -> Tuple[SentenceSignal, ...]:
        """Sentences that open by pointing at text outside themselves."""
        return tuple(
            sentence for sentence in self.sentences if sentence.is_context_dependent
        )

    @property
    def sentence_count(self) -> int:
        return len(self.sentences)


@dataclass(frozen=True)
class SectionProfile:
    """One division of the article, and the passages it holds."""

    ordinal: int
    #: ``None`` for the leading section of an article that opens with prose.
    heading_level: Optional[int]
    heading_text: Optional[str]
    passage_ordinals: Tuple[int, ...]
    word_count: int

    @property
    def has_heading(self) -> bool:
        return self.heading_text is not None

    @property
    def passage_count(self) -> int:
        return len(self.passage_ordinals)

    @property
    def is_empty(self) -> bool:
        """Whether this section's heading is followed by no passages of its own."""
        return not self.passage_ordinals


@dataclass(frozen=True)
class PassageReadinessAnalysis:
    """Raw section and passage signals for one immutable Article Version.

    Nothing here is summarized into a single value. The counts a reader is
    likely to want are exposed as properties over the same records, so a
    presentation layer never has to recount and never disagrees.
    """

    article_id: str
    article_version_id: str
    sections: Tuple[SectionProfile, ...]
    passage_profiles: Tuple[PassageReadinessProfile, ...]

    @property
    def section_count(self) -> int:
        return len(self.sections)

    @property
    def passages_before_first_heading(self) -> int:
        """Passages that precede every declared heading.

        Zero when the article opens with a heading, and equal to the passage
        count when it declares no headings at all.
        """
        leading = [section for section in self.sections if not section.has_heading]
        return sum(section.passage_count for section in leading)

    @property
    def empty_sections(self) -> Tuple[SectionProfile, ...]:
        """Headed sections holding no passages of their own."""
        return tuple(
            section
            for section in self.sections
            if section.has_heading and section.is_empty
        )

    @property
    def definition_opening_profiles(self) -> Tuple[PassageReadinessProfile, ...]:
        return tuple(
            profile for profile in self.passage_profiles if profile.opens_with_definition
        )


class AnalyzePassageReadiness:
    """Join the declared outline to the stored passages, and read each alone."""

    def __init__(
        self,
        content_repository: ContentRepository,
        heading_structure_analysis: AnalyzeHeadingStructure,
        passage_quality_analysis: AnalyzePassageQuality,
    ) -> None:
        self._content_repository = content_repository
        self._heading_structure_analysis = heading_structure_analysis
        self._passage_quality_analysis = passage_quality_analysis

    def execute(
        self, article: Article, article_version_id: str
    ) -> PassageReadinessAnalysis:
        article_version = self._content_repository.get_article_version(
            article_version_id
        )
        if article_version.article_id != article.article_id:
            raise DomainValidationError(
                "article version must belong to the article being analyzed"
            )

        headings = self._heading_structure_analysis.execute(
            article, article_version_id
        )
        quality = self._passage_quality_analysis.execute(article, article_version_id)
        passages = tuple(
            sorted(
                self._content_repository.list_passages_for_version(article_version_id),
                key=lambda passage: passage.ordinal_position,
            )
        )
        if any(
            passage.article_version_id != article_version.article_version_id
            for passage in passages
        ):
            raise DomainValidationError(
                "analysis passages must belong to the analyzed article version"
            )

        section_by_passage = self._assign_sections(headings, passages)
        profiles = tuple(
            self._profile(passage, section_by_passage[passage.ordinal_position], quality)
            for passage in passages
        )
        return PassageReadinessAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            sections=self._sections(headings, passages, section_by_passage, quality),
            passage_profiles=profiles,
        )

    # -- sectioning --------------------------------------------------------

    @staticmethod
    def _boundaries(
        headings: HeadingStructureAnalysis, passage_count: int
    ) -> Tuple[Tuple[Optional[DeclaredHeading], int, int], ...]:
        """Return each section as ``(heading, first passage, last passage + 1)``.

        Headings are taken in the order the outline declares them, which is
        document order. A position beyond the last passage is clamped, so a
        heading declared after all the body -- and a snapshot whose positions
        were never recorded -- yields an empty section rather than an error.
        """
        declared = headings.headings
        spans = []
        first_position = (
            min(passage_count, declared[0].body_position) if declared else passage_count
        )
        if first_position > 0 or not declared:
            spans.append((None, 0, first_position))
        for index, heading in enumerate(declared):
            start = min(passage_count, heading.body_position)
            end = (
                min(passage_count, declared[index + 1].body_position)
                if index + 1 < len(declared)
                else passage_count
            )
            spans.append((heading, start, max(start, end)))
        return tuple(spans)

    @classmethod
    def _assign_sections(
        cls, headings: HeadingStructureAnalysis, passages: Tuple[Passage, ...]
    ) -> Dict[int, int]:
        """Map each passage's ordinal to the ordinal of the section holding it."""
        assignment: Dict[int, int] = {}
        for ordinal, (_, start, end) in enumerate(
            cls._boundaries(headings, len(passages))
        ):
            for position in range(start, end):
                assignment[passages[position].ordinal_position] = ordinal
        return assignment

    @classmethod
    def _sections(
        cls,
        headings: HeadingStructureAnalysis,
        passages: Tuple[Passage, ...],
        section_by_passage: Dict[int, int],
        quality: PassageQualityAnalysis,
    ) -> Tuple[SectionProfile, ...]:
        words = {
            profile.ordinal_position: profile.word_count
            for profile in quality.passage_profiles
        }
        sections = []
        for ordinal, (heading, _, _) in enumerate(
            cls._boundaries(headings, len(passages))
        ):
            ordinals = tuple(
                passage.ordinal_position
                for passage in passages
                if section_by_passage.get(passage.ordinal_position) == ordinal
            )
            sections.append(
                SectionProfile(
                    ordinal=ordinal,
                    heading_level=heading.level if heading is not None else None,
                    heading_text=heading.text if heading is not None else None,
                    passage_ordinals=ordinals,
                    word_count=sum(words.get(position, 0) for position in ordinals),
                )
            )
        return tuple(sections)

    # -- per-passage signals -----------------------------------------------

    @staticmethod
    def _profile(
        passage: Passage, section_ordinal: int, quality: PassageQualityAnalysis
    ) -> PassageReadinessProfile:
        """Read one passage in isolation, the way it would be retrieved.

        The word count is taken from ``AnalyzePassageQuality`` rather than
        recounted, so the two analyses can never report different lengths for
        the same paragraph.
        """
        word_count = next(
            profile.word_count
            for profile in quality.passage_profiles
            if profile.passage_id == passage.passage_id
        )
        sentences = split_sentences(passage.text)
        signals = tuple(
            SentenceSignal(
                ordinal=ordinal,
                text=sentence,
                context_markers=context_markers_in(sentence, passage.language),
            )
            for ordinal, sentence in enumerate(sentences)
        )
        return PassageReadinessProfile(
            passage_id=passage.passage_id,
            ordinal_position=passage.ordinal_position,
            section_ordinal=section_ordinal,
            word_count=word_count,
            text=passage.text,
            sentences=signals,
            definition_opening=(
                definition_opening(sentences[0], passage.language)
                if sentences
                else None
            ),
        )
