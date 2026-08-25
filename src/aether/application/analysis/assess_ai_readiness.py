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


from typing import Optional

@dataclass(frozen=True)
class ScoreDimension:
    """Represents a single dimension of the AI Readiness Score.

    Scores are derived from measured ratios rather than arbitrary thresholds.
    """

    weight_percentage: int
    dimension_score: Optional[float]

    def __post_init__(self):
        if self.dimension_score is not None and not (0.0 <= self.dimension_score <= 100.0):
            raise ValueError(f"Score must be between 0 and 100, got {self.dimension_score}")
        if not (0 <= self.weight_percentage <= 100):
            raise ValueError(f"Weight must be between 0 and 100, got {self.weight_percentage}")

    @property
    def weighted_contribution(self) -> float:
        """Return the actual point contribution to the total score."""
        if self.dimension_score is None:
            return 0.0
        return self.dimension_score * (self.weight_percentage / 100.0)


@dataclass(frozen=True)
class SEOScore:
    """Composite 0-100 score for traditional SEO dimensions."""

    entity_coverage: ScoreDimension
    structured_data: ScoreDimension
    semantic_quality: ScoreDimension
    technical_access: ScoreDimension

    @property
    def total(self) -> Optional[int]:
        dimensions = [self.entity_coverage, self.structured_data, self.semantic_quality, self.technical_access]
        available_weight = sum(d.weight_percentage for d in dimensions if d.dimension_score is not None)
        if available_weight == 0:
            return None
        calculated_total = sum(d.weighted_contribution for d in dimensions)
        return round(calculated_total / (available_weight / 100.0))


@dataclass(frozen=True)
class GEOScore:
    """Composite 0-100 score for Generative Engine Optimization principles."""

    semantic_completeness: ScoreDimension
    entity_authority: ScoreDimension
    structural_richness: ScoreDimension
    discoverability: ScoreDimension

    @property
    def total(self) -> Optional[int]:
        dimensions = [self.semantic_completeness, self.entity_authority, self.structural_richness, self.discoverability]
        available_weight = sum(d.weight_percentage for d in dimensions if d.dimension_score is not None)
        if available_weight == 0:
            return None
        calculated_total = sum(d.weighted_contribution for d in dimensions)
        return round(calculated_total / (available_weight / 100.0))


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

        structured_score = None
        sd_analysis = report.structured_data_analysis
        if sd_analysis is not None:
            if sd_analysis.article_node_present:
                declared_count = len(sd_analysis.declared_article_properties)
                missing_count = len(sd_analysis.missing_article_properties)
                total_expected = declared_count + missing_count
                if total_expected > 0:
                    structured_score = (declared_count / total_expected) * 100.0
                else:
                    structured_score = 100.0
            else:
                structured_score = 0.0

        semantic_score = None
        dup_analysis = report.content_duplication_analysis
        if not report.body_capture_is_reliable:
            semantic_score = None
        elif dup_analysis is not None:
            if dup_analysis.total_passage_count > 0:
                unique_passages = dup_analysis.total_passage_count - len(dup_analysis.repeated_passages)
                semantic_score = (max(0, unique_passages) / dup_analysis.total_passage_count) * 100.0
            else:
                semantic_score = 0.0

        technical_score = None
        cons_analysis = report.declared_consistency_analysis

        if cons_analysis is not None:
            if getattr(cons_analysis, 'title_sources_disagree', False) or getattr(cons_analysis, 'description_sources_disagree', False):
                technical_score = 0.0
            else:
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
        if not report.body_capture_is_reliable:
            return GEOScore(
                semantic_completeness=ScoreDimension(weight_percentage=40, dimension_score=None),
                entity_authority=ScoreDimension(weight_percentage=30, dimension_score=None),
                structural_richness=ScoreDimension(weight_percentage=15, dimension_score=None),
                discoverability=ScoreDimension(weight_percentage=15, dimension_score=None),
            )
        semantic_comp = None
        if passage_quality and len(passage_quality.passage_profiles) > 0:
            profiles = passage_quality.passage_profiles
            stats_count = sum(1 for p in profiles if p.contains_statistics)
            stats_score = (stats_count / len(profiles)) * 100.0

            # Add N-gram overlap and definitive stance as positive signals
            overlap_score = getattr(report.structural_analysis, 'heading_passage_overlap_ratio', 0.0) * 100.0
            stance_score = getattr(report.structural_analysis, 'definitive_stance_ratio', 0.0) * 100.0

            content_score = (stats_score * 0.4) + (overlap_score * 0.3) + (stance_score * 0.3)
            if fluency is not None:
                bounded_structural_variety = min(
                    1.0, fluency.structural_variety_ratio
                )
                fluency_score = (
                    (
                        fluency.sentence_balance_ratio
                        + bounded_structural_variety
                    )
                    / 2.0
                    * 100.0
                )
                content_score = (content_score + fluency_score) / 2.0

            semantic_comp = content_score * passage_quality.passage_balance_ratio

        # 2. Entity & Authority (30%)
        # Her bilesen makale-kapsamli ve bagimsiz olculur. Olculemeyen bir
        # bilesen ortalamaya sifir olarak girmez, ortalamadan tamamen duser:
        # sabit /4.0 paydasi, calistirilmamis bir analizi kotu bir sonuc gibi
        # puanliyordu (0005).
        sd_analysis = report.structured_data_analysis
        links = report.internal_link_analysis
        struct = report.structural_analysis

        components = []

        # Beyan edilmemis yazar olculmus bir eksikliktir. Yapisal veri analizi
        # hic komposize edilmemisse (taslak akisi) hicbir sey olculmemistir.
        if sd_analysis is not None:
            components.append(
                100.0 if "author" in sd_analysis.declared_article_properties else 0.0
            )

        if links is not None:
            # Esik gerektirmeyen ikili olcum: govde disariya atif yapiyor mu?
            components.append(100.0 if links.outbound_body_domains else 0.0)
            if links.trust_index is not None:
                components.append(links.trust_index * 100.0)
            if links.third_party_ratio is not None:
                components.append(links.third_party_ratio * 100.0)

        if struct is not None and struct.unsupported_entity_ratio is not None:
            components.append((1.0 - struct.unsupported_entity_ratio) * 100.0)

        if passage_quality and passage_quality.passage_profiles:
            profiles = passage_quality.passage_profiles
            citation_count = sum(1 for p in profiles if p.contains_citation)
            components.append(citation_count / len(profiles) * 100.0)

        claim_evidence = report.claim_evidence_analysis
        if claim_evidence is not None and claim_evidence.detectable_claim_count > 0:
            components.append(claim_evidence.claim_evidence_coverage * 100.0)

        entity_auth = sum(components) / len(components) if components else None

        # 3. Structural Richness (15%)
        # Direct Answer Patterns + Table/List Density
        structural_richness = None
        struct = report.structural_analysis
        if struct and struct.total_word_count > 0:
            # Ratio of structured words (paydaya struct_words eklendi)
            struct_words = struct.table_word_count + struct.list_word_count + struct.blockquote_word_count
            richness_score = (struct_words / (struct.total_word_count + struct_words)) * 100.0

            # Answered questions boost (total_q == 0 ise skoru cezalandirma, sadece richness kullan)
            total_q = struct.answered_question_heading_count + struct.unanswered_question_heading_count
            if total_q == 0:
                structural_richness = richness_score
            else:
                q_score = (struct.answered_question_heading_count / total_q) * 100.0
                structural_richness = (richness_score * 0.5) + (q_score * 0.5)

        # 4. Discoverability (15%)
        # Based solely on body links ratio (No potential_orphan or arbitrary constants)
        discoverability = None
        links = report.internal_link_analysis

        if links:
            if links.outgoing_link_count > 0:
                discoverability = (links.body_link_count / links.outgoing_link_count) * 100.0
            else:
                discoverability = 0.0

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
