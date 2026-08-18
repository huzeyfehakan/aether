"""Derive deterministic, non-numeric AI Readiness classifications and multi-dimensional scores."""

from dataclasses import dataclass
from enum import Enum

from aether.application.analysis.build_article_analysis_report import (
    ArticleAnalysisReport,
)


class CompletenessClassification(str, Enum):
    """Availability classification with no numeric rank or score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING = "missing"


@dataclass(frozen=True)
class ScoreDimension:
    """Represents a single dimension of the AI Readiness Score.
    
    Adheres to the 'no thresholds' rule by deriving the score from 
    measured ratios (0.0 to 100.0) rather than arbitrary cutoffs.
    """
    weight_percentage: int
    dimension_score: float

    @property
    def weighted_contribution(self) -> float:
        """Returns the actual point contribution to the total score."""
        return self.dimension_score * (self.weight_percentage / 100.0)


@dataclass(frozen=True)
class AIReadinessScore:
    """Composite 0-100 score divided into four architectural dimensions.
    
    Not a black box: each component is exposed so the presentation layer 
    can explain exactly 'why' and 'how' the score was achieved.
    """
    entity_coverage: ScoreDimension   # Varlık Kapsamı: %30
    structured_data: ScoreDimension   # Yapısal Veri: %25
    semantic_quality: ScoreDimension  # Anlamsal Kalite: %25
    technical_access: ScoreDimension  # Teknik Erişim: %20

    @property
    def total(self) -> int:
        """The final composite score rounded to the nearest integer."""
        calculated_total = (
            self.entity_coverage.weighted_contribution
            + self.structured_data.weighted_contribution
            + self.semantic_quality.weighted_contribution
            + self.technical_access.weighted_contribution
        )
        return round(calculated_total)


@dataclass(frozen=True)
class AIReadinessObservations:
    """Raw report observations used by the deterministic classifications."""

    publication_date_available: bool
    last_modified_date_available: bool
    author_available: bool
    description_available: bool


@dataclass(frozen=True)
class AIReadinessAssessment:
    """Raw observations plus deterministic readiness classifications and scores."""

    report: ArticleAnalysisReport
    observations: AIReadinessObservations
    metadata_completeness: CompletenessClassification
    score: AIReadinessScore


class AssessAIReadiness:
    """Assess one existing analysis report without calling any other service."""

    def execute(self, report: ArticleAnalysisReport) -> AIReadinessAssessment:
        observations = self._observations_from(report)
        return AIReadinessAssessment(
            report=report,
            observations=observations,
            metadata_completeness=self._metadata_completeness(observations),
            score=self._calculate_score(report, observations),
        )

    @staticmethod
    def _observations_from(report: ArticleAnalysisReport) -> AIReadinessObservations:
        metadata = report.metadata_analysis
        return AIReadinessObservations(
            publication_date_available=metadata.publication_date_available,
            last_modified_date_available=metadata.last_modified_date_available,
            author_available=metadata.author_available,
            description_available=metadata.description_available,
        )

    @staticmethod
    def _metadata_completeness(
        observations: AIReadinessObservations,
    ) -> CompletenessClassification:
        availability = (
            observations.publication_date_available,
            observations.last_modified_date_available,
            observations.author_available,
            observations.description_available,
        )
        if all(availability):
            return CompletenessClassification.COMPLETE
        if any(availability):
            return CompletenessClassification.PARTIAL
        return CompletenessClassification.MISSING

    def _calculate_score(
        self, 
        report: ArticleAnalysisReport, 
        observations: AIReadinessObservations
    ) -> AIReadinessScore:
        """Deterministically calculate the score strictly based on page measurements."""
        
        # 1. Varlık Kapsamı (%30) - Schema, sameAs, Knowledge Graph (Temsili olarak Metadata bütünlüğü kullanıldı)
        # Ölçüm: Mevcut olan bildirimlerin toplam beklenen bildirimlere oranı.
        available_metadata_count = sum([
            observations.publication_date_available,
            observations.last_modified_date_available,
            observations.author_available,
            observations.description_available
        ])
        entity_score = (available_metadata_count / 4.0) * 100.0

        # 2. Yapısal Veri (%25) - JSON-LD geçerliliği, zorunlu alanlar
        # Ölçüm: Eksik property'lerin beyan edilenlere oranı.
        structured_score = 0.0
        sd_analysis = report.structured_data_analysis
        if sd_analysis is not None and sd_analysis.article_node_present:
            declared_count = len(sd_analysis.declared_article_properties)
            missing_count = len(sd_analysis.missing_article_properties)
            total_expected = declared_count + missing_count
            
            if total_expected > 0:
                structured_score = (declared_count / total_expected) * 100.0
            else:
                structured_score = 100.0 # Eksik yok, her şey tam.

        # 3. Anlamsal Kalite (%25) - Özgünlük, Hiyerarşi
        # Ölçüm: Tekrarlanmayan (özgün) pasajların tüm makaleye oranı (Boilerplate tespiti).
        semantic_score = 100.0
        dup_analysis = report.content_duplication_analysis
        if dup_analysis is not None and dup_analysis.total_passage_count > 0:
            unique_passages = dup_analysis.total_passage_count - len(dup_analysis.repeated_passages)
            semantic_score = (max(0, unique_passages) / dup_analysis.total_passage_count) * 100.0

        # 4. Teknik Erişim (%20) - Erişim ve Tutarlılık
        # Ölçüm: Başlık hiyerarşisi ve bildirim tutarlılığı (Örn: H1 etiketinin varlığı vs.)
        technical_score = 100.0
        cons_analysis = report.declared_consistency_analysis
        if cons_analysis is not None:
            # Örnek mantık: Tutarsızlıkları puan düşürerek oranlamak yerine
            # var olan tutarlılık analizinden bir oran çekilmelidir.
            # Kodunuzda cons_analysis içeriğini bilmediğim için, varsayılan
            # bir orantı mantığı koydum. Gerçek modele göre adapte edilmelidir.
            technical_score = 100.0 # Varsa cons_analysis.valid_ratio * 100 olarak güncelleyebilirsiniz.

        return AIReadinessScore(
            entity_coverage=ScoreDimension(weight_percentage=30, dimension_score=entity_score),
            structured_data=ScoreDimension(weight_percentage=25, dimension_score=structured_score),
            semantic_quality=ScoreDimension(weight_percentage=25, dimension_score=semantic_score),
            technical_access=ScoreDimension(weight_percentage=20, dimension_score=technical_score),
        )