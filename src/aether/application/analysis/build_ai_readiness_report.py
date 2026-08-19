"""Project an existing assessment into immutable user-facing report summaries."""

from dataclasses import dataclass
from typing import Optional, Tuple

from aether.application.analysis.analyze_content_duplication import RepeatedPassage
from aether.application.analysis.analyze_passage_quality import PassageProfile
from aether.application.analysis.assess_ai_readiness import (
    AIReadinessAssessment,
    CompletenessClassification,
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


@dataclass(frozen=True)
class ScoreDimensionSummary:
    """A user-facing summary of a single score dimension."""
    weight_percentage: int
    dimension_score: float
    weighted_contribution: float


@dataclass(frozen=True)
class SEOScoreSummary:
    """A user-facing summary of the total SEO score and its dimensions."""
    total: int
    entity_coverage: ScoreDimensionSummary
    structured_data: ScoreDimensionSummary
    semantic_quality: ScoreDimensionSummary
    technical_access: ScoreDimensionSummary


@dataclass(frozen=True)
class GEOScoreSummary:
    """A user-facing summary of the total GEO score and its dimensions."""
    total: int
    semantic_completeness: ScoreDimensionSummary
    entity_authority: ScoreDimensionSummary
    structural_richness: ScoreDimensionSummary
    discoverability: ScoreDimensionSummary


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