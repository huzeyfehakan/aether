import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, "src")

from aether.adapters.outbound.in_memory_content_repository import (  # noqa: E402
    InMemoryContentRepository,
)
from aether.application.analysis.analyze_heading_structure import (  # noqa: E402
    AnalyzeHeadingStructure,
)
from aether.application.ingestion.register_raw_html_article import (  # noqa: E402
    RawHtmlArticle,
    RegisterRawHtmlArticle,
)
from aether.domain.common import DomainValidationError  # noqa: E402


OBSERVED_AT = datetime(2026, 8, 7, 9, 0, tzinfo=timezone.utc)


class HeadingStructureTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryContentRepository()
        self.register = RegisterRawHtmlArticle(self.repository)
        self.analyze = AnalyzeHeadingStructure(self.repository)

    def ingest(self, slug, body):
        return self.register.execute(
            RawHtmlArticle(
                html=f'<html lang="tr"><head><title>{slug}</title></head>'
                f"<body><main>{body}</main></body></html>",
                source_url=f"https://publisher.example/{slug}",
                publisher="Publisher",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )

    def analyze_body(self, slug, body):
        registration = self.ingest(slug, body)
        return self.analyze.execute(
            registration.article, registration.article_version.article_version_id
        )

    def test_reads_the_outline_an_article_declares(self):
        analysis = self.analyze_body(
            "duzgun", "<h1>Ana başlık</h1><p>Metin.</p><h2>Bölüm</h2><p>Metin.</p>"
        )

        self.assertEqual([h.level for h in analysis.headings], [1, 2])
        self.assertEqual(analysis.top_level_count, 1)

    def test_reports_an_article_with_no_main_heading(self):
        analysis = self.analyze_body(
            "ana-yok", "<h2>Bölüm</h2><p>Metin.</p><h2>Başka bölüm</h2><p>Metin.</p>"
        )

        self.assertEqual(analysis.top_level_count, 0)
        self.assertTrue(analysis.has_headings)

    def test_reports_more_than_one_main_heading(self):
        analysis = self.analyze_body(
            "iki-ana", "<h1>Birinci</h1><p>Metin.</p><h1>İkinci</h1><p>Metin.</p>"
        )

        self.assertEqual(analysis.top_level_count, 2)

    def test_ignores_headings_outside_the_article(self):
        """A site banner heading is not the article's main heading."""
        registration = self.register.execute(
            RawHtmlArticle(
                html='<html lang="tr"><head><title>Sayfa</title></head><body>'
                "<header><h1>Yayıncı Adı</h1></header>"
                "<main><h1>Makale başlığı</h1><p>Metin.</p></main>"
                "<footer><h1>Alt bilgi</h1></footer></body></html>",
                source_url="https://publisher.example/banner",
                publisher="Publisher",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )

        analysis = self.analyze.execute(
            registration.article, registration.article_version.article_version_id
        )

        self.assertEqual([h.text for h in analysis.headings], ["Makale başlığı"])
        self.assertEqual(analysis.top_level_count, 1)

    def test_an_article_without_subheadings_is_not_reported(self):
        """Deliberately not a finding: it cannot be stated without a length rule.

        A short note needs no subheadings and a long feature does, and the
        boundary is a judgement about writing rather than a fact about markup.
        The absence of a main heading is reported instead, which is a fact.
        """
        analysis = self.analyze_body(
            "alt-basliksiz", "<h1>Ana başlık</h1><p>Tek paragraf.</p>"
        )

        self.assertEqual(analysis.top_level_count, 1)
        self.assertEqual(len(analysis.headings), 1)

    def test_more_than_one_main_heading_is_worded_as_a_heading_count(self):
        """It borrowed the repetition count and read as duplication."""
        from aether.application.analysis.analyze_article_metadata import (
            AnalyzeArticleMetadata,
        )
        from aether.application.analysis.analyze_article_structure import (
            AnalyzeArticleStructure,
        )
        from aether.application.analysis.analyze_passage_quality import (
            AnalyzePassageQuality,
        )
        from aether.application.analysis.build_article_analysis_report import (
            BuildArticleAnalysisReport,
        )
        from aether.application.analysis.derive_editor_recommendations import (
            DeriveEditorRecommendations,
            RecommendationCode,
        )
        from aether.presentation.editor_recommendation_text import heading_count_phrase

        registration = self.ingest(
            "iki-ana", "<h1>Birinci</h1><p>M.</p><h1>İkinci</h1><p>M.</p>"
        )
        report = BuildArticleAnalysisReport(
            AnalyzeArticleStructure(self.repository),
            AnalyzeArticleMetadata(self.repository),
            AnalyzePassageQuality(self.repository),
            heading_structure_analysis=AnalyzeHeadingStructure(self.repository),
        ).execute(registration.article, registration.article_version.article_version_id)

        recommendation = next(
            r
            for r in DeriveEditorRecommendations().execute(report)
            if r.code is RecommendationCode.MULTIPLE_TOP_LEVEL_HEADINGS
        )

        self.assertEqual(recommendation.heading_count, 2)
        self.assertEqual(recommendation.other_article_count, 0)
        self.assertIn("main heading", heading_count_phrase(recommendation.heading_count))
        self.assertNotIn("other article", heading_count_phrase(recommendation.heading_count))

    def test_rejects_an_article_version_from_a_different_article(self):
        first = self.ingest("birinci", "<h1>Bir</h1><p>Metin.</p>")
        second = self.ingest("ikinci", "<h1>İki</h1><p>Metin.</p>")

        with self.assertRaises(DomainValidationError):
            self.analyze.execute(
                first.article, second.article_version.article_version_id
            )


if __name__ == "__main__":
    unittest.main()
