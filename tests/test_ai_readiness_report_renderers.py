import json
import sys
import unittest

sys.path.insert(0, "src")

from aether.application.analysis.analyze_article_metadata import MetadataAnalysis  # noqa: E402
from aether.application.analysis.analyze_article_structure import (  # noqa: E402
    ArticleStructuralAnalysis,
)
from aether.application.analysis.analyze_passage_quality import (  # noqa: E402
    PassageProfile,
    PassageQualityAnalysis,
)
from aether.application.analysis.assess_ai_readiness import (  # noqa: E402
    AssessAIReadiness,
)
from aether.application.analysis.build_ai_readiness_report import (  # noqa: E402
    BuildAIReadinessReport,
)
from aether.application.analysis.build_article_analysis_report import (  # noqa: E402
    ArticleAnalysisReport,
)
from aether.presentation.ai_readiness_report_renderers import (  # noqa: E402
    JsonAIReadinessReportRenderer,
    MarkdownAIReadinessReportRenderer,
    PlainTextAIReadinessReportRenderer,
)


class AIReadinessReportRendererTests(unittest.TestCase):
    def report(self):
        analysis_report = ArticleAnalysisReport(
            structural_analysis=ArticleStructuralAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                total_passage_count=1,
                total_word_count=4,
            ),
            metadata_analysis=MetadataAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                title_available=True,
                title_length=12,
                canonical_url_available=True,
                publication_date_available=True,
                last_modified_date_available=False,
                language_available=True,
                author_available=True,
                description_available=False,
            ),
            passage_quality_analysis=PassageQualityAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                passage_profiles=(
                    PassageProfile(
                        passage_id="version-1:p0",
                        ordinal_position=0,
                        word_count=4,
                        character_count=20,
                    ),
                ),
                minimum_passage_word_count=4,
                maximum_passage_word_count=4,
                median_passage_word_count=4.0,
            ),
        )
        return BuildAIReadinessReport().execute(
            AssessAIReadiness().execute(analysis_report)
        )

    def test_json_renderer_serializes_existing_report_values(self):
        rendered = JsonAIReadinessReportRenderer().render(self.report())
        payload = json.loads(rendered)

        self.assertEqual(payload["article_identity"]["article_id"], "article-1")
        self.assertEqual(payload["structural_summary"]["total_word_count"], 4)
        self.assertTrue(payload["metadata_summary"]["author_available"])
        self.assertNotIn("score", payload)
        self.assertNotIn("recommendations", payload)

    def test_plain_text_renderer_includes_all_required_summaries(self):
        rendered = PlainTextAIReadinessReportRenderer().render(self.report())

        self.assertIn("AI Readiness Report", rendered)
        self.assertIn("Article Identity", rendered)
        self.assertIn("Structural Summary", rendered)
        self.assertIn("Metadata Summary", rendered)
        self.assertIn("Passage Quality Summary", rendered)
        self.assertIn("Assessment Summary", rendered)
        self.assertIn("Metadata Completeness: partial", rendered)

    def test_markdown_renderer_includes_report_values_and_profile_table(self):
        rendered = MarkdownAIReadinessReportRenderer().render(self.report())

        self.assertIn("# AI Readiness Report", rendered)
        self.assertIn("## Article Identity", rendered)
        self.assertIn("## Structural Summary", rendered)
        self.assertIn("## Metadata Summary", rendered)
        self.assertIn("## Passage Quality Summary", rendered)
        self.assertIn("## Assessment Summary", rendered)
        self.assertIn("| `version-1:p0` | 0 | 4 | 20 |", rendered)

    def test_renderers_are_deterministic(self):
        report = self.report()
        renderers = (
            JsonAIReadinessReportRenderer(),
            PlainTextAIReadinessReportRenderer(),
            MarkdownAIReadinessReportRenderer(),
        )

        for renderer in renderers:
            self.assertEqual(renderer.render(report), renderer.render(report))


if __name__ == "__main__":
    unittest.main()
