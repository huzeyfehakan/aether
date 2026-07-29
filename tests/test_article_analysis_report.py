import sys
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

sys.path.insert(0, "src")

from aether.adapters.outbound.in_memory_content_repository import (  # noqa: E402
    InMemoryContentRepository,
)
from aether.application.analysis.analyze_article_metadata import (  # noqa: E402
    AnalyzeArticleMetadata,
)
from aether.application.analysis.analyze_article_structure import (  # noqa: E402
    AnalyzeArticleStructure,
)
from aether.application.analysis.analyze_passage_quality import (  # noqa: E402
    AnalyzePassageQuality,
)
from aether.application.analysis.build_article_analysis_report import (  # noqa: E402
    ArticleAnalysisReport,
    BuildArticleAnalysisReport,
)
from aether.application.ingestion.register_source_snapshot import (  # noqa: E402
    RegisterSourceSnapshot,
    SourceArticleSnapshot,
)
from aether.domain.common import DomainValidationError  # noqa: E402


NOW = datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc)


class ArticleAnalysisReportTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryContentRepository()
        self.register = RegisterSourceSnapshot(self.repository)
        self.structure = AnalyzeArticleStructure(self.repository)
        self.metadata = AnalyzeArticleMetadata(self.repository)
        self.passage_quality = AnalyzePassageQuality(self.repository)
        self.build_report = BuildArticleAnalysisReport(
            self.structure, self.metadata, self.passage_quality
        )

    def register_article(self, source_url, body):
        return self.register.execute(
            SourceArticleSnapshot(
                publisher="TRT",
                canonical_source=source_url,
                original_language="tr",
                article_type="news_report",
                title="A report",
                body=body,
                observed_at=NOW,
                source_published_at=NOW,
            )
        )

    def test_report_aggregates_existing_analysis_results_without_scoring(self):
        registered = self.register_article(
            "https://example.org/news/story", "First paragraph.\n\nSecond paragraph."
        )

        report = self.build_report.execute(
            registered.article, registered.article_version.article_version_id
        )

        self.assertEqual(
            report.structural_analysis,
            self.structure.execute(
                registered.article, registered.article_version.article_version_id
            ),
        )
        self.assertEqual(
            report.metadata_analysis,
            self.metadata.execute(
                registered.article, registered.article_version.article_version_id
            ),
        )
        self.assertEqual(
            report.passage_quality_analysis,
            self.passage_quality.execute(
                registered.article, registered.article_version.article_version_id
            ),
        )
        self.assertFalse(hasattr(report, "ai_readiness_score"))

    def test_report_is_immutable(self):
        registered = self.register_article(
            "https://example.org/news/story", "Only paragraph."
        )
        report = self.build_report.execute(
            registered.article, registered.article_version.article_version_id
        )

        with self.assertRaises(FrozenInstanceError):
            report.metadata_analysis = None

    def test_report_rejects_results_from_different_article_versions(self):
        first = self.register_article(
            "https://example.org/news/first", "First paragraph."
        )
        second = self.register_article(
            "https://example.org/news/second", "Second paragraph."
        )

        with self.assertRaises(DomainValidationError):
            ArticleAnalysisReport(
                structural_analysis=self.structure.execute(
                    first.article, first.article_version.article_version_id
                ),
                metadata_analysis=self.metadata.execute(
                    second.article, second.article_version.article_version_id
                ),
                passage_quality_analysis=self.passage_quality.execute(
                    first.article, first.article_version.article_version_id
                ),
            )

    def test_report_is_deterministic(self):
        registered = self.register_article(
            "https://example.org/news/story", "Stable paragraph."
        )

        first = self.build_report.execute(
            registered.article, registered.article_version.article_version_id
        )
        second = self.build_report.execute(
            registered.article, registered.article_version.article_version_id
        )

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
