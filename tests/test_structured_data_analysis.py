import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "src")

from aether.adapters.outbound.in_memory_content_repository import (  # noqa: E402
    InMemoryContentRepository,
)
from aether.application.analysis.analyze_structured_data import (  # noqa: E402
    AnalyzeStructuredData,
)
from aether.application.ingestion.register_raw_html_article import (  # noqa: E402
    RawHtmlArticle,
    RegisterRawHtmlArticle,
)
from aether.domain.common import DomainValidationError  # noqa: E402
from aether.presentation.editor_recommendation_text import (  # noqa: E402
    missing_properties_phrase,
)


OBSERVED_AT = datetime(2026, 8, 6, 9, 0, tzinfo=timezone.utc)
FIXTURES = Path(__file__).parent / "fixtures"

COMPLETE_ARTICLE = """
    {"@context": "https://schema.org", "@type": "NewsArticle",
     "headline": "Bir başlık", "description": "Bir özet.",
     "datePublished": "2026-08-03T10:00:00+03:00",
     "dateModified": "2026-08-03T12:00:00+03:00",
     "author": {"@type": "Person", "name": "Ayşe Yılmaz"},
     "publisher": {"@type": "Organization", "name": "TRT"},
     "image": "https://example.org/i.png", "inLanguage": "tr"}
"""


class StructuredDataAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryContentRepository()
        self.register = RegisterRawHtmlArticle(self.repository)
        self.analyze = AnalyzeStructuredData(self.repository)

    def ingest(self, slug, json_ld=None):
        script = (
            f'<script type="application/ld+json">{json_ld}</script>' if json_ld else ""
        )
        return self.register.execute(
            RawHtmlArticle(
                html=f'<html lang="tr"><head><title>{slug}</title>{script}</head>'
                f"<body><main><p>Görünür paragraf.</p></main></body></html>",
                source_url=f"https://ebeveynakademisi.trtcocuk.net.tr/makale/{slug}",
                publisher="TRT",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )

    def analyze_slug(self, slug, json_ld=None):
        registration = self.ingest(slug, json_ld)
        return self.analyze.execute(
            registration.article, registration.article_version.article_version_id
        )

    def test_reports_a_page_that_declares_nothing_about_itself(self):
        analysis = self.analyze_slug("bildirimsiz")

        self.assertFalse(analysis.article_node_present)
        self.assertEqual(analysis.declared_node_types, ())
        self.assertEqual(analysis.missing_article_properties, ())

    def test_reports_a_page_whose_structured_data_is_not_an_article(self):
        analysis = self.analyze_slug(
            "sadece-kurulus",
            '{"@context": "https://schema.org", "@type": "Organization", "name": "TRT"}',
        )

        self.assertFalse(analysis.article_node_present)
        self.assertEqual(analysis.declared_node_types, ("Organization",))

    def test_names_the_properties_an_article_leaves_undeclared(self):
        analysis = self.analyze_slug(
            "eksik",
            '{"@context": "https://schema.org", "@type": "NewsArticle",'
            ' "headline": "Bir başlık", "datePublished": "2026-08-03T10:00:00+03:00"}',
        )

        self.assertTrue(analysis.article_node_present)
        self.assertEqual(
            analysis.declared_article_properties, ("datePublished", "headline")
        )
        self.assertEqual(
            analysis.missing_article_properties,
            ("description", "dateModified", "author", "publisher", "image", "inLanguage"),
        )

    def test_reports_nothing_missing_when_an_article_declares_everything(self):
        analysis = self.analyze_slug("tam", COMPLETE_ARTICLE)

        self.assertTrue(analysis.article_node_present)
        self.assertEqual(analysis.missing_article_properties, ())

    def test_finds_the_article_node_after_an_unrelated_node(self):
        """TRT Haber declares an Organization before its Article."""
        analysis = self.analyze_slug(
            "sirali",
            '{"@context": "https://schema.org", "@type": "Organization", "name": "TRT"}',
        )
        self.assertFalse(analysis.article_node_present)

        analysis = self.analyze_slug("sirali-2", COMPLETE_ARTICLE)
        self.assertTrue(analysis.article_node_present)

    def test_names_undeclared_properties_in_words_an_editor_recognises(self):
        self.assertEqual(
            missing_properties_phrase(("inLanguage",)), "Not declared: language"
        )
        self.assertEqual(
            missing_properties_phrase(("datePublished", "author")),
            "Not declared: publication date and author",
        )
        self.assertEqual(
            missing_properties_phrase(("headline", "image", "inLanguage")),
            "Not declared: headline, image and language",
        )

    def test_uses_the_real_trt_cocuk_fixture(self):
        html = (FIXTURES / "trt_ebeveyn_akademisi_makale.html").read_text(encoding="utf-8")
        registration = self.register.execute(
            RawHtmlArticle(
                html=html,
                source_url="https://ebeveynakademisi.trtcocuk.net.tr/makale/asiri-uyumlu-cocuklar-neyi-saklar-32449390",
                publisher="TRT Çocuk Ebeveyn Akademisi",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )

        analysis = self.analyze.execute(
            registration.article, registration.article_version.article_version_id
        )

        self.assertTrue(analysis.article_node_present)
        self.assertIn("headline", analysis.declared_article_properties)
        self.assertIn("inLanguage", analysis.missing_article_properties)
        self.assertNotIn("image", analysis.missing_article_properties)

    def test_structured_data_findings_are_addressed_to_the_technical_audience(self):
        """Declarations live in the page template, so an editor cannot fix them."""
        from aether.application.analysis.analyze_article_metadata import (
            AnalyzeArticleMetadata,
        )
        from aether.application.analysis.analyze_article_structure import (
            AnalyzeArticleStructure,
        )
        from aether.application.analysis.analyze_passage_quality import (
            AnalyzePassageQuality,
        )
        from aether.application.analysis.assess_ai_readiness import AssessAIReadiness
        from aether.application.analysis.build_ai_readiness_report import (
            BuildAIReadinessReport,
        )
        from aether.application.analysis.build_article_analysis_report import (
            BuildArticleAnalysisReport,
        )
        from aether.application.analysis.derive_editor_recommendations import (
            RecommendationCategory,
        )

        registration = self.ingest("bildirimsiz")
        analysis = BuildArticleAnalysisReport(
            AnalyzeArticleStructure(self.repository),
            AnalyzeArticleMetadata(self.repository),
            AnalyzePassageQuality(self.repository),
            None,
            AnalyzeStructuredData(self.repository),
        ).execute(registration.article, registration.article_version.article_version_id)
        report = BuildAIReadinessReport().execute(
            AssessAIReadiness().execute(analysis)
        )

        structured = [
            r
            for r in report.editor_recommendations
            if r.code.value.endswith("article_structured_data")
        ]
        self.assertEqual(len(structured), 1)
        self.assertEqual(structured[0].category, RecommendationCategory.TECHNICAL)

    def test_rejects_an_article_version_from_a_different_article(self):
        first = self.ingest("birinci")
        second = self.ingest("ikinci")

        with self.assertRaises(DomainValidationError):
            self.analyze.execute(
                first.article, second.article_version.article_version_id
            )


if __name__ == "__main__":
    unittest.main()
