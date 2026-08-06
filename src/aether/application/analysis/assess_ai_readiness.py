"""Derive deterministic, non-numeric AI Readiness classifications."""

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
class AIReadinessObservations:
    """Raw report observations used by the three deterministic classifications."""

    title_available: bool
    canonical_url_available: bool
    publication_date_available: bool
    last_modified_date_available: bool
    language_available: bool
    author_available: bool
    description_available: bool


@dataclass(frozen=True)
class AIReadinessAssessment:
    """Raw observations plus deterministic readiness classifications only."""

    report: ArticleAnalysisReport
    observations: AIReadinessObservations
    metadata_completeness: CompletenessClassification


class AssessAIReadiness:
    """Assess one existing analysis report without calling any other service."""

    def execute(self, report: ArticleAnalysisReport) -> AIReadinessAssessment:
        observations = self._observations_from(report)
        return AIReadinessAssessment(
            report=report,
            observations=observations,
            metadata_completeness=self._metadata_completeness(observations),
        )

    @staticmethod
    def _observations_from(report: ArticleAnalysisReport) -> AIReadinessObservations:
        metadata = report.metadata_analysis
        return AIReadinessObservations(
            title_available=metadata.title_available,
            canonical_url_available=metadata.canonical_url_available,
            publication_date_available=metadata.publication_date_available,
            last_modified_date_available=metadata.last_modified_date_available,
            language_available=metadata.language_available,
            author_available=metadata.author_available,
            description_available=metadata.description_available,
        )

    @staticmethod
    def _metadata_completeness(
        observations: AIReadinessObservations,
    ) -> CompletenessClassification:
        availability = (
            observations.title_available,
            observations.canonical_url_available,
            observations.publication_date_available,
            observations.last_modified_date_available,
            observations.language_available,
            observations.author_available,
            observations.description_available,
        )
        if all(availability):
            return CompletenessClassification.COMPLETE
        if any(availability):
            return CompletenessClassification.PARTIAL
        return CompletenessClassification.MISSING

