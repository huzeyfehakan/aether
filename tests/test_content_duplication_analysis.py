import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "src")

from aether.adapters.outbound.in_memory_content_repository import (  # noqa: E402
    InMemoryContentRepository,
)
from aether.application.analysis.analyze_content_duplication import (  # noqa: E402
    AnalyzeContentDuplication,
)
from aether.application.ingestion.register_raw_html_article import (  # noqa: E402
    RawHtmlArticle,
    RegisterRawHtmlArticle,
)
from aether.domain.common import DomainValidationError  # noqa: E402


OBSERVED_AT = datetime(2026, 8, 6, 9, 0, tzinfo=timezone.utc)
FIXTURES = Path(__file__).parent / "fixtures"
DISCLAIMER = "Bu içerik bilgilendirme amaçlı hazırlanmıştır."


def article_html(title, body_paragraphs):
    paragraphs = "".join(f"<p>{text}</p>" for text in body_paragraphs)
    return (
        f'<html lang="tr"><head><title>{title}</title></head>'
        f"<body><main>{paragraphs}</main></body></html>"
    )


class ContentDuplicationAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryContentRepository()
        self.register = RegisterRawHtmlArticle(self.repository)
        self.analyze = AnalyzeContentDuplication(self.repository)

    def ingest(self, slug, paragraphs, publisher="TRT Çocuk Ebeveyn Akademisi"):
        return self.register.execute(
            RawHtmlArticle(
                html=article_html(slug, paragraphs),
                source_url=f"https://ebeveynakademisi.trtcocuk.net.tr/makale/{slug}",
                publisher=publisher,
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )

    def test_reports_text_repeated_across_the_publishers_articles(self):
        first = self.ingest("birinci", ["Birinci makalenin özgün paragrafı.", DISCLAIMER])
        self.ingest("ikinci", ["İkinci makalenin özgün paragrafı.", DISCLAIMER])
        self.ingest("ucuncu", ["Üçüncü makalenin özgün paragrafı.", DISCLAIMER])

        analysis = self.analyze.execute(
            first.article, first.article_version.article_version_id
        )

        self.assertEqual(analysis.compared_article_count, 2)
        self.assertEqual(analysis.total_passage_count, 2)
        self.assertEqual(analysis.repeated_passage_count, 1)
        repeated = analysis.repeated_passages[0]
        self.assertEqual(repeated.text, DISCLAIMER)
        self.assertEqual(repeated.other_article_count, 2)

    def test_reports_nothing_when_no_other_article_has_been_analyzed(self):
        only = self.ingest("tek", ["Tek makalenin paragrafı.", DISCLAIMER])

        analysis = self.analyze.execute(
            only.article, only.article_version.article_version_id
        )

        self.assertEqual(analysis.compared_article_count, 0)
        self.assertEqual(analysis.repeated_passages, ())

    def test_does_not_compare_across_publishers(self):
        first = self.ingest("birinci", ["Özgün paragraf.", DISCLAIMER])
        self.ingest("baska", ["Farklı yayıncı paragrafı.", DISCLAIMER], publisher="TRT Haber")

        analysis = self.analyze.execute(
            first.article, first.article_version.article_version_id
        )

        self.assertEqual(analysis.compared_article_count, 0)
        self.assertEqual(analysis.repeated_passages, ())

    def test_orders_findings_by_how_widely_the_text_is_repeated(self):
        shared_twice = "Her makalede tekrar eden uyarı."
        shared_once = "İki makalede tekrar eden imza."
        first = self.ingest("birinci", ["Özgün paragraf.", shared_once, shared_twice])
        self.ingest("ikinci", ["Başka özgün paragraf.", shared_once, shared_twice])
        self.ingest("ucuncu", ["Üçüncü özgün paragraf.", shared_twice])

        analysis = self.analyze.execute(
            first.article, first.article_version.article_version_id
        )

        self.assertEqual(
            [(item.text, item.other_article_count) for item in analysis.repeated_passages],
            [(shared_twice, 2), (shared_once, 1)],
        )

    def test_finds_the_real_boilerplate_in_the_trt_cocuk_fixture(self):
        """The live TRT Çocuk fixture carries a standing legal notice."""
        html = (FIXTURES / "trt_ebeveyn_akademisi_makale.html").read_text(encoding="utf-8")
        first = self.register.execute(
            RawHtmlArticle(
                html=html,
                source_url="https://ebeveynakademisi.trtcocuk.net.tr/makale/asiri-uyumlu-cocuklar-neyi-saklar-32449390",
                publisher="TRT Çocuk Ebeveyn Akademisi",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )
        self.register.execute(
            RawHtmlArticle(
                html=html.replace(
                    "Aşırı uyumlu çocuklar çoğu zaman çevre tarafından kolay çocuk olarak tanımlanır.",
                    "Bambaşka bir makalenin açılış paragrafı.",
                ).replace("asiri-uyumlu-cocuklar-neyi-saklar-32449390", "ikinci-makale-32449391"),
                source_url="https://ebeveynakademisi.trtcocuk.net.tr/makale/ikinci-makale-32449391",
                publisher="TRT Çocuk Ebeveyn Akademisi",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )

        analysis = self.analyze.execute(
            first.article, first.article_version.article_version_id
        )

        self.assertEqual(analysis.compared_article_count, 1)
        repeated_text = [item.text for item in analysis.repeated_passages]
        self.assertIn("Bu içerik bilgilendirme amaçlı hazırlanmıştır.", repeated_text)
        self.assertIn("Prof. Dr. Funda Gümüştaş", repeated_text)
        self.assertNotIn(
            "Aşırı uyumlu çocuklar çoğu zaman çevre tarafından kolay çocuk olarak tanımlanır.",
            repeated_text,
        )

    def test_reports_a_body_that_is_mostly_shared_text(self):
        """Two measured quantities are compared; no length is judged."""
        long_notice = " ".join(["uyarı"] * 40)
        first = self.ingest("kisa", ["Kısa özgün cümle.", long_notice])
        self.ingest("ikinci", ["Başka özgün cümle.", long_notice])

        analysis = self.analyze.execute(
            first.article, first.article_version.article_version_id
        )

        self.assertTrue(analysis.is_mostly_repeated)
        self.assertEqual(analysis.repeated_word_count, 40)
        self.assertEqual(analysis.unique_word_count, 3)

    def test_a_short_article_of_its_own_writing_is_not_reported(self):
        """No word-count threshold: brevity alone is never a finding."""
        first = self.ingest("kisa-ozgun", ["İki kelime."])
        self.ingest("baska", ["Tamamen farklı bir cümle."])

        analysis = self.analyze.execute(
            first.article, first.article_version.article_version_id
        )

        self.assertFalse(analysis.is_mostly_repeated)
        self.assertEqual(analysis.repeated_word_count, 0)

    def test_a_long_article_with_a_little_boilerplate_is_not_reported(self):
        notice = "Bu bir standart uyarı metnidir."
        body = " ".join(["özgün"] * 60)
        first = self.ingest("uzun", [body, notice])
        self.ingest("uzun-iki", ["Başka gövde metni.", notice])

        analysis = self.analyze.execute(
            first.article, first.article_version.article_version_id
        )

        self.assertFalse(analysis.is_mostly_repeated)

    def test_nothing_is_reported_without_another_article_to_compare(self):
        only = self.ingest("tek", ["Kısa cümle.", "Başka cümle."])

        analysis = self.analyze.execute(
            only.article, only.article_version.article_version_id
        )

        self.assertFalse(analysis.is_mostly_repeated)
        self.assertEqual(analysis.compared_article_count, 0)

    def test_rejects_an_article_version_from_a_different_article(self):
        first = self.ingest("birinci", ["Özgün paragraf."])
        second = self.ingest("ikinci", ["Başka paragraf."])

        with self.assertRaises(DomainValidationError):
            self.analyze.execute(
                first.article, second.article_version.article_version_id
            )


if __name__ == "__main__":
    unittest.main()
