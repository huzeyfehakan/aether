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
                table_word_count=0,
                list_word_count=0,
                blockquote_word_count=0,
                answered_question_heading_count=0,
                unanswered_question_heading_count=0,
            ),
            metadata_analysis=MetadataAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                title_length=12,
                publication_date_available=True,
                last_modified_date_available=False,
                author_available=True,
                description_available=False,
            ),
            passage_quality_analysis=PassageQualityAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                passage_profiles=(
                    PassageProfile(
                        passage_id="p-1",
                        ordinal_position=1,
                        word_count=4,
                        character_count=20,
                        contains_statistics=False,
                        contains_citation=False,
                    ),
                ),
                passage_balance_ratio=1.0,
                keyword_stuffing_ratio=0.0,
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
        entity_detail = payload["assessment_summary"]["geo_score"][
            "entity_authority"
        ]["detail"]
        signals = {
            signal["label"]: signal["value"]
            for signal in entity_detail["signals"]
        }
        self.assertEqual(signals["Citation coverage"], 0.0)
        self.assertIsNone(signals["Claim evidence coverage"])
        geo_score = payload["assessment_summary"]["geo_score"]
        for dimension in (
            "semantic_completeness",
            "entity_authority",
            "structural_richness",
            "discoverability",
        ):
            self.assertIn("detail", geo_score[dimension])
        structural_signals = {
            signal["label"]: signal["value"]
            for signal in geo_score["structural_richness"]["detail"]["signals"]
        }
        self.assertIsNone(structural_signals["Answered question ratio"])
        self.assertNotIn("score", payload)
        self.assertNotIn("recommendations", payload)

    def test_plain_text_renderer_includes_all_required_summaries(self):
        rendered = PlainTextAIReadinessReportRenderer().render(self.report())

        self.assertIn("AI Readiness Report", rendered)
        self.assertIn("Article Identity", rendered)
        self.assertIn("Structural Summary", rendered)
        self.assertIn("Extracted Metadata", rendered)
        self.assertIn("Metadata Completeness: partial", rendered)
        self.assertIn("Claim evidence coverage: Not measured", rendered)
        # Optional sections are absent when their analysis was not composed.
        self.assertNotIn("Structured Data (Schema.org)", rendered)
        self.assertIn("Metadata Completeness: partial", rendered)

    def test_markdown_renderer_includes_report_values_and_profile_table(self):
        rendered = MarkdownAIReadinessReportRenderer().render(self.report())

        self.assertIn("# AI Readiness Report", rendered)
        self.assertIn("## Article Identity", rendered)
        self.assertIn("## Structural Summary", rendered)
        self.assertIn("## Extracted Metadata", rendered)
        self.assertIn("| `p-1` | 1 | 4 | 20 |", rendered)

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
