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

    Scores are derived from measured ratios rather than arbitrary thresholds.
    """

    weight_percentage: int
    dimension_score: float

    @property
    def weighted_contribution(self) -> float:
        """Return the actual point contribution to the total score."""
        return self.dimension_score * (self.weight_percentage / 100.0)


@dataclass(frozen=True)
class SEOScore:
    """Composite 0-100 score for traditional SEO dimensions."""

    entity_coverage: ScoreDimension
    structured_data: ScoreDimension
    semantic_quality: ScoreDimension
    technical_access: ScoreDimension

    @property
    def total(self) -> int:
        calculated_total = (
            self.entity_coverage.weighted_contribution
            + self.structured_data.weighted_contribution
            + self.semantic_quality.weighted_contribution
            + self.technical_access.weighted_contribution
        )

        return round(calculated_total)


@dataclass(frozen=True)
class GEOScore:
    """Composite 0-100 score for Generative Engine Optimization principles."""

    semantic_completeness: ScoreDimension
    entity_authority: ScoreDimension
    structural_richness: ScoreDimension
    discoverability: ScoreDimension

    @property
    def total(self) -> int:
        calculated_total = (
            self.semantic_completeness.weighted_contribution
            + self.entity_authority.weighted_contribution
            + self.structural_richness.weighted_contribution
            + self.discoverability.weighted_contribution
        )

        return round(calculated_total)


@dataclass(frozen=True)
class AIReadinessObservations:
    """Raw report observations used by deterministic classifications."""

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
    seo_score: SEOScore
    geo_score: GEOScore


class AssessAIReadiness:
    """Assess one existing analysis report without calling any other service."""

    def execute(
        self,
        report: ArticleAnalysisReport,
    ) -> AIReadinessAssessment:
        observations = self._observations_from(report)
        seo_score = self._calculate_seo_score(report, observations)
        geo_score = self._calculate_geo_score(report, observations)

        return AIReadinessAssessment(
            report=report,
            observations=observations,
            metadata_completeness=self._metadata_completeness(observations),
            seo_score=seo_score,
            geo_score=geo_score,
        )

    @staticmethod
    def _observations_from(
        report: ArticleAnalysisReport,
    ) -> AIReadinessObservations:
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

    def _calculate_seo_score(
        self,
        report: ArticleAnalysisReport,
        observations: AIReadinessObservations,
    ) -> SEOScore:
        """Deterministically calculate SEO score from page measurements."""

        available_metadata_count = sum(
            (
                observations.publication_date_available,
                observations.last_modified_date_available,
                observations.author_available,
                observations.description_available,
            )
        )

        entity_score = (
            available_metadata_count / 4.0
        ) * 100.0

        structured_score = 0.0
        sd_analysis = report.structured_data_analysis

        if sd_analysis is not None and sd_analysis.article_node_present:
            declared_count = len(sd_analysis.declared_article_properties)
            missing_count = len(sd_analysis.missing_article_properties)
            total_expected = declared_count + missing_count

            if total_expected > 0:
                structured_score = (
                    declared_count / total_expected
                ) * 100.0
            else:
                structured_score = 100.0

        semantic_score = 100.0
        dup_analysis = report.content_duplication_analysis

        if (
            dup_analysis is not None
            and dup_analysis.total_passage_count > 0
        ):
            unique_passages = (
                dup_analysis.total_passage_count
                - len(dup_analysis.repeated_passages)
            )

            semantic_score = (
                max(0, unique_passages)
                / dup_analysis.total_passage_count
            ) * 100.0

        technical_score = 100.0
        cons_analysis = report.declared_consistency_analysis

        if cons_analysis is not None:
            technical_score = 100.0

        return SEOScore(
            entity_coverage=ScoreDimension(
                weight_percentage=30,
                dimension_score=entity_score,
            ),
            structured_data=ScoreDimension(
                weight_percentage=25,
                dimension_score=structured_score,
            ),
            semantic_quality=ScoreDimension(
                weight_percentage=25,
                dimension_score=semantic_score,
            ),
            technical_access=ScoreDimension(
                weight_percentage=20,
                dimension_score=technical_score,
            ),
        )

    def _calculate_geo_score(
        self,
        report: ArticleAnalysisReport,
        observations: AIReadinessObservations,
    ) -> GEOScore:
        """Calculate GEO dimensions from deterministic article measurements."""

        # 1. Semantic Completeness (40%)
        # Statistics coverage combined with deterministic fluency measurements.
        passage_quality = report.passage_quality_analysis
        fluency = report.fluency_analysis

        semantic_comp = 0.0

        if passage_quality and passage_quality.passage_profiles:
            profiles = passage_quality.passage_profiles

            stats_count = sum(
                1
                for profile in profiles
                if profile.contains_statistics
            )

            statistics_coverage = (
                stats_count / len(profiles)
            )

            if fluency is not None:
                fluency_score = (
                    fluency.sentence_balance_ratio
                    + fluency.structural_variety_ratio
                ) / 2.0
            else:
                fluency_score = 1.0

            semantic_comp = (
                statistics_coverage
                * fluency_score
                * 100.0
            )

        # 2. Entity & Authority (30%)
        # Citation coverage across article passages.
        entity_auth = 0.0

        if passage_quality and passage_quality.passage_profiles:
            profiles = passage_quality.passage_profiles

            citation_count = sum(
                1
                for profile in profiles
                if profile.contains_citation
            )

            entity_auth = (
                citation_count / len(profiles)
            ) * 100.0

        # 3. Structural Richness (15%)
        # Based on retained structural content and answered questions.
        structural_richness = 0.0
        structural = report.structural_analysis

        if structural and structural.total_word_count > 0:
            structural_words = (
                structural.table_word_count
                + structural.list_word_count
                + structural.blockquote_word_count
            )

            richness_score = (
                structural_words
                / structural.total_word_count
            ) * 100.0

            total_questions = (
                structural.answered_question_heading_count
                + structural.unanswered_question_heading_count
            )

            if total_questions > 0:
                question_score = (
                    structural.answered_question_heading_count
                    / total_questions
                ) * 100.0
            else:
                question_score = 100.0

            structural_richness = (
                richness_score + question_score
            ) / 2.0

        # 4. Discoverability (15%)
        # Based on internal-link coverage.
        discoverability = 0.0
        links = report.internal_link_analysis

        if links:
            if not links.potential_orphan:
                discoverability += 50.0

            if links.outgoing_link_count > 0:
                discoverability += (
                    links.unique_target_count
                    / links.outgoing_link_count
                ) * 50.0

        return GEOScore(
            semantic_completeness=ScoreDimension(
                weight_percentage=40,
                dimension_score=semantic_comp,
            ),
            entity_authority=ScoreDimension(
                weight_percentage=30,
                dimension_score=entity_auth,
            ),
            structural_richness=ScoreDimension(
                weight_percentage=15,
                dimension_score=structural_richness,
            ),
            discoverability=ScoreDimension(
                weight_percentage=15,
                dimension_score=discoverability,
            ),
        )