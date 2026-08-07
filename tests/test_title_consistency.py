import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "src")

from aether.adapters.outbound.in_memory_content_repository import (  # noqa: E402
    InMemoryContentRepository,
)
from aether.application.analysis.analyze_title_consistency import (  # noqa: E402
    AnalyzeTitleConsistency,
)
from aether.application.analysis.declared_text_comparison import (  # noqa: E402
    all_declared_values_agree,
    normalize_declared_text,
    declared_values_agree,
)
from aether.application.ingestion.register_raw_html_article import (  # noqa: E402
    RawHtmlArticle,
    RegisterRawHtmlArticle,
)
from aether.domain.common import DomainValidationError  # noqa: E402
from aether.domain.source_data import DescriptionSource, TitleSource  # noqa: E402


OBSERVED_AT = datetime(2026, 8, 7, 9, 0, tzinfo=timezone.utc)
FIXTURES = Path(__file__).parent / "fixtures"


class TitleNormalizationTests(unittest.TestCase):
    """The normalization step, tested on its own."""

    def test_decodes_character_references(self):
        self.assertEqual(
            normalize_declared_text("&quot;Milli Dayanışma&quot; teklifi"),
            '"milli dayanışma" teklifi',
        )

    def test_collapses_whitespace(self):
        self.assertEqual(normalize_declared_text("  Bir   Başlık \n"), "bir başlık")

    def test_folds_case_without_depending_on_locale(self):
        self.assertEqual(normalize_declared_text("BIR BASLIK"), normalize_declared_text("bir baslik"))

    def test_drops_the_combining_dot_that_case_folding_introduces(self):
        """Folding a dotted capital I leaves a mark typed text never has."""
        self.assertEqual(normalize_declared_text("İstanbul"), normalize_declared_text("istanbul"))

    def test_documents_the_turkish_dotless_i_limit(self):
        """Resolving I against ı needs a Turkish locale, which would break others.

        A title declared in capitals in one place and lower case in another can
        therefore be reported as different. This pins the behaviour so the limit
        is visible rather than surprising.
        """
        self.assertNotEqual(normalize_declared_text("BAŞLIK"), normalize_declared_text("başlık"))

    def test_writes_every_padded_separator_one_way(self):
        self.assertEqual(
            normalize_declared_text("Başlık | Site"), normalize_declared_text("Başlık – Site")
        )

    def test_leaves_unpadded_punctuation_alone(self):
        """An unpadded hyphen is part of the headline, not a site separator."""
        self.assertEqual(normalize_declared_text("Ankara-Istanbul hattı"), "ankara-istanbul hattı")


class TitleAgreementTests(unittest.TestCase):
    def test_ignores_a_site_name_appended_to_one_declaration(self):
        self.assertTrue(
            declared_values_agree(
                "Aşırı Uyumlu Çocuklar Neyi Saklar? - Ebeveyn Akademisi",
                "Aşırı Uyumlu Çocuklar Neyi Saklar?",
            )
        )

    def test_ignores_a_site_name_prepended_to_one_declaration(self):
        self.assertTrue(
            declared_values_agree(
                "Five times Israel manipulated institutions",
                "TRT World - Five times Israel manipulated institutions",
            )
        )

    def test_reports_a_genuinely_different_headline(self):
        self.assertFalse(
            declared_values_agree(
                '12 Maddelik "Çerçeve Kanun" Teklifinin detayları netleşti - Son Dakika',
                '12 Maddelik "Milli Dayanışma" Teklifinin detayları netleşti',
            )
        )

    def test_a_shared_site_name_is_not_a_shared_headline(self):
        """The site name must not pass as the headline, in either position."""
        self.assertFalse(declared_values_agree("Story - Site", "Other - Site"))
        self.assertFalse(declared_values_agree("Site - Story", "Site - Other"))

    def test_a_missing_declaration_is_not_a_disagreement(self):
        self.assertTrue(declared_values_agree("Bir Başlık", ""))
        self.assertTrue(all_declared_values_agree(()))
        self.assertTrue(all_declared_values_agree(("Tek Başlık",)))

    def test_compares_all_declarations_together_not_in_pairs(self):
        """One title may carry the site name first and another last."""
        declarations = (
            "Five times Israel manipulated institutions - TRT World",
            "TRT World - Five times Israel manipulated institutions",
            "Five times Israel manipulated institutions",
        )

        self.assertTrue(all_declared_values_agree(declarations))


class TitleConsistencyAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryContentRepository()
        self.register = RegisterRawHtmlArticle(self.repository)
        self.analyze = AnalyzeTitleConsistency(self.repository)

    def ingest(self, slug, document_title, og_title=None, headline=None,
               description=None, og_description=None):
        og = f'<meta property="og:title" content="{og_title}" />' if og_title else ""
        og += f'<meta name="description" content="{description}" />' if description else ""
        og += (
            f'<meta property="og:description" content="{og_description}" />'
            if og_description
            else ""
        )
        ld = (
            f'<script type="application/ld+json">{{"@type": "NewsArticle", '
            f'"headline": "{headline}"}}</script>'
            if headline
            else ""
        )
        return self.register.execute(
            RawHtmlArticle(
                html=f'<html lang="tr"><head><title>{document_title}</title>{og}{ld}</head>'
                f"<body><main><p>Görünür paragraf.</p></main></body></html>",
                source_url=f"https://publisher.example/{slug}",
                publisher="Publisher",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )

    def analyze_slug(self, slug, **kwargs):
        registration = self.ingest(slug, **kwargs)
        return self.analyze.execute(
            registration.article, registration.article_version.article_version_id
        )

    def test_retains_every_declared_title_with_its_source(self):
        analysis = self.analyze_slug(
            "hepsi",
            document_title="Başlık - Site",
            og_title="Başlık",
            headline="Başlık",
        )

        self.assertEqual(analysis.declared_source_count, 3)
        self.assertEqual(
            [title.source for title in analysis.declared_titles],
            [
                TitleSource.DOCUMENT_TITLE,
                TitleSource.OPEN_GRAPH,
                TitleSource.STRUCTURED_DATA,
            ],
        )
        self.assertTrue(analysis.titles_agree)

    def test_reports_disagreement_when_headlines_actually_differ(self):
        analysis = self.analyze_slug(
            "farkli",
            document_title="Birinci Başlık - Site",
            og_title="Tamamen Başka Başlık",
        )

        self.assertFalse(analysis.titles_agree)

    def test_a_single_declaration_cannot_disagree(self):
        analysis = self.analyze_slug("tek", document_title="Yalnız Başlık")

        self.assertEqual(analysis.declared_source_count, 1)
        self.assertTrue(analysis.titles_agree)

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

        # The document title carries a site suffix the headline does not; that
        # is formatting, not a different headline.
        self.assertEqual(analysis.declared_source_count, 2)
        self.assertTrue(analysis.titles_agree)

    def test_reports_when_summaries_actually_differ(self):
        analysis = self.analyze_slug(
            "ozet-farkli",
            document_title="Başlık",
            description="Bu makale çocuk gelişimini anlatıyor.",
            og_description="Tamamen farklı bir özet metni.",
        )

        self.assertEqual(analysis.declared_description_count, 2)
        self.assertFalse(analysis.descriptions_agree)
        self.assertEqual(
            [d.source for d in analysis.declared_descriptions],
            [DescriptionSource.META_DESCRIPTION, DescriptionSource.OPEN_GRAPH],
        )

    def test_ignores_a_tagline_appended_to_one_summary(self):
        """TRT Çocuk appends a site tagline to the meta description only."""
        analysis = self.analyze_slug(
            "ozet-tagline",
            document_title="Başlık",
            description="Bir özet metni. - Çocuk gelişiminde bilmeniz gerekenler",
            og_description="Bir özet metni.",
        )

        self.assertTrue(analysis.descriptions_agree)

    def test_a_single_summary_cannot_disagree(self):
        analysis = self.analyze_slug(
            "ozet-tek", document_title="Başlık", description="Yalnız özet."
        )

        self.assertEqual(analysis.declared_description_count, 1)
        self.assertTrue(analysis.descriptions_agree)

    def test_rejects_an_article_version_from_a_different_article(self):
        first = self.ingest("birinci", document_title="Bir")
        second = self.ingest("ikinci", document_title="İki")

        with self.assertRaises(DomainValidationError):
            self.analyze.execute(
                first.article, second.article_version.article_version_id
            )


if __name__ == "__main__":
    unittest.main()
