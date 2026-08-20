"""Measure deterministic claim-to-evidence coverage for one article version."""

from dataclasses import dataclass

from aether.application.analysis.analyze_passage_quality import (
    AnalyzePassageQuality,
)
from aether.domain.common import DomainValidationError
from aether.domain.content import Article
from aether.ports.outbound.content_repository import ContentRepository


@dataclass(frozen=True)
class ClaimEvidenceAnalysis:
    """Deterministic coverage of detectable claims with citations."""

    article_id: str
    article_version_id: str
    detectable_claim_count: int
    supported_claim_count: int
    claim_evidence_coverage: float


class AnalyzeClaimEvidence:
    """Measure whether detectable statistical claims have citation evidence."""

    def __init__(
        self,
        content_repository: ContentRepository,
        passage_quality_analysis: AnalyzePassageQuality,
    ) -> None:
        self._content_repository = content_repository
        self._passage_quality_analysis = passage_quality_analysis

    def execute(
        self,
        article: Article,
        article_version_id: str,
    ) -> ClaimEvidenceAnalysis:
        article_version = self._content_repository.get_article_version(
            article_version_id
        )

        if article_version.article_id != article.article_id:
            raise DomainValidationError(
                "article version must belong to the article being analyzed"
            )

        passage_quality = self._passage_quality_analysis.execute(
            article,
            article_version_id,
        )

        profiles = passage_quality.passage_profiles

        detectable_claim_count = sum(
            1
            for profile in profiles
            if profile.contains_statistics
        )

        supported_claim_count = sum(
            1
            for profile in profiles
            if profile.contains_statistics
            and profile.contains_citation
        )

        claim_evidence_coverage = (
            supported_claim_count / detectable_claim_count
            if detectable_claim_count
            else 0.0
        )

        return ClaimEvidenceAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            detectable_claim_count=detectable_claim_count,
            supported_claim_count=supported_claim_count,
            claim_evidence_coverage=claim_evidence_coverage,
        )