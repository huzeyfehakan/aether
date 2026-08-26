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
from aether.application.analysis.analyze_declared_consistency import (  # noqa: E402
    DeclaredConsistencyAnalysis,
)
from aether.application.analysis.analyze_fluency import FluencyAnalysis  # noqa: E402
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

    def test_technical_access_uses_canonical_consistency_fields(self):
        base = self.report(
            metadata_available=(False, False, True, False, False, True, True),
            coverage_ratio=0.0,
            covered_paragraphs=0,
            structural_counts=(0, 0, 0),
        )
        cases = (
            (True, True, 100.0),
            (False, True, 0.0),
            (True, False, 0.0),
            (False, False, 0.0),
        )

        for titles_agree, descriptions_agree, expected in cases:
            with self.subTest(
                titles_agree=titles_agree,
                descriptions_agree=descriptions_agree,
            ):
                consistency = DeclaredConsistencyAnalysis(
                    article_id="article-1",
                    article_version_id="version-1",
                    declared_titles=(),
                    titles_agree=titles_agree,
                    declared_descriptions=(),
                    descriptions_agree=descriptions_agree,
                )
                assessment = AssessAIReadiness().execute(
                    replace(base, declared_consistency_analysis=consistency)
                )
                self.assertEqual(
                    assessment.seo_score.technical_access.dimension_score,
                    expected,
                )

    def test_technical_access_none_and_optional_weight_score_impact(self):
        base = self.report(
            metadata_available=(False, False, True, False, False, True, True),
            coverage_ratio=0.0,
            covered_paragraphs=0,
            structural_counts=(0, 0, 0),
        )
        self.assertIsNone(
            AssessAIReadiness().execute(base).seo_score.technical_access.dimension_score
        )

        def assessed_total(titles_agree):
            consistency = DeclaredConsistencyAnalysis(
                article_id="article-1",
                article_version_id="version-1",
                declared_titles=(),
                titles_agree=titles_agree,
                declared_descriptions=(),
                descriptions_agree=True,
            )
            seo = AssessAIReadiness().execute(
                replace(base, declared_consistency_analysis=consistency)
            ).seo_score
            dimensions = (
                seo.entity_coverage,
                seo.structured_data,
                seo.semantic_quality,
                seo.technical_access,
            )
            available_weight = sum(
                dimension.weight_percentage
                for dimension in dimensions
                if dimension.dimension_score is not None
            )
            expected_total = round(
                sum(dimension.weighted_contribution for dimension in dimensions)
                / (available_weight / 100.0)
            )
            self.assertEqual(seo.total, expected_total)
            return seo.total

        self.assertEqual(assessed_total(True), 85)
        self.assertEqual(assessed_total(False), 45)

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

    def test_oversized_passage_diagnostics_do_not_change_any_score(self):
        report = self.report(
            metadata_available=(True, True, True, True, True, True, True),
            coverage_ratio=1.0,
            covered_paragraphs=2,
            structural_counts=(2, 600, 2),
        )
        profiles = (
            PassageProfile(
                passage_id="p1",
                ordinal_position=0,
                word_count=100,
                character_count=500,
                contains_statistics=True,
                contains_citation=True,
            ),
            PassageProfile(
                passage_id="p2",
                ordinal_position=1,
                word_count=500,
                character_count=2500,
                contains_statistics=False,
                contains_citation=False,
            ),
        )
        base_quality = replace(
            report.passage_quality_analysis,
            passage_profiles=profiles,
            passage_balance_ratio=0.6,
        )
        baseline = AssessAIReadiness().execute(
            replace(report, passage_quality_analysis=base_quality)
        )
        instrumented = AssessAIReadiness().execute(
            replace(
                report,
                passage_quality_analysis=replace(
                    base_quality,
                    oversized_passage_rate_128=0.5,
                    oversized_passage_rate_256=0.5,
                    oversized_passage_rate_512=0.0,
                ),
            )
        )

        self.assertEqual(instrumented.seo_score, baseline.seo_score)
        self.assertEqual(instrumented.geo_score, baseline.geo_score)
        self.assertEqual(
            instrumented.geo_score.semantic_completeness,
            baseline.geo_score.semantic_completeness,
        )
        self.assertEqual(
            instrumented.geo_score.entity_authority,
            baseline.geo_score.entity_authority,
        )
        self.assertEqual(
            instrumented.geo_score.structural_richness,
            baseline.geo_score.structural_richness,
        )
        self.assertEqual(
            instrumented.geo_score.discoverability,
            baseline.geo_score.discoverability,
        )

    def test_passage_balance_is_invariant_for_semantic_completeness_and_geo(self):
        report = self.report(
            metadata_available=(True, True, True, True, True, True, True),
            coverage_ratio=0.5,
            covered_paragraphs=1,
            structural_counts=(2, 80, 1),
        )
        report = replace(
            report,
            structural_analysis=replace(
                report.structural_analysis,
                heading_passage_overlap_ratio=0.5,
            ),
            passage_quality_analysis=replace(
                report.passage_quality_analysis,
                passage_profiles=(
                    PassageProfile("p1", 0, 40, 200, True, False),
                    PassageProfile("p2", 1, 40, 200, False, False),
                ),
            ),
        )

        results = []
        for ratio in (0.0, 0.25, 0.5, 0.75, 1.0):
            with self.subTest(passage_balance_ratio=ratio):
                assessment = AssessAIReadiness().execute(
                    replace(
                        report,
                        passage_quality_analysis=replace(
                            report.passage_quality_analysis,
                            passage_balance_ratio=ratio,
                        ),
                    )
                )
                results.append(
                    (
                        assessment.geo_score.semantic_completeness.dimension_score,
                        assessment.geo_score.total,
                    )
                )

        self.assertEqual(len(set(results)), 1)

    def test_semantic_completeness_renormalizes_unmeasured_optional_signals(self):
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
            total_passage_count=1,
            total_word_count=20,
            table_word_count=0,
            list_word_count=0,
            blockquote_word_count=0,
            answered_question_heading_count=0,
            unanswered_question_heading_count=0,
            heading_passage_overlap_ratio=None,
            direct_answer_coverage_ratio=0.0,
        )
        passage_quality = PassageQualityAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            passage_profiles=(
                PassageProfile(
                    passage_id="p1",
                    ordinal_position=0,
                    word_count=20,
                    character_count=100,
                    contains_statistics=True,
                    contains_citation=False,
                ),
            ),
            passage_balance_ratio=1.0,
            keyword_stuffing_ratio=0.0,
        )
        report = ArticleAnalysisReport(
            structural_analysis=structural,
            metadata_analysis=metadata,
            passage_quality_analysis=passage_quality,
        )

        semantic_scores = []
        geo_totals = []
        for direct_answer_ratio in (None, 0.0, 0.5, 1.0):
            with self.subTest(direct_answer_ratio=direct_answer_ratio):
                assessment = AssessAIReadiness().execute(
                    replace(
                        report,
                        structural_analysis=replace(
                            structural,
                            direct_answer_coverage_ratio=direct_answer_ratio,
                        ),
                    )
                )
                self.assertEqual(
                    assessment.geo_score.semantic_completeness.dimension_score,
                    100.0,
                )
                semantic_scores.append(
                    assessment.geo_score.semantic_completeness.dimension_score
                )
                geo_totals.append(assessment.geo_score.total)
        self.assertEqual(len(set(semantic_scores)), 1)
        self.assertEqual(len(set(geo_totals)), 1)

    def test_semantic_completeness_uses_only_remaining_base_content_weights(self):
        report = self.report(
            metadata_available=(True, True, True, True, True, True, True),
            coverage_ratio=1.0,
            covered_paragraphs=1,
            structural_counts=(1, 20, 1),
        )
        profile = PassageProfile(
            passage_id="p1",
            ordinal_position=0,
            word_count=20,
            character_count=100,
            contains_statistics=True,
            contains_citation=False,
        )
        report = replace(
            report,
            structural_analysis=replace(
                report.structural_analysis,
                heading_passage_overlap_ratio=0.0,
                direct_answer_coverage_ratio=1.0,
            ),
            passage_quality_analysis=replace(
                report.passage_quality_analysis,
                passage_profiles=(profile,),
            ),
        )

        assessment = AssessAIReadiness().execute(report)

        self.assertAlmostEqual(
            assessment.geo_score.semantic_completeness.dimension_score,
            (100.0 * 0.4 + 0.0 * 0.3) / (0.4 + 0.3),
        )

    def test_semantic_completeness_still_reacts_to_each_remaining_input(self):
        report = self.report(
            metadata_available=(True, True, True, True, True, True, True),
            coverage_ratio=0.5,
            covered_paragraphs=1,
            structural_counts=(2, 40, 1),
        )
        profiles = (
            PassageProfile("p1", 0, 20, 100, True, False),
            PassageProfile("p2", 1, 20, 100, False, False),
        )
        fluency = FluencyAnalysis(
            article_id="article-1",
            article_version_id="version-1",
            sentence_count=2,
            average_sentence_word_count=10.0,
            sentence_length_variation=1.0,
            sentence_balance_ratio=0.5,
            structural_variety_ratio=0.5,
        )
        report = replace(
            report,
            structural_analysis=replace(
                report.structural_analysis,
                heading_passage_overlap_ratio=0.5,
            ),
            passage_quality_analysis=replace(
                report.passage_quality_analysis,
                passage_profiles=profiles,
            ),
            fluency_analysis=fluency,
        )
        baseline = AssessAIReadiness().execute(report).geo_score.semantic_completeness
        statistics_changed = AssessAIReadiness().execute(
            replace(
                report,
                passage_quality_analysis=replace(
                    report.passage_quality_analysis,
                    passage_profiles=(profiles[0], replace(profiles[1], contains_statistics=True)),
                ),
            )
        ).geo_score.semantic_completeness
        overlap_changed = AssessAIReadiness().execute(
            replace(
                report,
                structural_analysis=replace(
                    report.structural_analysis,
                    heading_passage_overlap_ratio=1.0,
                ),
            )
        ).geo_score.semantic_completeness
        fluency_changed = AssessAIReadiness().execute(
            replace(
                report,
                fluency_analysis=replace(
                    fluency,
                    sentence_balance_ratio=1.0,
                    structural_variety_ratio=1.0,
                ),
            )
        ).geo_score.semantic_completeness

        self.assertNotEqual(statistics_changed, baseline)
        self.assertNotEqual(overlap_changed, baseline)
        self.assertNotEqual(fluency_changed, baseline)

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
