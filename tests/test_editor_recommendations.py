import sys
import unittest
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
from aether.application.analysis.analyze_content_duplication import (  # noqa: E402
    AnalyzeContentDuplication,
)
from aether.application.analysis.analyze_passage_quality import (  # noqa: E402
    AnalyzePassageQuality,
)
from aether.application.analysis.assess_ai_readiness import AssessAIReadiness  # noqa: E402
from aether.application.analysis.build_ai_readiness_report import (  # noqa: E402
    BuildAIReadinessReport,
)
from aether.application.analysis.build_article_analysis_report import (  # noqa: E402
    BuildArticleAnalysisReport,
)
from aether.application.analysis.derive_editor_recommendations import (  # noqa: E402
    RecommendationCategory,
    RecommendationCode,
)
from aether.application.ingestion.register_raw_html_article import (  # noqa: E402
    RawHtmlArticle,
    RegisterRawHtmlArticle,
)
from aether.presentation.ai_readiness_report_renderers import (  # noqa: E402
    PlainTextAIReadinessReportRenderer,
)
from aether.presentation.editor_recommendation_text import (  # noqa: E402
    compared_articles_phrase,
    recommendation_text,
)


OBSERVED_AT = datetime(2026, 8, 6, 9, 0, tzinfo=timezone.utc)
NOTICE = "Bu içerik bilgilendirme amaçlı hazırlanmıştır."


class EditorRecommendationTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryContentRepository()
        self.register = RegisterRawHtmlArticle(self.repository)

    def build(self, with_duplication=True, is_draft=False):
        return BuildArticleAnalysisReport(
            AnalyzeArticleStructure(self.repository),
            AnalyzeArticleMetadata(self.repository),
            AnalyzePassageQuality(self.repository),
            AnalyzeContentDuplication(self.repository) if with_duplication else None,
            is_draft=is_draft,
        )

    def ingest(self, slug, paragraphs):
        body = "".join(f"<p>{text}</p>" for text in paragraphs)
        return self.register.execute(
            RawHtmlArticle(
                html=f'<html lang="tr"><head><title>{slug}</title></head>'
                f"<body><main>{body}</main></body></html>",
                source_url=f"https://ebeveynakademisi.trtcocuk.net.tr/makale/{slug}",
                publisher="TRT Çocuk Ebeveyn Akademisi",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )

    @staticmethod
    def of_code(report, code):
        return [r for r in report.editor_recommendations if r.code is code]

    def report_for(self, registration, with_duplication=True, is_draft=False):
        analysis = self.build(with_duplication, is_draft).execute(
            registration.article, registration.article_version.article_version_id
        )
        return BuildAIReadinessReport().execute(AssessAIReadiness().execute(analysis))

    @staticmethod
    def words(count):
        return " ".join("word" for _ in range(count))

    def test_recommends_the_metadata_an_editor_can_supply(self):
        """Absence was measured and displayed, but never turned into advice."""
        first = self.ingest("eksik", ["Özgün paragraf."])

        report = self.report_for(first)
        codes = {r.code for r in report.editor_recommendations}

        for code in (
            RecommendationCode.MISSING_PUBLICATION_DATE,
            RecommendationCode.MISSING_AUTHOR,
        ):
            self.assertIn(code, codes)
            self.assertEqual(
                self.of_code(report, code)[0].category, RecommendationCategory.EDITOR
            )

    def test_a_last_modified_date_is_addressed_to_the_technical_audience(self):
        """A CMS stamps this on save; an editor has no field for it."""
        first = self.ingest("eksik-tarih", ["Özgün paragraf."])

        report = self.report_for(first)

        recommendation = self.of_code(
            report, RecommendationCode.MISSING_LAST_MODIFIED_DATE
        )[0]
        self.assertEqual(recommendation.category, RecommendationCategory.TECHNICAL)

    def test_every_metadata_recommendation_names_a_concrete_action(self):
        """Naming the gap is not advice; the editor must know what to do."""
        first = self.ingest("eylem", ["Özgün paragraf."])
        report = self.report_for(first)

        for code in (
            RecommendationCode.MISSING_PUBLICATION_DATE,
            RecommendationCode.MISSING_AUTHOR,
        ):
            with self.subTest(code=code):
                text = recommendation_text(self.of_code(report, code)[0])
                self.assertIn("cms", text.what_to_do.lower())
                self.assertGreater(len(text.why_it_matters.split()), 20)
                self.assertNotEqual(text.headline, text.what_to_do)

    def test_makes_no_metadata_recommendation_when_the_field_is_present(self):
        html = (
            '<html lang="tr"><head><title>Başlık</title>'
            '<meta name="author" content="Ayşe Yılmaz" />'
            '<meta name="description" content="Bir özet." />'
            '<meta property="article:published_time" content="2026-08-03T10:00:00+03:00" />'
            '<meta property="article:modified_time" content="2026-08-04T10:00:00+03:00" />'
            "</head><body><main><p>Özgün paragraf.</p></main></body></html>"
        )
        registration = self.register.execute(
            RawHtmlArticle(
                html=html,
                source_url="https://ebeveynakademisi.trtcocuk.net.tr/makale/tam",
                publisher="TRT Çocuk Ebeveyn Akademisi",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )

        report = self.report_for(registration)
        codes = {r.code for r in report.editor_recommendations}

        for code in (
            RecommendationCode.MISSING_PUBLICATION_DATE,
            RecommendationCode.MISSING_AUTHOR,
            RecommendationCode.MISSING_SUMMARY,
            RecommendationCode.MISSING_LAST_MODIFIED_DATE,
        ):
            self.assertNotIn(code, codes)

    def test_recommends_an_opening_shorter_than_twenty_one_words_for_a_long_article(self):
        article = self.ingest("short-opening", [self.words(10), self.words(190)])

        report = self.report_for(article)

        self.assertEqual(
            len(self.of_code(report, RecommendationCode.WEAK_ARTICLE_OPENING)), 1
        )

    def test_does_not_recommend_a_long_article_with_an_opening_over_twenty_words(self):
        article = self.ingest("long-opening", [self.words(35), self.words(165)])

        report = self.report_for(article)

        self.assertEqual(
            self.of_code(report, RecommendationCode.WEAK_ARTICLE_OPENING), []
        )

    def test_does_not_recommend_a_short_article_with_a_short_opening(self):
        article = self.ingest("short-article", [self.words(10), self.words(90)])

        report = self.report_for(article)

        self.assertEqual(
            self.of_code(report, RecommendationCode.WEAK_ARTICLE_OPENING), []
        )

    def test_recommends_a_weak_opening_for_a_draft(self):
        article = self.ingest("draft-short-opening", [self.words(10), self.words(190)])

        report = self.report_for(article, is_draft=True)

        self.assertEqual(
            len(self.of_code(report, RecommendationCode.WEAK_ARTICLE_OPENING)), 1
        )

    def test_repeated_text_is_addressed_to_the_editor(self):
        """The editor owns the article body and is the person who sees it."""
        first = self.ingest("birinci", ["Özgün paragraf.", NOTICE])
        self.ingest("ikinci", ["Başka özgün paragraf.", NOTICE])

        report = self.report_for(first)

        repeated = self.of_code(
            report, RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY
        )
        self.assertEqual(len(repeated), 1)
        recommendation = repeated[0]
        self.assertEqual(
            recommendation.category, RecommendationCategory.EDITOR
        )
        self.assertEqual(recommendation.excerpt, NOTICE)
        self.assertEqual(report.content_reuse_summary.compared_article_count, 1)

    def test_makes_no_recommendation_when_nothing_is_repeated(self):
        first = self.ingest("birinci", ["Özgün paragraf."])
        self.ingest("ikinci", ["Tamamen farklı paragraf."])

        report = self.report_for(first)

        self.assertEqual(
            self.of_code(report, RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY), []
        )
        self.assertEqual(report.content_reuse_summary.compared_article_count, 1)

    def test_report_omits_reuse_entirely_when_the_capability_is_not_used(self):
        first = self.ingest("birinci", ["Özgün paragraf.", NOTICE])
        self.ingest("ikinci", ["Başka paragraf.", NOTICE])

        report = self.report_for(first, with_duplication=False)

        self.assertIsNone(report.content_reuse_summary)
        self.assertEqual(
            self.of_code(report, RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY), []
        )

    def test_states_how_many_articles_were_compared(self):
        for count, expected in (
            (0, "No previously analyzed articles from this publisher"),
            (1, "previously analyzed articles from this publisher (1 article)"),
            (4, "previously analyzed articles from this publisher (4 articles)"),
        ):
            with self.subTest(count=count):
                self.assertIn(expected, compared_articles_phrase(count))

    def test_rendered_report_files_repetition_under_editor_recommendations(self):
        first = self.ingest("birinci", ["Özgün paragraf.", NOTICE])
        self.ingest("ikinci", ["Başka özgün paragraf.", NOTICE])

        rendered = PlainTextAIReadinessReportRenderer().render(self.report_for(first))

        self.assertIn("Editor Recommendations", rendered)
        self.assertIn("Things you can change in this article now.", rendered)
        self.assertIn(
            "Compared against previously analyzed articles from this publisher "
            "(1 article).",
            rendered,
        )
        self.assertIn("What to do:", rendered)

    def test_repeated_paragraphs_share_one_explanation(self):
        """Repeating the rationale per occurrence buries the occurrences."""
        second_notice = "Yazan: Prof. Dr. Funda Gümüştaş"
        first = self.ingest("birinci", ["Özgün paragraf.", NOTICE, second_notice])
        self.ingest("ikinci", ["Başka özgün paragraf.", NOTICE, second_notice])

        report = self.report_for(first)
        rendered = PlainTextAIReadinessReportRenderer().render(report)

        self.assertEqual(
            len(self.of_code(report, RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY)), 2
        )
        self.assertEqual(rendered.count("Why it matters: Repeated text"), 1)
        self.assertEqual(
            rendered.count("This paragraph also appears in your other articles"), 1
        )
        self.assertIn(NOTICE, rendered)
        self.assertIn(second_notice, rendered)

    def test_content_quality_wording_makes_no_claim_about_ai_systems(self):
        """Repetition is a fact about the text, not evidence of model behaviour."""
        first = self.ingest("birinci", ["Özgün paragraf.", NOTICE])
        self.ingest("ikinci", ["Başka özgün paragraf.", NOTICE])
        report = self.report_for(first)

        text = recommendation_text(
            self.of_code(report, RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY)[0]
        )
        wording = " ".join((text.headline, text.why_it_matters, text.what_to_do)).lower()

        for claim in ("retrieval", "ignored", "rank"):
            self.assertNotIn(claim, wording)
        for jargon in ("passage", "corpus", "fingerprint"):
            self.assertNotIn(jargon, wording)


if __name__ == "__main__":
    unittest.main()
