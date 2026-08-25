"""Turn existing analysis facts into recommendations an editor can act on.

This is the one place where a finding becomes advice. Every recommendation
answers a single question: what can the editor improve before publishing this
article?

Recommendations carry a category naming *who can act on them*. An editor can
change what this article says today. Changing how the page is built -- its
markup, its declarations, its template -- needs the CMS or engineering, and
usually fixes every article at once rather than this one. Mixing the two buries
the few things an editor can fix among many things they cannot, which is the
fastest way to make a report ignored.

Only a category, a code and the supporting facts are produced here. The wording
belongs to presentation, which serves editors in their own language; putting
sentences in this layer would fix the report to one language and place
copywriting inside a use case.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

from aether.application.analysis.build_article_analysis_report import (
    ArticleAnalysisReport,
)


class RecommendationCategory(str, Enum):
    """Who can act on a recommendation."""

    EDITOR = "editor"
    TECHNICAL = "technical"


class RecommendationPriority(int, Enum):
    """Triage priority for editor recommendations."""
    P1_TECHNICAL = 1
    P2_PRIMARY_EVIDENCE = 2
    P3_STRUCTURAL_FORMAT = 3

class RecommendationCode(str, Enum):
    """The recommendations this MVP can justify from deterministic facts."""

    REPEATED_TEXT_IN_ARTICLE_BODY = "repeated_text_in_article_body"
    NO_ARTICLE_STRUCTURED_DATA = "no_article_structured_data"
    INCOMPLETE_ARTICLE_STRUCTURED_DATA = "incomplete_article_structured_data"
    TITLE_SOURCES_DISAGREE = "title_sources_disagree"
    DESCRIPTION_SOURCES_DISAGREE = "description_sources_disagree"
    MISSING_PUBLICATION_DATE = "missing_publication_date"
    MISSING_AUTHOR = "missing_author"
    MISSING_SUMMARY = "missing_summary"
    MISSING_LAST_MODIFIED_DATE = "missing_last_modified_date"
    BODY_MOSTLY_REPEATED_TEXT = "body_mostly_repeated_text"
    NO_TOP_LEVEL_HEADING = "no_top_level_heading"
    MULTIPLE_TOP_LEVEL_HEADINGS = "multiple_top_level_headings"
    WEAK_ARTICLE_OPENING = "weak_article_opening"
    WEAK_TOPIC_INTRODUCTION = "weak_topic_introduction"
    # New GEO metric codes
    NO_OUTBOUND_LINKS = "no_outbound_links"
    NO_CITATIONS = "no_citations"
    NO_STATISTICS = "no_statistics"
    ORPHAN_PAGE = "orphan_page"
    NO_INTERNAL_BODY_LINKS = "no_internal_body_links"
    CONTENT_BLOAT = "content_bloat"
    SKIPPED_HEADING_LEVEL = "skipped_heading_level"
    CONFLICTING_PUBLISHED_DATES = "conflicting_published_dates"
    UNSUPPORTED_ENTITIES = "unsupported_entities"
    LOW_TRUST_INDEX = "low_trust_index"
    MISSING_SAME_AS_SCHEMA = "missing_same_as_schema"


#: Structured data is declared by the page template, so correcting it is a CMS
#: or engineering change that fixes every article at once.
#:
#: Repeated text is filed under the editor because the editor owns the article
#: body and is the person who sees the paragraph. Whether the remedy is theirs
#: or the CMS team's depends on how the text got there, which the markup does
#: not reveal, so the advice names both paths rather than guessing.
_CATEGORIES = {
    RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY: RecommendationCategory.EDITOR,
    RecommendationCode.BODY_MOSTLY_REPEATED_TEXT: RecommendationCategory.EDITOR,
    RecommendationCode.TITLE_SOURCES_DISAGREE: RecommendationCategory.EDITOR,
    RecommendationCode.DESCRIPTION_SOURCES_DISAGREE: RecommendationCategory.EDITOR,
    # Fields an editor fills in when writing the article.
    RecommendationCode.MISSING_PUBLICATION_DATE: RecommendationCategory.EDITOR,
    RecommendationCode.MISSING_AUTHOR: RecommendationCategory.EDITOR,
    RecommendationCode.MISSING_SUMMARY: RecommendationCategory.EDITOR,
    # Editors write the headings inside an article.
    RecommendationCode.NO_TOP_LEVEL_HEADING: RecommendationCategory.EDITOR,
    RecommendationCode.MULTIPLE_TOP_LEVEL_HEADINGS: RecommendationCategory.EDITOR,
    RecommendationCode.WEAK_ARTICLE_OPENING: RecommendationCategory.EDITOR,
    RecommendationCode.WEAK_TOPIC_INTRODUCTION: RecommendationCategory.EDITOR,
    # New GEO codes
    RecommendationCode.NO_OUTBOUND_LINKS: RecommendationCategory.EDITOR,
    RecommendationCode.NO_CITATIONS: RecommendationCategory.EDITOR,
    RecommendationCode.NO_STATISTICS: RecommendationCategory.EDITOR,
    RecommendationCode.ORPHAN_PAGE: RecommendationCategory.EDITOR,
    RecommendationCode.NO_INTERNAL_BODY_LINKS: RecommendationCategory.EDITOR,
    RecommendationCode.CONTENT_BLOAT: RecommendationCategory.EDITOR,
    RecommendationCode.SKIPPED_HEADING_LEVEL: RecommendationCategory.EDITOR,
    RecommendationCode.UNSUPPORTED_ENTITIES: RecommendationCategory.EDITOR,
    RecommendationCode.LOW_TRUST_INDEX: RecommendationCategory.EDITOR,
    # The CMS stamps this on save; an editor has no field for it.
    RecommendationCode.MISSING_LAST_MODIFIED_DATE: RecommendationCategory.TECHNICAL,
    RecommendationCode.NO_ARTICLE_STRUCTURED_DATA: RecommendationCategory.TECHNICAL,
    RecommendationCode.INCOMPLETE_ARTICLE_STRUCTURED_DATA: (
        RecommendationCategory.TECHNICAL
    ),
    RecommendationCode.CONFLICTING_PUBLISHED_DATES: RecommendationCategory.TECHNICAL,
    RecommendationCode.MISSING_SAME_AS_SCHEMA: RecommendationCategory.TECHNICAL,
}

_PRIORITIES = {
    # P1: Technical and crucial completeness
    RecommendationCode.NO_ARTICLE_STRUCTURED_DATA: RecommendationPriority.P1_TECHNICAL,
    RecommendationCode.INCOMPLETE_ARTICLE_STRUCTURED_DATA: RecommendationPriority.P1_TECHNICAL,
    RecommendationCode.MISSING_LAST_MODIFIED_DATE: RecommendationPriority.P1_TECHNICAL,
    RecommendationCode.MISSING_PUBLICATION_DATE: RecommendationPriority.P1_TECHNICAL,
    RecommendationCode.MISSING_AUTHOR: RecommendationPriority.P1_TECHNICAL,
    RecommendationCode.MISSING_SUMMARY: RecommendationPriority.P1_TECHNICAL,
    RecommendationCode.TITLE_SOURCES_DISAGREE: RecommendationPriority.P1_TECHNICAL,
    RecommendationCode.DESCRIPTION_SOURCES_DISAGREE: RecommendationPriority.P1_TECHNICAL,
    RecommendationCode.CONFLICTING_PUBLISHED_DATES: RecommendationPriority.P1_TECHNICAL,
    RecommendationCode.MISSING_SAME_AS_SCHEMA: RecommendationPriority.P1_TECHNICAL,

    # P2: Primary Evidence (GEO Authority)
    RecommendationCode.NO_OUTBOUND_LINKS: RecommendationPriority.P2_PRIMARY_EVIDENCE,
    RecommendationCode.NO_CITATIONS: RecommendationPriority.P2_PRIMARY_EVIDENCE,
    RecommendationCode.NO_STATISTICS: RecommendationPriority.P2_PRIMARY_EVIDENCE,
    RecommendationCode.ORPHAN_PAGE: RecommendationPriority.P2_PRIMARY_EVIDENCE,
    RecommendationCode.NO_INTERNAL_BODY_LINKS: RecommendationPriority.P2_PRIMARY_EVIDENCE,
    RecommendationCode.UNSUPPORTED_ENTITIES: RecommendationPriority.P2_PRIMARY_EVIDENCE,
    RecommendationCode.LOW_TRUST_INDEX: RecommendationPriority.P2_PRIMARY_EVIDENCE,

    # P3: Structural Format
    RecommendationCode.NO_TOP_LEVEL_HEADING: RecommendationPriority.P3_STRUCTURAL_FORMAT,
    RecommendationCode.MULTIPLE_TOP_LEVEL_HEADINGS: RecommendationPriority.P3_STRUCTURAL_FORMAT,
    RecommendationCode.WEAK_ARTICLE_OPENING: RecommendationPriority.P3_STRUCTURAL_FORMAT,
    RecommendationCode.WEAK_TOPIC_INTRODUCTION: RecommendationPriority.P3_STRUCTURAL_FORMAT,
    RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY: RecommendationPriority.P3_STRUCTURAL_FORMAT,
    RecommendationCode.BODY_MOSTLY_REPEATED_TEXT: RecommendationPriority.P3_STRUCTURAL_FORMAT,
    RecommendationCode.CONTENT_BLOAT: RecommendationPriority.P3_STRUCTURAL_FORMAT,
    RecommendationCode.SKIPPED_HEADING_LEVEL: RecommendationPriority.P3_STRUCTURAL_FORMAT,
}

@dataclass(frozen=True)
class EditorRecommendation:
    """One improvement an editor can make, with the evidence behind it."""

    code: RecommendationCode
    excerpt: str = ""
    passage_ids: Tuple[str, ...] = ()
    other_article_count: int = 0
    missing_properties: Tuple[str, ...] = ()
    heading_count: int = 0
    repeated_word_count: int = 0
    total_word_count: int = 0
    declared_values: Tuple[Tuple[str, str], ...] = ()

    @property
    def category(self) -> RecommendationCategory:
        return _CATEGORIES[self.code]

    @property
    def priority(self) -> RecommendationPriority:
        return _PRIORITIES[self.code]


#: Schema.org Article properties that restate a field the metadata analysis
#: already checks. When the underlying data is absent, the two findings are the
#: same gap in different words, and the metadata one is the stronger of the
#: pair: a publisher cannot declare a date they do not have. When the data is
#: present but undeclared, only the structured-data finding applies, and it
#: says something the metadata finding cannot.
_PROPERTY_BEHIND_METADATA = {
    "datePublished": "publication_date_available",
    "dateModified": "last_modified_date_available",
    "author": "author_available",
    "description": "description_available",
}


def _absent_metadata_properties(report: ArticleAnalysisReport) -> frozenset:
    """Schema.org properties whose underlying data the article also lacks."""
    metadata = report.metadata_analysis
    return frozenset(
        name
        for name, attribute in _PROPERTY_BEHIND_METADATA.items()
        if not getattr(metadata, attribute)
    )


class DeriveEditorRecommendations:
    """Derive editor-facing advice from an existing analysis report."""

    def execute(self, report: ArticleAnalysisReport) -> Tuple[EditorRecommendation, ...]:
        if report.is_draft:
            # A draft has no published page, so only the checks its own text
            # can answer are run. Nothing is inferred about what the CMS will
            # publish around it.
            draft_recommendations = list(
                self._heading_structure(report)
                + self._weak_article_opening(report)
                + self._repeated_text(report)
                + self._geo_evidence_and_discoverability(report)
            )
            draft_recommendations.sort(key=lambda r: r.priority)
            return tuple(draft_recommendations)
        recommendations = list(
            self._missing_metadata(report)
            + self._heading_structure(report)
            + self._weak_article_opening(report)
            + self._declared_consistency(report)
            + self._repeated_text(report)
            + self._structured_data(report)
            + self._topic_introduction(report)
            + self._geo_evidence_and_discoverability(report)
        )
        # Sort by priority
        recommendations.sort(key=lambda r: r.priority)
        return tuple(recommendations)

    @staticmethod
    def _geo_evidence_and_discoverability(
        report: ArticleAnalysisReport,
    ) -> Tuple[EditorRecommendation, ...]:
        recommendations = []

        # GEO Evidence
        if report.passage_quality_analysis and report.passage_quality_analysis.passage_profiles:
            profiles = report.passage_quality_analysis.passage_profiles
            stat_count = sum(1 for p in profiles if p.contains_statistics)

            if stat_count == 0:
                recommendations.append(EditorRecommendation(code=RecommendationCode.NO_STATISTICS))

        # Discoverability & Link Authority
        links = report.internal_link_analysis
        if links is not None:
            if not getattr(links, 'outbound_body_domains', ()):
                recommendations.append(EditorRecommendation(code=RecommendationCode.NO_OUTBOUND_LINKS))
            if links.body_link_count == 0:
                recommendations.append(EditorRecommendation(code=RecommendationCode.NO_INTERNAL_BODY_LINKS))

        # Structured Data Identity
        sd_analysis = report.structured_data_analysis
        if sd_analysis is not None:
            has_same_as = "sameas" in [p.lower() for p in sd_analysis.all_declared_properties]
            if not has_same_as:
                recommendations.append(EditorRecommendation(code=RecommendationCode.MISSING_SAME_AS_SCHEMA))

        # Content Bloat & Unsupported Entities
        if report.structural_analysis is not None:
            if report.structural_analysis.heading_passage_overlap_ratio == 0.0 and report.structural_analysis.definitive_stance_ratio == 0.0:
                if report.structural_analysis.total_passage_count > 3: # Only for longer articles
                    recommendations.append(EditorRecommendation(code=RecommendationCode.CONTENT_BLOAT))
            unsupported = report.structural_analysis.unsupported_entity_ratio
            if unsupported is not None and unsupported > 0.0:
                recommendations.append(EditorRecommendation(code=RecommendationCode.UNSUPPORTED_ENTITIES))

        return tuple(recommendations)

    @staticmethod
    def _structured_data(
        report: ArticleAnalysisReport,
    ) -> Tuple[EditorRecommendation, ...]:
        analysis = report.structured_data_analysis
        if analysis is None:
            return ()
        if not analysis.article_node_present:
            return (
                EditorRecommendation(
                    code=RecommendationCode.NO_ARTICLE_STRUCTURED_DATA,
                ),
            )
        undeclared = tuple(
            name
            for name in analysis.missing_article_properties
            if name not in _absent_metadata_properties(report)
        )
        if undeclared:
            return (
                EditorRecommendation(
                    code=RecommendationCode.INCOMPLETE_ARTICLE_STRUCTURED_DATA,
                    missing_properties=undeclared,
                ),
            )
        return ()

    @staticmethod
    def _missing_metadata(
        report: ArticleAnalysisReport,
    ) -> Tuple[EditorRecommendation, ...]:
        """Absent metadata an editor or the CMS can supply.

        Only fields that can actually be absent are checked. The domain
        refuses to build an article without a title, a canonical URL or a
        language, so those can never be missing here.
        """
        metadata = report.metadata_analysis
        missing = (
            (metadata.publication_date_available, RecommendationCode.MISSING_PUBLICATION_DATE),
            (metadata.author_available, RecommendationCode.MISSING_AUTHOR),
            (metadata.description_available, RecommendationCode.MISSING_SUMMARY),
            (
                metadata.last_modified_date_available,
                RecommendationCode.MISSING_LAST_MODIFIED_DATE,
            ),
        )
        recs = [
            EditorRecommendation(code=code) for available, code in missing if not available
        ]
        if getattr(metadata, 'cross_date_conflict', False):
            recs.append(EditorRecommendation(code=RecommendationCode.CONFLICTING_PUBLISHED_DATES))

        return tuple(recs)

    @staticmethod
    def _heading_structure(
        report: ArticleAnalysisReport,
    ) -> Tuple[EditorRecommendation, ...]:
        analysis = report.heading_structure_analysis
        if analysis is None:
            return ()

        recommendations = []
        if analysis.top_level_count == 0:
            recommendations.append(
                EditorRecommendation(
                    code=RecommendationCode.NO_TOP_LEVEL_HEADING,
                )
            )
        elif analysis.top_level_count > 1:
            recommendations.append(
                EditorRecommendation(
                    code=RecommendationCode.MULTIPLE_TOP_LEVEL_HEADINGS,
                    heading_count=analysis.top_level_count,
                )
            )

        if getattr(analysis, 'skipped_heading_levels', False):
            recommendations.append(
                EditorRecommendation(
                    code=RecommendationCode.SKIPPED_HEADING_LEVEL,
                )
            )

        return tuple(recommendations)

    @staticmethod
    def _weak_article_opening(
        report: ArticleAnalysisReport,
    ) -> Tuple[EditorRecommendation, ...]:
        """Report a short first paragraph only when the article is substantial."""
        profiles = report.passage_quality_analysis.passage_profiles
        if not profiles:
            return ()
        total_word_count = sum(profile.word_count for profile in profiles)
        if total_word_count < 150 or profiles[0].word_count > 20:
            return ()
        return (EditorRecommendation(code=RecommendationCode.WEAK_ARTICLE_OPENING),)
    @staticmethod
    def _topic_introduction(
        report: ArticleAnalysisReport,
    ) -> Tuple[EditorRecommendation, ...]:
        analysis = report.topic_introduction_analysis

        if analysis is None:
            return ()

        if len(analysis.meaningful_title_terms) < 3:
            return ()

        if analysis.coverage >= 0.40:
            return ()

        return (
            EditorRecommendation(
                code=RecommendationCode.WEAK_TOPIC_INTRODUCTION,
            ),
        )

    @staticmethod
    def _declared_consistency(
        report: ArticleAnalysisReport,
    ) -> Tuple[EditorRecommendation, ...]:
        analysis = report.declared_consistency_analysis
        if analysis is None:
            return ()
        found = []
        if not analysis.titles_agree:
            found.append(
                EditorRecommendation(
                    code=RecommendationCode.TITLE_SOURCES_DISAGREE,
                    declared_values=tuple(
                        (title.source.value, title.value)
                        for title in analysis.declared_titles
                    ),
                )
            )
        if not analysis.descriptions_agree:
            found.append(
                EditorRecommendation(
                    code=RecommendationCode.DESCRIPTION_SOURCES_DISAGREE,
                    declared_values=tuple(
                        (description.source.value, description.value)
                        for description in analysis.declared_descriptions
                    ),
                )
            )
        return tuple(found)

    @staticmethod
    def _repeated_text(
        report: ArticleAnalysisReport,
    ) -> Tuple[EditorRecommendation, ...]:
        duplication = report.content_duplication_analysis
        if duplication is None:
            return ()
        whole_body = (
            (
                EditorRecommendation(
                    code=RecommendationCode.BODY_MOSTLY_REPEATED_TEXT,
                    repeated_word_count=duplication.repeated_word_count,
                    total_word_count=duplication.total_word_count,
                ),
            )
            if duplication.is_mostly_repeated
            else ()
        )
        return whole_body + tuple(
            EditorRecommendation(
                code=RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY,
                excerpt=repeated.text,
                passage_ids=(repeated.passage_id,),
                other_article_count=repeated.other_article_count,
            )
            for repeated in duplication.repeated_passages
        )
