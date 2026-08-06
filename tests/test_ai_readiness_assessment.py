import sys
import unittest
from dataclasses import FrozenInstanceError

sys.path.insert(0, "src")

from aether.application.analysis.analyze_article_metadata import MetadataAnalysis  # noqa: E402
from aether.application.analysis.analyze_article_structure import (  # noqa: E402
    ArticleStructuralAnalysis,
)
from aether.application.analysis.analyze_passage_quality import (  # noqa: E402
    PassageQualityAnalysis,
)
from aether.application.analysis.assess_ai_readiness import (  # noqa: E402
    AIReadinessAssessment,
    AssessAIReadiness,
    CompletenessClassification,
)
from aether.application.analysis.build_article_analysis_report import (  # noqa: E402
    ArticleAnalysisReport,
)


class AIReadinessAssessmentTests(unittest.TestCase):
    def report(
        self,
        *,
        metadata_available,
        coverage_ratio,
        covered_paragraphs,
        ordinals_contiguous,
        structural_counts,
    ):
        metadata = MetadataAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            title_available=metadata_available[0],
            title_length=10,
            canonical_url_available=metadata_available[1],
            publication_date_available=metadata_available[2],
            last_modified_date_available=metadata_available[3],
            language_available=metadata_available[4],
            author_available=metadata_available[5],
            description_available=metadata_available[6],
        )
        structural = ArticleStructuralAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            total_passage_count=structural_counts[0],
            total_word_count=structural_counts[1],
            average_passage_length=0.0,
            heading_count=None,
            paragraph_count=structural_counts[2],
            publication_date_available=metadata_available[2],
            canonical_url_available=metadata_available[1],
            language_available=metadata_available[4],
        )
        passage_quality = PassageQualityAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            passage_profiles=(),
            minimum_passage_word_count=None,
            maximum_passage_word_count=None,
            median_passage_word_count=None,
            source_paragraph_count=2,
            covered_source_paragraph_count=covered_paragraphs,
            source_paragraph_coverage_ratio=coverage_ratio,
            passage_ordinals_are_contiguous=ordinals_contiguous,
        )
        return ArticleAnalysisReport(
            structural_analysis=structural,
            metadata_analysis=metadata,
            passage_quality_analysis=passage_quality,
        )

    def test_classifies_complete_report_and_preserves_raw_observations(self):
        report = self.report(
            metadata_available=(True, True, True, True, True, True, True),
            coverage_ratio=1.0,
            covered_paragraphs=2,
            ordinals_contiguous=True,
            structural_counts=(2, 10, 2),
        )

        assessment = AssessAIReadiness().execute(report)

        self.assertIs(assessment.report, report)
        self.assertEqual(
            assessment.metadata_completeness, CompletenessClassification.COMPLETE
        )
        self.assertEqual(
            assessment.passage_coverage, CompletenessClassification.COMPLETE
        )
        self.assertEqual(
            assessment.structural_completeness, CompletenessClassification.COMPLETE
        )
        self.assertTrue(assessment.observations.author_available)
        self.assertEqual(assessment.observations.source_paragraph_coverage_ratio, 1.0)
        self.assertEqual(assessment.observations.total_word_count, 10)
        self.assertFalse(hasattr(assessment, "score"))

    def test_classifies_partial_report_from_existing_raw_observations(self):
        report = self.report(
            metadata_available=(True, True, True, False, True, False, False),
            coverage_ratio=0.5,
            covered_paragraphs=1,
            ordinals_contiguous=False,
            structural_counts=(0, 5, 1),
        )

        assessment = AssessAIReadiness().execute(report)

        self.assertEqual(
            assessment.metadata_completeness, CompletenessClassification.PARTIAL
        )
        self.assertEqual(
            assessment.passage_coverage, CompletenessClassification.PARTIAL
        )
        self.assertEqual(
            assessment.structural_completeness, CompletenessClassification.PARTIAL
        )

    def test_classifies_missing_report_without_numeric_scoring(self):
        report = self.report(
            metadata_available=(False, False, False, False, False, False, False),
            coverage_ratio=0.0,
            covered_paragraphs=0,
            ordinals_contiguous=False,
            structural_counts=(0, 0, 0),
        )

        assessment = AssessAIReadiness().execute(report)

        self.assertEqual(
            assessment.metadata_completeness, CompletenessClassification.MISSING
        )
        self.assertEqual(
            assessment.passage_coverage, CompletenessClassification.MISSING
        )
        self.assertEqual(
            assessment.structural_completeness, CompletenessClassification.MISSING
        )

    def test_assessment_is_deterministic_and_immutable(self):
        report = self.report(
            metadata_available=(True, True, True, True, True, True, True),
            coverage_ratio=1.0,
            covered_paragraphs=2,
            ordinals_contiguous=True,
            structural_counts=(2, 10, 2),
        )

        first = AssessAIReadiness().execute(report)
        second = AssessAIReadiness().execute(report)

        self.assertEqual(first, second)
        with self.assertRaises(FrozenInstanceError):
            first.metadata_completeness = CompletenessClassification.MISSING
        self.assertIsInstance(first, AIReadinessAssessment)


if __name__ == "__main__":
    unittest.main()
