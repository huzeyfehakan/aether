"""Offline end-to-end acceptance coverage for a representative publisher article."""

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

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
from aether.application.analysis.assess_ai_readiness import (  # noqa: E402
    AssessAIReadiness,
)
from aether.application.analysis.build_ai_readiness_report import (  # noqa: E402
    BuildAIReadinessReport,
)
from aether.application.analysis.build_article_analysis_report import (  # noqa: E402
    BuildArticleAnalysisReport,
)
from aether.application.ingestion.register_raw_html_article import (  # noqa: E402
    RawHtmlArticle,
    RegisterRawHtmlArticle,
)
from aether.presentation.ai_readiness_report_renderers import (  # noqa: E402
    JsonAIReadinessReportRenderer,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "trt_world_erdogan_kazakhstan.html"
OBSERVED_AT = datetime(2026, 7, 27, 9, 0, tzinfo=timezone.utc)


class HappyPathPublisherArticleAcceptanceTests(unittest.TestCase):
    """Validate the complete deterministic MVP path against offline publisher HTML."""

    def build_report(self):
        repository = InMemoryContentRepository()
        registration = RegisterRawHtmlArticle(repository).execute(
            RawHtmlArticle(
                html=FIXTURE_PATH.read_text(encoding="utf-8"),
                source_url="https://www.trtworld.com/article/3e946db45c45",
                publisher="TRT World",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )
        analysis_report = BuildArticleAnalysisReport(
            AnalyzeArticleStructure(repository),
            AnalyzeArticleMetadata(repository),
            AnalyzePassageQuality(repository),
        ).execute(registration.article, registration.article_version.article_version_id)
        return registration, BuildAIReadinessReport().execute(
            AssessAIReadiness().execute(analysis_report)
        )

    def test_trt_world_fixture_produces_a_complete_deterministic_report(self):
        registration, report = self.build_report()

        self.assertTrue(registration.version_created)
        self.assertEqual(registration.article.publisher, "TRT World")
        self.assertEqual(
            registration.article.canonical_source,
            "https://www.trtworld.com/article/3e946db45c45",
        )
        self.assertEqual(registration.article.original_language, "en")
        self.assertEqual(len(registration.passages), 3)
        self.assertEqual(
            [passage.location_anchor for passage in registration.passages],
            ["paragraph:1", "paragraph:2", "paragraph:3"],
        )

        self.assertEqual(report.structural_summary.total_passage_count, 3)
        self.assertEqual(report.structural_summary.total_word_count, 47)
        self.assertTrue(all(vars(report.metadata_summary).values()))
        self.assertEqual(report.assessment_summary.metadata_completeness.value, "complete")

        rendered = JsonAIReadinessReportRenderer().render(report)
        payload = json.loads(rendered)
        self.assertEqual(payload["structural_summary"]["total_passage_count"], 3)
        self.assertEqual(payload["metadata_summary"]["title_length"], 65)
        self.assertEqual(payload["assessment_summary"], {
            "metadata_completeness": "complete",
        })
        self.assertNotIn("raw_html", rendered)
        self.assertNotIn("structured_data_raw", rendered)

    def test_trt_world_fixture_report_is_deterministic(self):
        _, first = self.build_report()
        _, second = self.build_report()

        renderer = JsonAIReadinessReportRenderer()
        self.assertEqual(renderer.render(first), renderer.render(second))


if __name__ == "__main__":
    unittest.main()
