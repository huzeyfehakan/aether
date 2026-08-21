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
            unsupported_entity_ratio=0.0,
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

    def entity_authority_report(self):
        from aether.application.analysis.analyze_internal_links import InternalLinkAnalysisResult
        from aether.application.analysis.analyze_structured_data import StructuredDataAnalysis
        from dataclasses import replace

        report = self.report(
            metadata_available=(True, True, True, True, True, True, True),
            coverage_ratio=1.0,
            covered_paragraphs=2,
            structural_counts=(2, 10, 2),
        )

        # Override with our specific test data
        return replace(report,
            structured_data_analysis=StructuredDataAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                article_node_present=True,
                declared_node_types=("Article", "Person", "Organization"),
                declared_article_properties=("author", "publisher"),
                all_declared_properties=("author", "publisher"),
                missing_article_properties=("datePublished",)
            ),
            internal_link_analysis=InternalLinkAnalysisResult(
                article_id="article-1",
                article_version_id="version-1",
                outgoing_link_count=5,
                unique_target_count=5,
                body_link_count=0,
                incoming_link_count=1,
                potential_orphan=False,
                outbound_body_domains=(),
                third_party_ratio=None,
                trust_index=None,
            )
        )

    def test_geo_entity_authority_scores_correctly_with_body_vs_non_body_links(self):
        report = self.entity_authority_report()
        assessment = AssessAIReadiness().execute(report)

        # Yazar beyan edilmis (100), govde hicbir yere atif yapmiyor (0),
        # varliklar kanitlanmis (100). trust_index ve third_party_ratio bos
        # kume uzerinde oran oldugu icin ortalamaya hic girmiyor.
        self.assertAlmostEqual(
            assessment.geo_score.entity_authority.dimension_score, 200 / 3, places=6
        )

    def test_body_citations_raise_entity_authority_above_an_article_with_none(self):
        from dataclasses import replace
        """Ayni makale, tek fark govdedeki dis atiflar."""
        cited = replace(
            self.entity_authority_report(),
            internal_link_analysis=replace(
                self.entity_authority_report().internal_link_analysis,
                outbound_body_domains=("wikipedia.org", "reuters.com"),
                trust_index=(3 + 2) / (2 * 3),
                third_party_ratio=1.0,
            ),
        )

        scored = AssessAIReadiness().execute(cited)

        # (100 yazar + 100 atif var + 83.33 guven + 100 bagimsizlik + 100 kanit) / 5
        self.assertAlmostEqual(
            scored.geo_score.entity_authority.dimension_score, 483.3333333 / 5.0, places=4
        )

    def test_an_unmeasurable_entity_authority_leaves_its_weight_out_of_the_total(self):
        from dataclasses import replace
        """Taslak: yapisal veri ve link analizi hic komposize edilmemis."""
        report = replace(
            self.entity_authority_report(),
            structured_data_analysis=None,
            internal_link_analysis=None,
            structural_analysis=replace(
                self.entity_authority_report().structural_analysis,
                unsupported_entity_ratio=None
            )
        )

        geo = AssessAIReadiness().execute(report).geo_score

        self.assertIsNone(geo.entity_authority.dimension_score)
        # 30 puanlik agirlik toplamdan dusuyor, sifir olarak sayilmiyor.
        self.assertEqual(geo.entity_authority.weighted_contribution, 0.0)

if __name__ == "__main__":
    unittest.main()
