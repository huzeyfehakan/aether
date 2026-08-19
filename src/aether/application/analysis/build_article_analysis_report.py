"""Aggregate existing immutable analysis results without interpretation."""

from dataclasses import dataclass
from typing import Optional

from aether.application.analysis.analyze_article_metadata import (
    AnalyzeArticleMetadata,
    MetadataAnalysis,
)
from aether.application.analysis.analyze_article_structure import (
    AnalyzeArticleStructure,
    ArticleStructuralAnalysis,
)
from aether.application.analysis.analyze_content_duplication import (
    AnalyzeContentDuplication,
    ContentDuplicationAnalysis,
)
from aether.application.analysis.analyze_heading_structure import (
    AnalyzeHeadingStructure,
    HeadingStructureAnalysis,
)
from aether.application.analysis.analyze_declared_consistency import (
    AnalyzeDeclaredConsistency,
    DeclaredConsistencyAnalysis,
)
from aether.application.analysis.analyze_structured_data import (
    AnalyzeStructuredData,
    StructuredDataAnalysis,
)
from aether.application.analysis.analyze_passage_quality import (
    AnalyzePassageQuality,
    PassageQualityAnalysis,
)
from aether.application.analysis.analyze_passage_readiness import (
    AnalyzePassageReadiness,
    PassageReadinessAnalysis,
)
from aether.domain.common import DomainValidationError
from aether.domain.content import Article


@dataclass(frozen=True)
class ArticleAnalysisReport:
    """An immutable container of existing raw analysis results only.

    ``content_duplication_analysis`` is optional. Comparing an article against
    other articles is a corpus-aware capability: it needs a stored publisher
    corpus, and a caller analysing a single article in isolation can compose
    the report without it.
    """

    structural_analysis: ArticleStructuralAnalysis
    metadata_analysis: MetadataAnalysis
    passage_quality_analysis: PassageQualityAnalysis
    content_duplication_analysis: Optional[ContentDuplicationAnalysis] = None
    structured_data_analysis: Optional[StructuredDataAnalysis] = None
    declared_consistency_analysis: Optional[DeclaredConsistencyAnalysis] = None
    heading_structure_analysis: Optional[HeadingStructureAnalysis] = None
    passage_readiness_analysis: Optional[PassageReadinessAnalysis] = None
    #: An unpublished draft. Metadata, declared consistency and structured data
    #: describe the published page, which does not exist yet, so findings about
    #: them would be about the CMS template rather than the draft.
    is_draft: bool = False

    def __post_init__(self) -> None:
        analyses = [
            self.structural_analysis,
            self.metadata_analysis,
            self.passage_quality_analysis,
        ]
        if self.content_duplication_analysis is not None:
            analyses.append(self.content_duplication_analysis)
        if self.structured_data_analysis is not None:
            analyses.append(self.structured_data_analysis)
        if self.declared_consistency_analysis is not None:
            analyses.append(self.declared_consistency_analysis)
        if self.heading_structure_analysis is not None:
            analyses.append(self.heading_structure_analysis)
        if self.passage_readiness_analysis is not None:
            analyses.append(self.passage_readiness_analysis)
        article_ids = {analysis.article_id for analysis in analyses}
        version_ids = {analysis.article_version_id for analysis in analyses}
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
        content_duplication_analysis: Optional[AnalyzeContentDuplication] = None,
        structured_data_analysis: Optional[AnalyzeStructuredData] = None,
        declared_consistency_analysis: Optional[AnalyzeDeclaredConsistency] = None,
        heading_structure_analysis: Optional[AnalyzeHeadingStructure] = None,
        passage_readiness_analysis: Optional[AnalyzePassageReadiness] = None,
        is_draft: bool = False,
    ) -> None:
        self._structure_analysis = structure_analysis
        self._metadata_analysis = metadata_analysis
        self._passage_quality_analysis = passage_quality_analysis
        self._content_duplication_analysis = content_duplication_analysis
        self._structured_data_analysis = structured_data_analysis
        self._declared_consistency_analysis = declared_consistency_analysis
        self._heading_structure_analysis = heading_structure_analysis
        self._passage_readiness_analysis = passage_readiness_analysis
        self._is_draft = is_draft

    def execute(self, article: Article, article_version_id: str) -> ArticleAnalysisReport:
        return ArticleAnalysisReport(
            structural_analysis=self._structure_analysis.execute(article, article_version_id),
            metadata_analysis=self._metadata_analysis.execute(article, article_version_id),
            passage_quality_analysis=self._passage_quality_analysis.execute(
                article, article_version_id
            ),
            content_duplication_analysis=(
                self._content_duplication_analysis.execute(article, article_version_id)
                if self._content_duplication_analysis is not None
                else None
            ),
            structured_data_analysis=(
                self._structured_data_analysis.execute(article, article_version_id)
                if self._structured_data_analysis is not None
                else None
            ),
            declared_consistency_analysis=(
                self._declared_consistency_analysis.execute(article, article_version_id)
                if self._declared_consistency_analysis is not None
                else None
            ),
            heading_structure_analysis=(
                self._heading_structure_analysis.execute(article, article_version_id)
                if self._heading_structure_analysis is not None
                else None
            ),
            passage_readiness_analysis=(
                self._passage_readiness_analysis.execute(article, article_version_id)
                if self._passage_readiness_analysis is not None
                else None
            ),
            is_draft=self._is_draft,
        )
