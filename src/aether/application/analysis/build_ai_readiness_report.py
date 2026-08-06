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
    title_available: bool
    title_length: int
    canonical_url_available: bool
    publication_date_available: bool
    last_modified_date_available: bool
    language_available: bool
    author_available: bool
    description_available: bool


@dataclass(frozen=True)
class PassageQualitySummary:
    passage_profiles: Tuple[PassageProfile, ...]
    minimum_passage_word_count: Optional[int]
    maximum_passage_word_count: Optional[int]
    median_passage_word_count: Optional[float]


@dataclass(frozen=True)
class AssessmentSummary:
    metadata_completeness: CompletenessClassification


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
                title_available=metadata.title_available,
                title_length=metadata.title_length,
                canonical_url_available=metadata.canonical_url_available,
                publication_date_available=metadata.publication_date_available,
                last_modified_date_available=metadata.last_modified_date_available,
                language_available=metadata.language_available,
                author_available=metadata.author_available,
                description_available=metadata.description_available,
            ),
            passage_quality_summary=PassageQualitySummary(
                passage_profiles=passage_quality.passage_profiles,
                minimum_passage_word_count=passage_quality.minimum_passage_word_count,
                maximum_passage_word_count=passage_quality.maximum_passage_word_count,
                median_passage_word_count=passage_quality.median_passage_word_count,
            ),
            assessment_summary=AssessmentSummary(
                metadata_completeness=assessment.metadata_completeness,
            ),
            content_reuse_summary=self._content_reuse_summary(report),
            editor_recommendations=self._recommendations.execute(report),
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
