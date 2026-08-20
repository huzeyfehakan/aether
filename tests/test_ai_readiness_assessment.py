import sys
import unittest
from dataclasses import FrozenInstanceError

sys.path.insert(0, "src")

from aether.application.analysis.analyze_article_metadata import MetadataAnalysis  # noqa: E402
from aether.application.analysis.analyze_article_structure import (  # noqa: E402
    ArticleStructuralAnalysis,
)
from aether.application.analysis.analyze_claim_evidence import (  # noqa: E402
    ClaimEvidenceAnalysis,
)
from aether.application.analysis.analyze_passage_quality import (  # noqa: E402
    PassageProfile,
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
        structural_counts,
    ):
        metadata = MetadataAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            title_length=10,
            publication_date_available=metadata_available[2],
            last_modified_date_available=metadata_available[3],
            author_available=metadata_available[5],
            description_available=metadata_available[6],
        )
        structural = ArticleStructuralAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            total_passage_count=structural_counts[0],
            total_word_count=structural_counts[1],
            table_word_count=0,
            list_word_count=0,
            blockquote_word_count=0,
            answered_question_heading_count=0,
            unanswered_question_heading_count=0,
        )
        passage_quality = PassageQualityAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            passage_profiles=(),
            passage_balance_ratio=1.0,
            keyword_stuffing_ratio=0.0,
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
            structural_counts=(2, 10, 2),
        )

        assessment = AssessAIReadiness().execute(report)

        self.assertIs(assessment.report, report)
        self.assertEqual(
            assessment.metadata_completeness, CompletenessClassification.COMPLETE
        )
        self.assertTrue(assessment.observations.author_available)
        self.assertTrue(hasattr(assessment, "seo_score"))
        self.assertTrue(hasattr(assessment, "geo_score"))

    def test_classifies_partial_report_from_existing_raw_observations(self):
        report = self.report(
            metadata_available=(True, True, True, False, True, False, False),
            coverage_ratio=0.5,
            covered_paragraphs=1,
            structural_counts=(0, 5, 1),
        )

        assessment = AssessAIReadiness().execute(report)

        self.assertEqual(
            assessment.metadata_completeness, CompletenessClassification.PARTIAL
        )

    def test_classifies_missing_report_without_numeric_scoring(self):
        report = self.report(
            metadata_available=(False, False, False, False, False, False, False),
            coverage_ratio=0.0,
            covered_paragraphs=0,
            structural_counts=(0, 0, 0),
        )

        assessment = AssessAIReadiness().execute(report)

        self.assertEqual(
            assessment.metadata_completeness, CompletenessClassification.MISSING
        )

    def test_assessment_is_deterministic_and_immutable(self):
        report = self.report(
            metadata_available=(True, True, True, True, True, True, True),
            coverage_ratio=1.0,
            covered_paragraphs=2,
            structural_counts=(2, 10, 2),
        )

        first = AssessAIReadiness().execute(report)
        second = AssessAIReadiness().execute(report)

        self.assertEqual(first, second)
        with self.assertRaises(FrozenInstanceError):
            first.metadata_completeness = CompletenessClassification.MISSING
        self.assertIsInstance(first, AIReadinessAssessment)

    def test_entity_authority_decreases_when_claim_evidence_coverage_is_low(self):
        metadata = MetadataAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            title_length=10,
            publication_date_available=True,
            last_modified_date_available=True,
            author_available=True,
            description_available=True,
        )
        structural = ArticleStructuralAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            total_passage_count=2,
            total_word_count=100,
            table_word_count=0,
            list_word_count=0,
            blockquote_word_count=0,
            answered_question_heading_count=0,
            unanswered_question_heading_count=0,
        )
        profiles = (
            PassageProfile(
                passage_id="p1",
                ordinal_position=0,
                word_count=50,
                character_count=250,
                contains_statistics=True,
                contains_citation=True,
            ),
            PassageProfile(
                passage_id="p2",
                ordinal_position=1,
                word_count=50,
                character_count=250,
                contains_statistics=True,
                contains_citation=False,
            ),
        )
        passage_quality = PassageQualityAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            passage_profiles=profiles,
            passage_balance_ratio=1.0,
            keyword_stuffing_ratio=0.0,
        )
        claim_evidence = ClaimEvidenceAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            detectable_claim_count=2,
            supported_claim_count=0,
            claim_evidence_coverage=0.0,
        )
        report = ArticleAnalysisReport(
            structural_analysis=structural,
            metadata_analysis=metadata,
            passage_quality_analysis=passage_quality,
            claim_evidence_analysis=claim_evidence,
        )

        assessment = AssessAIReadiness().execute(report)

        # citation_score = 1 / 2 = 0.5; claim_evidence_score = 0.0
        # entity_auth = (0.5 * 0.5 + 0.0 * 0.5) * 100.0 = 25.0
        self.assertEqual(
            assessment.geo_score.entity_authority.dimension_score,
            25.0,
        )
        self.assertEqual(
            assessment.geo_score.entity_authority.weight_percentage,
            30,
        )
        self.assertEqual(
            assessment.geo_score.entity_authority.weighted_contribution,
            7.5,
        )

    def test_entity_authority_reaches_maximum_when_citations_and_claim_evidence_are_full(self):
        metadata = MetadataAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            title_length=10,
            publication_date_available=True,
            last_modified_date_available=True,
            author_available=True,
            description_available=True,
        )
        structural = ArticleStructuralAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            total_passage_count=2,
            total_word_count=100,
            table_word_count=0,
            list_word_count=0,
            blockquote_word_count=0,
            answered_question_heading_count=0,
            unanswered_question_heading_count=0,
        )
        profiles = (
            PassageProfile(
                passage_id="p1",
                ordinal_position=0,
                word_count=50,
                character_count=250,
                contains_statistics=True,
                contains_citation=True,
            ),
            PassageProfile(
                passage_id="p2",
                ordinal_position=1,
                word_count=50,
                character_count=250,
                contains_statistics=True,
                contains_citation=True,
            ),
        )
        passage_quality = PassageQualityAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            passage_profiles=profiles,
            passage_balance_ratio=1.0,
            keyword_stuffing_ratio=0.0,
        )
        claim_evidence = ClaimEvidenceAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            detectable_claim_count=2,
            supported_claim_count=2,
            claim_evidence_coverage=1.0,
        )
        report = ArticleAnalysisReport(
            structural_analysis=structural,
            metadata_analysis=metadata,
            passage_quality_analysis=passage_quality,
            claim_evidence_analysis=claim_evidence,
        )

        assessment = AssessAIReadiness().execute(report)

        # citation_score = 1.0; claim_evidence_score = 1.0
        # entity_auth = (1.0 * 0.5 + 1.0 * 0.5) * 100.0 = 100.0
        self.assertEqual(
            assessment.geo_score.entity_authority.dimension_score,
            100.0,
        )
        self.assertEqual(
            assessment.geo_score.entity_authority.weighted_contribution,
            30.0,
        )

    def test_entity_authority_preserves_citation_behavior_when_no_detectable_claims(self):
        metadata = MetadataAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            title_length=10,
            publication_date_available=True,
            last_modified_date_available=True,
            author_available=True,
            description_available=True,
        )
        structural = ArticleStructuralAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            total_passage_count=2,
            total_word_count=100,
            table_word_count=0,
            list_word_count=0,
            blockquote_word_count=0,
            answered_question_heading_count=0,
            unanswered_question_heading_count=0,
        )
        profiles = (
            PassageProfile(
                passage_id="p1",
                ordinal_position=0,
                word_count=50,
                character_count=250,
                contains_statistics=False,
                contains_citation=True,
            ),
            PassageProfile(
                passage_id="p2",
                ordinal_position=1,
                word_count=50,
                character_count=250,
                contains_statistics=False,
                contains_citation=False,
            ),
        )
        passage_quality = PassageQualityAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            passage_profiles=profiles,
            passage_balance_ratio=1.0,
            keyword_stuffing_ratio=0.0,
        )
        claim_evidence = ClaimEvidenceAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            detectable_claim_count=0,
            supported_claim_count=0,
            claim_evidence_coverage=0.0,
        )
        report = ArticleAnalysisReport(
            structural_analysis=structural,
            metadata_analysis=metadata,
            passage_quality_analysis=passage_quality,
            claim_evidence_analysis=claim_evidence,
        )

        assessment = AssessAIReadiness().execute(report)

        # citation_score = 1 / 2 = 0.5; detectable_claim_count == 0 -> entity_auth = 0.5 * 100.0 = 50.0
        self.assertEqual(
            assessment.geo_score.entity_authority.dimension_score,
            50.0,
        )
        self.assertEqual(
            assessment.geo_score.entity_authority.weighted_contribution,
            15.0,
        )


if __name__ == "__main__":
    unittest.main()
