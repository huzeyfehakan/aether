import sys
import unittest
from dataclasses import FrozenInstanceError

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
    AIReadinessReport,
    BuildAIReadinessReport,
)
from aether.application.analysis.build_article_analysis_report import (  # noqa: E402
    ArticleAnalysisReport,
)


class AIReadinessReportTests(unittest.TestCase):
    def assessment(self):
        report = ArticleAnalysisReport(
            structural_analysis=ArticleStructuralAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                total_passage_count=2,
                total_word_count=12,
                table_word_count=0,
                list_word_count=0,
                blockquote_word_count=0,
                answered_question_heading_count=0,
                unanswered_question_heading_count=0,
            ),
            metadata_analysis=MetadataAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                title_length=14,
                publication_date_available=True,
                last_modified_date_available=False,
                author_available=True,
                description_available=True,
            ),
            passage_quality_analysis=PassageQualityAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                passage_profiles=(
                    PassageProfile(
                        passage_id="version-1:p0",
                        ordinal_position=0,
                        word_count=6,
                        character_count=30,
                        contains_statistics=False,
                        contains_citation=False,
                    ),
                    PassageProfile(
                        passage_id="version-1:p1",
                        ordinal_position=1,
                        word_count=6,
                        character_count=34,
                        contains_statistics=False,
                        contains_citation=False,
                    ),
                ),
                passage_balance_ratio=1.0,
                keyword_stuffing_ratio=0.0,
            ),
        )
        return AssessAIReadiness().execute(report)

    def test_projects_existing_assessment_into_all_required_summaries(self):
        report = BuildAIReadinessReport().execute(self.assessment())

        self.assertEqual(report.article_identity.article_id, "article-1")
        self.assertEqual(report.article_identity.article_version_id, "version-1")
        self.assertEqual(report.structural_summary.total_word_count, 12)
        self.assertTrue(report.metadata_summary.author_available)
        self.assertEqual(len(report.passage_quality_summary.passage_profiles), 2)
        self.assertEqual(
            report.assessment_summary.metadata_completeness.value, "partial"
        )
        self.assertFalse(hasattr(report, "score"))
        self.assertFalse(hasattr(report, "recommendations"))

    def test_report_is_deterministic_and_immutable(self):
        assessment = self.assessment()
        first = BuildAIReadinessReport().execute(assessment)
        second = BuildAIReadinessReport().execute(assessment)

        self.assertEqual(first, second)
        with self.assertRaises(FrozenInstanceError):
            first.structural_summary = None
        self.assertIsInstance(first, AIReadinessReport)

    def test_report_uses_assessment_values_without_reclassification(self):
        assessment = self.assessment()

        report = BuildAIReadinessReport().execute(assessment)

        self.assertIs(
            report.assessment_summary.metadata_completeness,
            assessment.metadata_completeness,
        )


if __name__ == "__main__":n+    unittest.main()
