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
    semantic_completeness: ScoreDimension   # %40
    entity_authority: ScoreDimension        # %30
    structural_richness: ScoreDimension     # %15
    discoverability: ScoreDimension         # %15

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
    seo_score: SEOScore
    geo_score: GEOScore


class AssessAIReadiness:
    """Assess one existing analysis report without calling any other service."""

    def execute(self, report: ArticleAnalysisReport) -> AIReadinessAssessment:
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

    def _calculate_seo_score(
        self, 
        report: ArticleAnalysisReport, 
        observations: AIReadinessObservations
    ) -> SEOScore:
        """Deterministically calculate SEO score strictly based on page measurements."""
        available_metadata_count = sum([
            observations.publication_date_available,
            observations.last_modified_date_available,
            observations.author_available,
            observations.description_available
        ])
        entity_score = (available_metadata_count / 4.0) * 100.0

        structured_score = 0.0
        sd_analysis = report.structured_data_analysis
        if sd_analysis is not None and sd_analysis.article_node_present:
            declared_count = len(sd_analysis.declared_article_properties)
            missing_count = len(sd_analysis.missing_article_properties)
            total_expected = declared_count + missing_count
            if total_expected > 0:
                structured_score = (declared_count / total_expected) * 100.0
            else:
                structured_score = 100.0
        
        semantic_score = 100.0
        dup_analysis = report.content_duplication_analysis
        if dup_analysis is not None and dup_analysis.total_passage_count > 0:
            unique_passages = dup_analysis.total_passage_count - len(dup_analysis.repeated_passages)
            semantic_score = (max(0, unique_passages) / dup_analysis.total_passage_count) * 100.0

        technical_score = 100.0
        cons_analysis = report.declared_consistency_analysis
        if cons_analysis is not None:
            technical_score = 100.0

        return SEOScore(
            entity_coverage=ScoreDimension(weight_percentage=30, dimension_score=entity_score),
            structured_data=ScoreDimension(weight_percentage=25, dimension_score=structured_score),
            semantic_quality=ScoreDimension(weight_percentage=25, dimension_score=semantic_score),
            technical_access=ScoreDimension(weight_percentage=20, dimension_score=technical_score),
        )

    def _calculate_geo_score(
        self,
        report: ArticleAnalysisReport,
        observations: AIReadinessObservations
    ) -> GEOScore:
        # 1. Semantic Completeness (40%)
        # Based on passages with statistics and fluency penalty
        passage_quality = report.passage_quality_analysis
        semantic_comp = 0.0
        if passage_quality and len(passage_quality.passage_profiles) > 0:
            profiles = passage_quality.passage_profiles
            stats_count = sum(1 for p in profiles if p.contains_statistics)
            stats_score = (stats_count / len(profiles)) * 100.0
            
            # Add N-gram overlap and definitive stance as positive signals
            overlap_score = report.structural_analysis.heading_passage_overlap_ratio * 100.0
            stance_score = report.structural_analysis.definitive_stance_ratio * 100.0
            
            base_score = (stats_score + overlap_score + stance_score) / 3.0
            
            # Fluency balance multiplier (up to 1.0)
            balance = passage_quality.passage_balance_ratio
            
            # Keyword stuffing penalty (deduct up to 20 points based on ratio)
            penalty = passage_quality.keyword_stuffing_ratio * 100.0 * 2.0 # Arbitrary simple scaling
            penalty = min(penalty, 20.0)
            
            semantic_comp = max(0.0, (base_score * balance) - penalty)
        
        # 2. Entity & Authority (30%)
        # Based on citations and outbound domains
        entity_auth = 0.0
        
        # Sanity Check (Cross Validation): If there are no outbound domains,
        # entity authority must be 0, regardless of raw citation marks.
        outbound_domains = report.internal_link_analysis.outbound_domains if report.internal_link_analysis else ()
        
        _SOCIAL_DOMAINS = {"reddit.com", "twitter.com", "x.com", "facebook.com", "instagram.com", "tiktok.com", "linkedin.com", "pinterest.com"}
        
        social_count = sum(1 for d in outbound_domains if d in _SOCIAL_DOMAINS or any(d.endswith(f".{s}") for s in _SOCIAL_DOMAINS))
        earned_count = len(outbound_domains) - social_count
        
        earned_media_multiplier = getattr(report.internal_link_analysis, 'third_party_ratio', 0.0) if report.internal_link_analysis else 0.0
        
        if len(outbound_domains) > 0 and passage_quality and len(passage_quality.passage_profiles) > 0:
            profiles = passage_quality.passage_profiles
            cit_count = sum(1 for p in profiles if p.contains_citation)
            effective_cit_count = cit_count + earned_count
            
            # Apply unsupported entities penalty
            unsupported_penalty = 1.0
            if report.structural_analysis:
                unsupported_ratio = getattr(report.structural_analysis, 'unsupported_entity_ratio', 0.0)
                if unsupported_ratio > 0:
                    unsupported_penalty = 1.0 - (unsupported_ratio * 0.5) # Up to 50% penalty
                    
            # Base authority purely on citations, but strictly gated by third-party multiplier and trust index
            trust_index = getattr(report.internal_link_analysis, 'trust_index', 0.0) if report.internal_link_analysis else 0.0
            
            entity_auth = min((effective_cit_count / len(profiles)) * 100.0, 100.0) * earned_media_multiplier * unsupported_penalty * (0.5 + trust_index / 2)
            
        # 3. Structural Richness (15%)
        # Direct Answer Patterns + Table/List Density
        structural_richness = 0.0
        struct = report.structural_analysis
        if struct and struct.total_word_count > 0:
            # Ratio of structured words
            struct_words = struct.table_word_count + struct.list_word_count + struct.blockquote_word_count
            richness_score = min((struct_words / struct.total_word_count) * 100.0, 100.0)
            
            # Answered questions boost
            total_q = struct.answered_question_heading_count + struct.unanswered_question_heading_count
            q_score = 100.0 if total_q == 0 else (struct.answered_question_heading_count / total_q) * 100.0
            
            structural_richness = (richness_score * 0.5) + (q_score * 0.5)
            
        # 4. Discoverability (15%)
        # Internal links
        discoverability = 0.0
        links = report.internal_link_analysis
        if links:
            if not links.potential_orphan:
                discoverability += 50.0 # Not an orphan
            if links.outgoing_link_count > 0:
                # Based on uniqueness ratio
                discoverability += (links.unique_target_count / links.outgoing_link_count) * 50.0

        return GEOScore(
            semantic_completeness=ScoreDimension(weight_percentage=40, dimension_score=semantic_comp),
            entity_authority=ScoreDimension(weight_percentage=30, dimension_score=entity_auth),
            structural_richness=ScoreDimension(weight_percentage=15, dimension_score=structural_richness),
            discoverability=ScoreDimension(weight_percentage=15, dimension_score=discoverability),
        )