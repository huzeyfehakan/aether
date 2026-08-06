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

    def build(self, with_duplication=True):
        return BuildArticleAnalysisReport(
            AnalyzeArticleStructure(self.repository),
            AnalyzeArticleMetadata(self.repository),
            AnalyzePassageQuality(self.repository),
            AnalyzeContentDuplication(self.repository) if with_duplication else None,
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

    def report_for(self, registration, with_duplication=True):
        analysis = self.build(with_duplication).execute(
            registration.article, registration.article_version.article_version_id
        )
        return BuildAIReadinessReport().execute(AssessAIReadiness().execute(analysis))

    def test_repeated_text_is_a_content_quality_recommendation(self):
        """Repetition is measured in the text; it is not an AI visibility claim."""
        first = self.ingest("birinci", ["Özgün paragraf.", NOTICE])
        self.ingest("ikinci", ["Başka özgün paragraf.", NOTICE])

        report = self.report_for(first)

        self.assertEqual(len(report.editor_recommendations), 1)
        recommendation = report.editor_recommendations[0]
        self.assertEqual(
            recommendation.code, RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY
        )
        self.assertEqual(
            recommendation.category, RecommendationCategory.CONTENT_QUALITY
        )
        self.assertEqual(recommendation.excerpt, NOTICE)
        self.assertEqual(report.content_reuse_summary.compared_article_count, 1)

    def test_makes_no_recommendation_when_nothing_is_repeated(self):
        first = self.ingest("birinci", ["Özgün paragraf."])
        self.ingest("ikinci", ["Tamamen farklı paragraf."])

        report = self.report_for(first)

        self.assertEqual(report.editor_recommendations, ())
        self.assertEqual(report.content_reuse_summary.compared_article_count, 1)

    def test_report_omits_reuse_entirely_when_the_capability_is_not_used(self):
        first = self.ingest("birinci", ["Özgün paragraf.", NOTICE])
        self.ingest("ikinci", ["Başka paragraf.", NOTICE])

        report = self.report_for(first, with_duplication=False)

        self.assertIsNone(report.content_reuse_summary)
        self.assertEqual(report.editor_recommendations, ())

    def test_states_how_many_articles_were_compared(self):
        for count, expected in (
            (0, "No other articles from this publisher have been analysed yet"),
            (1, "Checked against 1 other article"),
            (4, "Checked against 4 other articles"),
        ):
            with self.subTest(count=count):
                self.assertIn(expected, compared_articles_phrase(count))

    def test_rendered_report_files_repetition_under_content_quality(self):
        first = self.ingest("birinci", ["Özgün paragraf.", NOTICE])
        self.ingest("ikinci", ["Başka özgün paragraf.", NOTICE])

        rendered = PlainTextAIReadinessReportRenderer().render(self.report_for(first))

        self.assertIn("Content Quality", rendered)
        self.assertNotIn("AI Visibility", rendered)
        self.assertIn("Checked against 1 other article from this publisher.", rendered)
        self.assertIn("What to do:", rendered)

    def test_content_quality_wording_makes_no_claim_about_ai_systems(self):
        """Repetition is a fact about the text, not evidence of model behaviour."""
        first = self.ingest("birinci", ["Özgün paragraf.", NOTICE])
        self.ingest("ikinci", ["Başka özgün paragraf.", NOTICE])
        report = self.report_for(first)

        text = recommendation_text(report.editor_recommendations[0])
        wording = " ".join((text.headline, text.why_it_matters, text.what_to_do)).lower()

        for claim in ("ai system", "retrieval", "model", "ignored", "rank"):
            self.assertNotIn(claim, wording)
        for jargon in ("passage", "corpus", "fingerprint"):
            self.assertNotIn(jargon, wording)


if __name__ == "__main__":
    unittest.main()
