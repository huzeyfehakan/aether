"""Project an existing assessment into immutable user-facing report summaries."""

from dataclasses import dataclass
from typing import Optional, Tuple, Union

from enum import Enum

class SignalKind(Enum):
    SCORE = "SCORE"
    RATIO = "RATIO"
    COUNT = "COUNT"
    MEASUREMENT = "MEASUREMENT"

from aether.application.analysis.analyze_content_duplication import RepeatedPassage
from aether.application.analysis.analyze_passage_quality import PassageProfile
from aether.application.analysis.assess_ai_readiness import (
    AIReadinessAssessment,
    CompletenessClassification,
    ScoreDimension,
)
from aether.application.analysis.derive_editor_recommendations import (
    DeriveEditorRecommendations,
    EditorRecommendation,
)


@dataclass(frozen=True)
class ArticleIdentitySummary:
    article_id: str
    article_version_id: str


@dataclass(frozen=True)
class StructuralSummary:
    total_passage_count: int
    total_word_count: int


@dataclass(frozen=True)
class MetadataSummary:
    title_length: int
    publication_date_available: bool
    last_modified_date_available: bool
    author_available: bool
    description_available: bool


@dataclass(frozen=True)
class PassageQualitySummary:
    passage_profiles: Tuple[PassageProfile, ...]
    passage_count: int
    oversized_passage_rate_128: Optional[float]
    oversized_passage_rate_256: Optional[float]
    oversized_passage_rate_512: Optional[float]


@dataclass(frozen=True)
class DirectAnswerCoverageDiagnostic:
    """Experimental question-answer signal that is not included in scoring."""

    ratio: Optional[float]
    included_in_score: bool = False


@dataclass(frozen=True)
class PassageBalanceDiagnostic:
    """Experimental passage-length distribution signal, excluded from scoring."""

    ratio: float
    included_in_score: bool = False


@dataclass(frozen=True)
class ScoreDimensionSummary:
    """A user-facing summary of a single score dimension."""
    weight_percentage: int
    dimension_score: Optional[float]
    weighted_contribution: float


@dataclass(frozen=True)
class ScoreSignalDetail:
    """One deterministic input to a score dimension, if it was measurable."""

    label: str
    value: Optional[Union[float, str]]
    explanation: str
    kind: Optional[SignalKind] = None
    is_context: bool = False


@dataclass(frozen=True)
class ScoreDimensionDetail:
    """Presentation detail for one score dimension and its existing inputs."""

    label: str
    dimension_score: Optional[float]
    signals: Tuple[ScoreSignalDetail, ...]


@dataclass(frozen=True)
class DimensionLimitingFactor:
    """One measured dimension's contribution gap under score renormalization."""

    dimension_key: str
    dimension_score: float
    configured_weight_percentage: int
    effective_weight_percentage: float
    maximum_contribution: float
    actual_contribution: float
    lost_contribution: float


@dataclass(frozen=True)
class SEOScoreSummary:
    """A user-facing summary of the total SEO score and its dimensions."""
    total: Optional[int]
    entity_coverage: ScoreDimensionSummary
    structured_data: ScoreDimensionSummary
    semantic_quality: ScoreDimensionSummary
    technical_access: ScoreDimensionSummary
    entity_coverage_detail: ScoreDimensionDetail
    structured_data_detail: ScoreDimensionDetail
    semantic_quality_detail: ScoreDimensionDetail
    technical_access_detail: ScoreDimensionDetail
    limiting_factors: Tuple[DimensionLimitingFactor, ...] = ()


@dataclass(frozen=True)
class GEOScoreSummary:
    """A user-facing summary of the total GEO score and its dimensions."""
    total: Optional[int]
    semantic_completeness: ScoreDimensionSummary
    entity_authority: ScoreDimensionSummary
    structural_richness: ScoreDimensionSummary
    discoverability: ScoreDimensionSummary
    semantic_completeness_detail: ScoreDimensionDetail
    entity_authority_detail: ScoreDimensionDetail
    structural_richness_detail: ScoreDimensionDetail
    discoverability_detail: ScoreDimensionDetail
    limiting_factors: Tuple[DimensionLimitingFactor, ...] = ()


@dataclass(frozen=True)
class AssessmentSummary:
    """Includes both completeness classification and the deterministic composite scores."""
    metadata_completeness: CompletenessClassification
    seo_score: SEOScoreSummary
    geo_score: GEOScoreSummary


@dataclass(frozen=True)
class StructuredDataSummary:
    """What this article declares about itself to machines."""

    article_node_present: bool
    declared_node_types: Tuple[str, ...]
    declared_article_properties: Tuple[str, ...]
    missing_article_properties: Tuple[str, ...]


@dataclass(frozen=True)
class ContentReuseSummary:
    """Text this article shares with the publisher's other articles.

    ``compared_article_count`` accompanies every finding so an editor can see
    how much evidence it rests on. Zero means no other article was available to
    compare against, not that the article is free of repeated text.
    """

    compared_article_count: int
    total_passage_count: int
    repeated_passages: Tuple[RepeatedPassage, ...]


@dataclass(frozen=True)
class AIReadinessReport:
    """Final MVP output composed exclusively from an existing assessment."""

    article_identity: ArticleIdentitySummary
    structural_summary: StructuralSummary
    metadata_summary: MetadataSummary
    passage_quality_summary: PassageQualitySummary
    passage_balance_diagnostic: PassageBalanceDiagnostic
    direct_answer_coverage_diagnostic: DirectAnswerCoverageDiagnostic
    assessment_summary: AssessmentSummary
    content_reuse_summary: Optional[ContentReuseSummary] = None
    structured_data_summary: Optional[StructuredDataSummary] = None
    editor_recommendations: Tuple[EditorRecommendation, ...] = ()


class BuildAIReadinessReport:
    """Create a presentation-ready immutable projection without new rules."""

    def __init__(
        self,
        recommendations: Optional[DeriveEditorRecommendations] = None,
    ) -> None:
        self._recommendations = recommendations or DeriveEditorRecommendations()

    def execute(self, assessment: AIReadinessAssessment) -> AIReadinessReport:
        report = assessment.report
        structural = report.structural_analysis
        metadata = report.metadata_analysis
        passage_quality = report.passage_quality_analysis
        
        raw_seo = assessment.seo_score
        raw_geo = assessment.geo_score
        
        seo_summary = SEOScoreSummary(
            total=raw_seo.total,
            entity_coverage=ScoreDimensionSummary(
                weight_percentage=raw_seo.entity_coverage.weight_percentage,
                dimension_score=raw_seo.entity_coverage.dimension_score,
                weighted_contribution=raw_seo.entity_coverage.weighted_contribution,
            ),
            structured_data=ScoreDimensionSummary(
                weight_percentage=raw_seo.structured_data.weight_percentage,
                dimension_score=raw_seo.structured_data.dimension_score,
                weighted_contribution=raw_seo.structured_data.weighted_contribution,
            ),
            semantic_quality=ScoreDimensionSummary(
                weight_percentage=raw_seo.semantic_quality.weight_percentage,
                dimension_score=raw_seo.semantic_quality.dimension_score,
                weighted_contribution=raw_seo.semantic_quality.weighted_contribution,
            ),
            technical_access=ScoreDimensionSummary(
                weight_percentage=raw_seo.technical_access.weight_percentage,
                dimension_score=raw_seo.technical_access.dimension_score,
                weighted_contribution=raw_seo.technical_access.weighted_contribution,
            ),
            entity_coverage_detail=self._entity_coverage_detail(
                report, raw_seo.entity_coverage.dimension_score
            ),
            structured_data_detail=self._seo_structured_data_detail(
                report, raw_seo.structured_data.dimension_score
            ),
            semantic_quality_detail=self._semantic_quality_detail(
                report, raw_seo.semantic_quality.dimension_score
            ),
            technical_access_detail=self._technical_access_detail(
                report, raw_seo.technical_access.dimension_score
            ),
            limiting_factors=self._dimension_limiting_factors(
                (
                    ("entity_coverage", raw_seo.entity_coverage),
                    ("structured_data", raw_seo.structured_data),
                    ("semantic_quality", raw_seo.semantic_quality),
                    ("technical_access", raw_seo.technical_access),
                )
            ),
        )

        geo_summary = GEOScoreSummary(
            total=raw_geo.total,
            semantic_completeness=ScoreDimensionSummary(
                weight_percentage=raw_geo.semantic_completeness.weight_percentage,
                dimension_score=raw_geo.semantic_completeness.dimension_score,
                weighted_contribution=raw_geo.semantic_completeness.weighted_contribution,
            ),
            entity_authority=ScoreDimensionSummary(
                weight_percentage=raw_geo.entity_authority.weight_percentage,
                dimension_score=raw_geo.entity_authority.dimension_score,
                weighted_contribution=raw_geo.entity_authority.weighted_contribution,
            ),
            structural_richness=ScoreDimensionSummary(
                weight_percentage=raw_geo.structural_richness.weight_percentage,
                dimension_score=raw_geo.structural_richness.dimension_score,
                weighted_contribution=raw_geo.structural_richness.weighted_contribution,
            ),
            discoverability=ScoreDimensionSummary(
                weight_percentage=raw_geo.discoverability.weight_percentage,
                dimension_score=raw_geo.discoverability.dimension_score,
                weighted_contribution=raw_geo.discoverability.weighted_contribution,
            ),
            semantic_completeness_detail=self._semantic_completeness_detail(
                report, raw_geo.semantic_completeness.dimension_score
            ),
            entity_authority_detail=self._entity_authority_detail(
                report, raw_geo.entity_authority.dimension_score
            ),
            structural_richness_detail=self._structural_richness_detail(
                report, raw_geo.structural_richness.dimension_score
            ),
            discoverability_detail=self._discoverability_detail(
                report, raw_geo.discoverability.dimension_score
            ),
            limiting_factors=self._dimension_limiting_factors(
                (
                    ("semantic_completeness", raw_geo.semantic_completeness),
                    ("entity_authority", raw_geo.entity_authority),
                    ("structural_richness", raw_geo.structural_richness),
                    ("discoverability", raw_geo.discoverability),
                )
            ),
        )

        return AIReadinessReport(
            article_identity=ArticleIdentitySummary(
                article_id=structural.article_id,
                article_version_id=structural.article_version_id,
            ),
            structural_summary=StructuralSummary(
                total_passage_count=structural.total_passage_count,
                total_word_count=structural.total_word_count,
            ),
            metadata_summary=MetadataSummary(
                title_length=metadata.title_length,
                publication_date_available=metadata.publication_date_available,
                last_modified_date_available=metadata.last_modified_date_available,
                author_available=metadata.author_available,
                description_available=metadata.description_available,
            ),
            passage_quality_summary=PassageQualitySummary(
                passage_profiles=passage_quality.passage_profiles,
                passage_count=len(passage_quality.passage_profiles),
                oversized_passage_rate_128=(
                    passage_quality.oversized_passage_rate_128
                ),
                oversized_passage_rate_256=(
                    passage_quality.oversized_passage_rate_256
                ),
                oversized_passage_rate_512=(
                    passage_quality.oversized_passage_rate_512
                ),
            ),
            passage_balance_diagnostic=PassageBalanceDiagnostic(
                ratio=passage_quality.passage_balance_ratio,
            ),
            direct_answer_coverage_diagnostic=DirectAnswerCoverageDiagnostic(
                ratio=structural.direct_answer_coverage_ratio,
            ),
            assessment_summary=AssessmentSummary(
                metadata_completeness=assessment.metadata_completeness,
                seo_score=seo_summary,
                geo_score=geo_summary,
            ),
            content_reuse_summary=self._content_reuse_summary(report),
            structured_data_summary=self._structured_data_summary(report),
            editor_recommendations=self._recommendations.execute(report),
        )

    @staticmethod
    def _dimension_limiting_factors(
        dimensions: Tuple[Tuple[str, ScoreDimension], ...]
    ) -> Tuple[DimensionLimitingFactor, ...]:
        """Rank measured contribution gaps using the score's own dimensions."""

        available = tuple(
            (position, key, dimension)
            for position, (key, dimension) in enumerate(dimensions)
            if dimension.dimension_score is not None
        )
        available_weight = sum(
            dimension.weight_percentage for _, _, dimension in available
        )
        if available_weight == 0:
            return ()

        ranked = []
        for position, key, dimension in available:
            effective_weight = dimension.weight_percentage / available_weight
            maximum = effective_weight * 100.0
            actual = effective_weight * dimension.dimension_score
            lost = maximum - actual
            if lost > 0.0:
                ranked.append(
                    (
                        position,
                        DimensionLimitingFactor(
                            dimension_key=key,
                            dimension_score=dimension.dimension_score,
                            configured_weight_percentage=dimension.weight_percentage,
                            effective_weight_percentage=effective_weight * 100.0,
                            maximum_contribution=maximum,
                            actual_contribution=actual,
                            lost_contribution=lost,
                        ),
                    )
                )
        ranked.sort(key=lambda item: (-item[1].lost_contribution, item[0]))
        return tuple(factor for _, factor in ranked)

    @staticmethod
    def _entity_coverage_detail(
        report, dimension_score: Optional[float]
    ) -> ScoreDimensionDetail:
        metadata = report.metadata_analysis
        values = (
            None,
            None,
            None,
            None,
        ) if dimension_score is None else (
            "Available" if metadata.publication_date_available else "Missing",
            "Available" if metadata.last_modified_date_available else "Missing",
            "Available" if metadata.author_available else "Missing",
            "Available" if metadata.description_available else "Missing",
        )
        return ScoreDimensionDetail(
            label="Entity Coverage",
            dimension_score=dimension_score,
            signals=(
                ScoreSignalDetail(
                    "Publication date",
                    values[0],
                    "Whether a publication date was available to the SEO formula",
                ),
                ScoreSignalDetail(
                    "Last modified date",
                    values[1],
                    "Whether a last-modified date was available to the SEO formula",
                ),
                ScoreSignalDetail(
                    "Author",
                    values[2],
                    "Whether an author was available to the SEO formula",
                ),
                ScoreSignalDetail(
                    "Description",
                    values[3],
                    "Whether a description was available to the SEO formula",
                ),
            ),
        )

    @staticmethod
    def _seo_structured_data_detail(
        report, dimension_score: Optional[float]
    ) -> ScoreDimensionDetail:
        analysis = report.structured_data_analysis
        if analysis is None or dimension_score is None:
            values = (None, None, None, None)
        else:
            values = (
                "Present" if analysis.article_node_present else "Missing",
                ", ".join(analysis.declared_article_properties) or "None",
                ", ".join(analysis.missing_article_properties) or "None",
                dimension_score,
            )
        return ScoreDimensionDetail(
            label="Structured Data",
            dimension_score=dimension_score,
            signals=tuple(
                ScoreSignalDetail(label, value, explanation)
                for label, value, explanation in zip(
                    (
                        "Article structured data",
                        "Declared expected properties",
                        "Missing expected properties",
                        "Property coverage",
                    ),
                    values,
                    (
                        "Whether an Article or NewsArticle node was found",
                        "Expected Article properties declared by that node",
                        "Expected Article properties absent from that node",
                        "Declared expected properties divided by all expected properties",
                    ),
                )
            ),
        )

    @staticmethod
    def _semantic_quality_detail(
        report, dimension_score: Optional[float]
    ) -> ScoreDimensionDetail:
        analysis = report.content_duplication_analysis
        if analysis is None or dimension_score is None:
            values = (None, None, None, None)
        else:
            total = analysis.total_passage_count
            repeated = len(analysis.repeated_passages)
            unique = max(0, total - repeated)
            values = (float(total), float(unique), float(repeated), dimension_score)
        return ScoreDimensionDetail(
            label="Semantic Quality",
            dimension_score=dimension_score,
            signals=tuple(
                ScoreSignalDetail(label, value, explanation)
                for label, value, explanation in zip(
                    (
                        "Total passages",
                        "Unique passages",
                        "Repeated passages",
                        "Unique passage ratio",
                    ),
                    values,
                    (
                        "Passages included in duplication analysis",
                        "Total passages minus repeated passages, floored at zero",
                        "Passages reported as repeated",
                        "Unique passages divided by total passages",
                    ),
                )
            ),
        )

    @staticmethod
    def _technical_access_detail(
        report, dimension_score: Optional[float]
    ) -> ScoreDimensionDetail:
        analysis = report.declared_consistency_analysis
        if analysis is None:
            values = (None, None)
        else:
            values = (
                "Yes" if not analysis.titles_agree else "No",
                "Yes" if not analysis.descriptions_agree else "No",
            )
        return ScoreDimensionDetail(
            label="Technical Access",
            dimension_score=dimension_score,
            signals=(
                ScoreSignalDetail(
                    "Title sources disagree",
                    values[0],
                    "Disagreement flag read by the existing SEO formula",
                ),
                ScoreSignalDetail(
                    "Description sources disagree",
                    values[1],
                    "Disagreement flag read by the existing SEO formula",
                ),
            ),
        )

    @staticmethod
    def _semantic_completeness_detail(
        report, dimension_score: Optional[float]
    ) -> ScoreDimensionDetail:
        profiles = report.passage_quality_analysis.passage_profiles
        structural = report.structural_analysis
        fluency = report.fluency_analysis

        statistics_coverage = None
        heading_passage_overlap = None
        sentence_balance = None
        structural_variety = None
        if profiles:
            statistics_count = sum(
                1 for profile in profiles if profile.contains_statistics
            )
            statistics_coverage = statistics_count / len(profiles) * 100.0
            if structural.heading_passage_overlap_ratio is not None:
                heading_passage_overlap = (
                    structural.heading_passage_overlap_ratio * 100.0
                )
            if fluency is not None:
                sentence_balance = fluency.sentence_balance_ratio * 100.0
                structural_variety = (
                    min(1.0, fluency.structural_variety_ratio) * 100.0
                )

        return ScoreDimensionDetail(
            label="Semantic Completeness",
            dimension_score=dimension_score,
            signals=(
                ScoreSignalDetail(
                    label="Statistics coverage",
                    value=statistics_coverage,
                    explanation="Share of passages containing statistics",
                ),
                ScoreSignalDetail(
                    label="Heading-passage overlap",
                    value=heading_passage_overlap,
                    explanation="Measured overlap between headings and passages",
                ),
                ScoreSignalDetail(
                    label="Sentence balance",
                    value=sentence_balance,
                    explanation="Fluency sentence-balance ratio",
                ),
                ScoreSignalDetail(
                    label="Structural variety",
                    value=structural_variety,
                    explanation="Fluency structural-variety ratio, capped at 100",
                ),
            ),
        )

    @staticmethod
    def _entity_authority_detail(
        report, dimension_score: Optional[float]
    ) -> ScoreDimensionDetail:
        structured_data = report.structured_data_analysis
        links = report.internal_link_analysis
        structural = report.structural_analysis
        profiles = report.passage_quality_analysis.passage_profiles
        claim_evidence = report.claim_evidence_analysis

        author_declaration = None
        if structured_data is not None:
            author_declaration = (
                100.0
                if "author" in structured_data.declared_article_properties
                else 0.0
            )

        outbound_body_sources = None
        if links is not None:
            outbound_body_sources = 100.0 if links.outbound_body_domains else 0.0

        supported_entities = None
        if structural.unsupported_entity_ratio is not None:
            supported_entities = (
                1.0 - structural.unsupported_entity_ratio
            ) * 100.0

        citation_coverage = None
        if profiles:
            citation_count = sum(1 for profile in profiles if profile.contains_citation)
            citation_coverage = citation_count / len(profiles) * 100.0

        claim_evidence_coverage = None
        if claim_evidence is not None and claim_evidence.detectable_claim_count > 0:
            claim_evidence_coverage = claim_evidence.claim_evidence_coverage * 100.0

        return ScoreDimensionDetail(
            label="Entity Authority",
            dimension_score=dimension_score,
            signals=(
                ScoreSignalDetail(
                    label="Author declaration",
                    value=author_declaration,
                    explanation="Schema.org Article author declaration",
                ),
                ScoreSignalDetail(
                    label="Outbound body sources",
                    value=outbound_body_sources,
                    explanation="Whether the article body links to an external domain",
                ),
                ScoreSignalDetail(
                    label="Trust index",
                    value=(
                        None
                        if links is None or links.trust_index is None
                        else links.trust_index * 100.0
                    ),
                    explanation="Trust-weighted outbound body sources",
                ),
                ScoreSignalDetail(
                    label="Third-party source ratio",
                    value=(
                        None
                        if links is None or links.third_party_ratio is None
                        else links.third_party_ratio * 100.0
                    ),
                    explanation="Share of outbound body sources that are third-party",
                ),
                ScoreSignalDetail(
                    label="Supported entities",
                    value=supported_entities,
                    explanation="One minus the unsupported entity ratio",
                ),
                ScoreSignalDetail(
                    label="Citation coverage",
                    value=citation_coverage,
                    explanation="Share of passages containing a citation",
                ),
                ScoreSignalDetail(
                    label="Claim evidence coverage",
                    value=claim_evidence_coverage,
                    explanation="Share of detectable claims with evidence",
                ),
            ),
        )

    @staticmethod
    def _structural_richness_detail(
        report, dimension_score: Optional[float]
    ) -> ScoreDimensionDetail:
        structural = report.structural_analysis
        table_share = None
        list_share = None
        blockquote_share = None
        structured_content_ratio = None
        answered_question_ratio = None

        if structural.total_word_count > 0:
            structured_words = (
                structural.table_word_count
                + structural.list_word_count
                + structural.blockquote_word_count
            )
            richness_denominator = structural.total_word_count + structured_words
            table_share = structural.table_word_count / richness_denominator * 100.0
            list_share = structural.list_word_count / richness_denominator * 100.0
            blockquote_share = (
                structural.blockquote_word_count / richness_denominator * 100.0
            )
            structured_content_ratio = (
                structured_words / richness_denominator * 100.0
            )

            total_questions = (
                structural.answered_question_heading_count
                + structural.unanswered_question_heading_count
            )
            if total_questions > 0:
                answered_question_ratio = (
                    structural.answered_question_heading_count
                    / total_questions
                    * 100.0
                )

        return ScoreDimensionDetail(
            label="Structural Richness",
            dimension_score=dimension_score,
            signals=(
                ScoreSignalDetail(
                    label="Table word share",
                    value=table_share,
                    explanation="Table words as a share of the richness denominator",
                ),
                ScoreSignalDetail(
                    label="List word share",
                    value=list_share,
                    explanation="List words as a share of the richness denominator",
                ),
                ScoreSignalDetail(
                    label="Blockquote word share",
                    value=blockquote_share,
                    explanation="Blockquote words as a share of the richness denominator",
                ),
                ScoreSignalDetail(
                    label="Structured content ratio",
                    value=structured_content_ratio,
                    explanation="Combined table, list, and blockquote word ratio",
                ),
                ScoreSignalDetail(
                    label="Answered question ratio",
                    value=answered_question_ratio,
                    explanation="Share of question headings that have an answer",
                ),
            ),
        )

    @staticmethod
    def _discoverability_detail(
        report, dimension_score: Optional[float]
    ) -> ScoreDimensionDetail:
        links = report.internal_link_analysis
        structural = report.structural_analysis
        
        body_link_saturation = None
        unique_target_ratio = None
        
        if links is not None:
            if structural and structural.total_passage_count > 0:
                density = links.body_link_count / structural.total_passage_count
                body_link_saturation = (density / (1 + density)) * 100.0
            else:
                body_link_saturation = 0.0
                
            if links.body_link_count > 0:
                unique_target_ratio = (
                    links.unique_body_target_count / links.body_link_count
                ) * 100.0
            else:
                unique_target_ratio = 0.0

        return ScoreDimensionDetail(
            label="Discoverability",
            dimension_score=dimension_score,
            signals=(
                ScoreSignalDetail(
                    label="Body link saturation",
                    value=body_link_saturation,
                    explanation="Score contribution based on body link density",
                    kind=SignalKind.RATIO,
                ),
                ScoreSignalDetail(
                    label="Unique target ratio",
                    value=unique_target_ratio,
                    explanation="Ratio of unique link targets to total body links",
                    kind=SignalKind.RATIO,
                    is_context=True,
                ),
            ),
        )

    @staticmethod
    def _structured_data_summary(report) -> Optional[StructuredDataSummary]:
        analysis = report.structured_data_analysis
        if analysis is None:
            return None
        return StructuredDataSummary(
            article_node_present=analysis.article_node_present,
            declared_node_types=analysis.declared_node_types,
            declared_article_properties=analysis.declared_article_properties,
            missing_article_properties=analysis.missing_article_properties,
        )

    @staticmethod
    def _content_reuse_summary(report) -> Optional[ContentReuseSummary]:
        duplication = report.content_duplication_analysis
        if duplication is None:
            return None
        return ContentReuseSummary(
            compared_article_count=duplication.compared_article_count,
            total_passage_count=duplication.total_passage_count,
            repeated_passages=duplication.repeated_passages,
        )
