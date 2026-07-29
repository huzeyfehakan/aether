"""Aggregate existing immutable analysis results without interpretation."""

from dataclasses import dataclass

from aether.application.analysis.analyze_article_metadata import (
    AnalyzeArticleMetadata,
    MetadataAnalysis,
)
from aether.application.analysis.analyze_article_structure import (
    AnalyzeArticleStructure,
    ArticleStructuralAnalysis,
)
from aether.application.analysis.analyze_passage_quality import (
    AnalyzePassageQuality,
    PassageQualityAnalysis,
)
from aether.domain.common import DomainValidationError
from aether.domain.content import Article


@dataclass(frozen=True)
class ArticleAnalysisReport:
    """An immutable container of existing raw analysis results only."""

    structural_analysis: ArticleStructuralAnalysis
    metadata_analysis: MetadataAnalysis
    passage_quality_analysis: PassageQualityAnalysis

    def __post_init__(self) -> None:
        article_ids = {
            self.structural_analysis.article_id,
            self.metadata_analysis.article_id,
            self.passage_quality_analysis.article_id,
        }
        version_ids = {
            self.structural_analysis.article_version_id,
            self.metadata_analysis.article_version_id,
            self.passage_quality_analysis.article_version_id,
        }
        if len(article_ids) != 1 or len(version_ids) != 1:
            raise DomainValidationError(
                "all report analyses must refer to the same article version"
            )


class BuildArticleAnalysisReport:
    """Compose a report by executing the already-defined raw analysis use cases."""

    def __init__(
        self,
        structure_analysis: AnalyzeArticleStructure,
        metadata_analysis: AnalyzeArticleMetadata,
        passage_quality_analysis: AnalyzePassageQuality,
    ) -> None:
        self._structure_analysis = structure_analysis
        self._metadata_analysis = metadata_analysis
        self._passage_quality_analysis = passage_quality_analysis

    def execute(self, article: Article, article_version_id: str) -> ArticleAnalysisReport:
        return ArticleAnalysisReport(
            structural_analysis=self._structure_analysis.execute(article, article_version_id),
            metadata_analysis=self._metadata_analysis.execute(article, article_version_id),
            passage_quality_analysis=self._passage_quality_analysis.execute(
                article, article_version_id
            ),
        )
