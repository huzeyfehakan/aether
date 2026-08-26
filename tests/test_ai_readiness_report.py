import sys
import unittest
from dataclasses import FrozenInstanceError, replace

sys.path.insert(0, "src")

from aether.application.analysis.analyze_article_metadata import MetadataAnalysis  # noqa: E402
from aether.application.analysis.analyze_article_structure import (  # noqa: E402
    ArticleStructuralAnalysis,
)
from aether.application.analysis.analyze_claim_evidence import (  # noqa: E402
    ClaimEvidenceAnalysis,
)
from aether.application.analysis.analyze_content_duplication import (  # noqa: E402
    ContentDuplicationAnalysis,
    RepeatedPassage,
)
from aether.application.analysis.analyze_declared_consistency import (  # noqa: E402
    DeclaredConsistencyAnalysis,
)
from aether.application.analysis.analyze_internal_links import (  # noqa: E402
    InternalLinkAnalysisResult,
)
from aether.application.analysis.analyze_fluency import FluencyAnalysis  # noqa: E402
from aether.application.analysis.analyze_passage_quality import (  # noqa: E402
    PassageProfile,
    PassageQualityAnalysis,
)
from aether.application.analysis.analyze_structured_data import (  # noqa: E402
    StructuredDataAnalysis,
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

    def assessment_with_entity_authority_signals(self, detectable_claim_count=2):
        base_report = self.assessment().report
        profiles = tuple(
            replace(
                profile,
                contains_citation=index == 0,
                contains_statistics=index == 0,
            )
            for index, profile in enumerate(
                base_report.passage_quality_analysis.passage_profiles
            )
        )
        analysis_report = replace(
            base_report,
            structural_analysis=replace(
                base_report.structural_analysis,
                total_word_count=100,
                table_word_count=10,
                list_word_count=5,
                blockquote_word_count=5,
                answered_question_heading_count=3,
                unanswered_question_heading_count=1,
                heading_passage_overlap_ratio=0.4,
                direct_answer_coverage_ratio=0.6,
                unsupported_entity_ratio=0.24,
            ),
            passage_quality_analysis=replace(
                base_report.passage_quality_analysis,
                passage_profiles=profiles,
            ),
            structured_data_analysis=StructuredDataAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                article_node_present=True,
                declared_node_types=("Article",),
                declared_article_properties=("author",),
                all_declared_properties=("author",),
                missing_article_properties=(),
            ),
            internal_link_analysis=InternalLinkAnalysisResult(
                article_id="article-1",
                article_version_id="version-1",
                outgoing_link_count=2,
                unique_target_count=2,
                body_link_count=2,
                incoming_link_count=0,
                potential_orphan=True,
                outbound_body_domains=("example.org",),
                third_party_ratio=0.82,
                trust_index=0.71,
            ),
            claim_evidence_analysis=ClaimEvidenceAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                detectable_claim_count=detectable_claim_count,
                supported_claim_count=1 if detectable_claim_count else 0,
                claim_evidence_coverage=0.5 if detectable_claim_count else 0.0,
            ),
            fluency_analysis=FluencyAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                sentence_count=4,
                average_sentence_word_count=12.0,
                sentence_length_variation=2.0,
                sentence_balance_ratio=0.8,
                structural_variety_ratio=1.2,
            ),
        )
        return AssessAIReadiness().execute(analysis_report)

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

    def test_seo_details_project_only_existing_formula_inputs(self):
        assessment = self.assessment()
        analysis = replace(
            assessment.report,
            structured_data_analysis=StructuredDataAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                article_node_present=True,
                declared_node_types=("Article",),
                declared_article_properties=("author", "headline"),
                all_declared_properties=("author", "headline"),
                missing_article_properties=("description",),
            ),
            content_duplication_analysis=ContentDuplicationAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                compared_article_count=1,
                total_passage_count=2,
                repeated_passages=(
                    RepeatedPassage("p-1", 1, "Repeated", 1, 1),
                ),
            ),
            declared_consistency_analysis=DeclaredConsistencyAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                declared_titles=(),
                titles_agree=False,
                declared_descriptions=(),
                descriptions_agree=False,
            ),
        )
        assessment = AssessAIReadiness().execute(analysis)
        scores_before = (assessment.seo_score, assessment.geo_score)

        report = BuildAIReadinessReport().execute(assessment)
        seo = report.assessment_summary.seo_score
        entity = {signal.label: signal.value for signal in seo.entity_coverage_detail.signals}
        structured = {signal.label: signal.value for signal in seo.structured_data_detail.signals}
        semantic = {signal.label: signal.value for signal in seo.semantic_quality_detail.signals}
        technical = {signal.label: signal.value for signal in seo.technical_access_detail.signals}

        self.assertEqual(entity, {
            "Publication date": "Available",
            "Last modified date": "Missing",
            "Author": "Available",
            "Description": "Available",
        })
        self.assertEqual(structured["Article structured data"], "Present")
        self.assertEqual(structured["Declared expected properties"], "author, headline")
        self.assertEqual(structured["Missing expected properties"], "description")
        self.assertAlmostEqual(structured["Property coverage"], 200 / 3)
        self.assertEqual(semantic, {
            "Total passages": 2.0,
            "Unique passages": 1.0,
            "Repeated passages": 1.0,
            "Unique passage ratio": 50.0,
        })
        self.assertEqual(technical, {
            "Title sources disagree": "Yes",
            "Description sources disagree": "Yes",
        })
        self.assertEqual(seo.technical_access.dimension_score, 0.0)
        self.assertEqual((assessment.seo_score, assessment.geo_score), scores_before)

    def test_unavailable_seo_analyses_preserve_not_measured_values(self):
        seo = BuildAIReadinessReport().execute(self.assessment()).assessment_summary.seo_score

        for detail in (
            seo.structured_data_detail,
            seo.semantic_quality_detail,
            seo.technical_access_detail,
        ):
            self.assertTrue(all(signal.value is None for signal in detail.signals))

    def test_projects_passage_extractability_as_a_separate_diagnostic(self):
        assessment = self.assessment()
        assessment = replace(
            assessment,
            report=replace(
                assessment.report,
                passage_quality_analysis=replace(
                    assessment.report.passage_quality_analysis,
                    oversized_passage_rate_128=0.5,
                    oversized_passage_rate_256=0.25,
                    oversized_passage_rate_512=0.0,
                ),
            ),
        )

        report = BuildAIReadinessReport().execute(assessment)
        diagnostic = report.passage_quality_summary

        self.assertEqual(diagnostic.passage_count, 2)
        self.assertEqual(diagnostic.oversized_passage_rate_128, 0.5)
        self.assertEqual(diagnostic.oversized_passage_rate_256, 0.25)
        self.assertEqual(diagnostic.oversized_passage_rate_512, 0.0)
        self.assertFalse(
            hasattr(report.assessment_summary.geo_score, "passage_extractability")
        )

    def test_projects_passage_balance_as_a_separate_unscored_diagnostic(self):
        assessment = self.assessment()
        assessment = replace(
            assessment,
            report=replace(
                assessment.report,
                passage_quality_analysis=replace(
                    assessment.report.passage_quality_analysis,
                    passage_balance_ratio=0.25,
                ),
            ),
        )

        report = BuildAIReadinessReport().execute(assessment)

        self.assertEqual(report.passage_balance_diagnostic.ratio, 0.25)
        self.assertFalse(report.passage_balance_diagnostic.included_in_score)
        self.assertFalse(
            hasattr(report.assessment_summary.geo_score, "passage_balance")
        )

    def test_entity_authority_detail_projects_existing_measured_signals(self):
        report = BuildAIReadinessReport().execute(
            self.assessment_with_entity_authority_signals()
        )
        detail = report.assessment_summary.geo_score.entity_authority_detail
        signals = {signal.label: signal.value for signal in detail.signals}

        self.assertEqual(
            detail.dimension_score,
            report.assessment_summary.geo_score.entity_authority.dimension_score,
        )
        self.assertEqual(signals["Author declaration"], 100.0)
        self.assertEqual(signals["Outbound body sources"], 100.0)
        self.assertEqual(signals["Trust index"], 71.0)
        self.assertEqual(signals["Third-party source ratio"], 82.0)
        self.assertEqual(signals["Supported entities"], 76.0)
        self.assertEqual(signals["Citation coverage"], 50.0)
        self.assertEqual(signals["Claim evidence coverage"], 50.0)

    def test_claim_evidence_detail_is_unmeasured_without_detectable_claims(self):
        report = BuildAIReadinessReport().execute(
            self.assessment_with_entity_authority_signals(
                detectable_claim_count=0
            )
        )
        signals = {
            signal.label: signal.value
            for signal in report.assessment_summary.geo_score.entity_authority_detail.signals
        }

        self.assertIsNone(signals["Claim evidence coverage"])

    def test_semantic_completeness_detail_uses_existing_formula_signals(self):
        report = BuildAIReadinessReport().execute(
            self.assessment_with_entity_authority_signals()
        )
        detail = report.assessment_summary.geo_score.semantic_completeness_detail
        signals = {signal.label: signal.value for signal in detail.signals}

        self.assertEqual(signals["Statistics coverage"], 50.0)
        self.assertEqual(signals["Heading-passage overlap"], 40.0)
        self.assertNotIn("Direct answer coverage", signals)
        self.assertNotIn("Passage balance", signals)
        self.assertEqual(signals["Sentence balance"], 80.0)
        self.assertEqual(signals["Structural variety"], 100.0)

    def test_semantic_completeness_detail_preserves_unmeasured_optional_signals(self):
        assessment = self.assessment_with_entity_authority_signals()
        assessment = replace(
            assessment,
            report=replace(
                assessment.report,
                structural_analysis=replace(
                    assessment.report.structural_analysis,
                    heading_passage_overlap_ratio=None,
                ),
            ),
        )
        report = BuildAIReadinessReport().execute(assessment)
        signals = {
            signal.label: signal.value
            for signal in report.assessment_summary.geo_score.semantic_completeness_detail.signals
        }

        self.assertIsNone(signals["Heading-passage overlap"])

    def test_direct_answer_coverage_is_a_separate_unscored_diagnostic(self):
        measured = BuildAIReadinessReport().execute(
            self.assessment_with_entity_authority_signals()
        )
        self.assertEqual(measured.direct_answer_coverage_diagnostic.ratio, 0.6)
        self.assertFalse(
            measured.direct_answer_coverage_diagnostic.included_in_score
        )
        self.assertNotIn(
            "Direct answer coverage",
            {
                signal.label
                for signal in measured.assessment_summary.geo_score.semantic_completeness_detail.signals
            },
        )

        assessment = self.assessment_with_entity_authority_signals()
        unmeasured = BuildAIReadinessReport().execute(
            replace(
                assessment,
                report=replace(
                    assessment.report,
                    structural_analysis=replace(
                        assessment.report.structural_analysis,
                        direct_answer_coverage_ratio=None,
                    ),
                ),
            )
        )
        self.assertIsNone(unmeasured.direct_answer_coverage_diagnostic.ratio)

    def test_structural_richness_detail_breaks_out_existing_word_components(self):
        report = BuildAIReadinessReport().execute(
            self.assessment_with_entity_authority_signals()
        )
        signals = {
            signal.label: signal.value
            for signal in report.assessment_summary.geo_score.structural_richness_detail.signals
        }

        self.assertAlmostEqual(signals["Table word share"], 10 / 120 * 100.0)
        self.assertAlmostEqual(signals["List word share"], 5 / 120 * 100.0)
        self.assertAlmostEqual(signals["Blockquote word share"], 5 / 120 * 100.0)
        self.assertAlmostEqual(signals["Structured content ratio"], 20 / 120 * 100.0)
        self.assertEqual(signals["Answered question ratio"], 75.0)

    def test_discoverability_detail_exposes_link_counts_and_used_ratio(self):
        report = BuildAIReadinessReport().execute(
            self.assessment_with_entity_authority_signals()
        )
        signals = {
            signal.label: signal.value
            for signal in report.assessment_summary.geo_score.discoverability_detail.signals
        }

        self.assertEqual(signals["Body links"], 2.0)
        self.assertEqual(signals["Outgoing links"], 2.0)
        self.assertEqual(signals["Body link density"], 1.0) # 2 links / 2 passages
        self.assertEqual(signals["Unique targets"], 2.0)


if __name__ == "__main__":n+    unittest.main()
