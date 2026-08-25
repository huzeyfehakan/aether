import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "src")

from aether.adapters.outbound.in_memory_content_repository import (  # noqa: E402
    InMemoryContentRepository,
)
from aether.application.ingestion.register_raw_html_article import (  # noqa: E402
    RawHtmlArticle,
    RegisterRawHtmlArticle,
)
from aether.domain.common import DomainValidationError  # noqa: E402


OBSERVED_AT = datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc)
FIXTURES = Path(__file__).parent / "fixtures"


class RawHtmlIngestionTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryContentRepository()
        self.register = RegisterRawHtmlArticle(self.repository)

    def raw_article(self, html):
        return RawHtmlArticle(
            html=html,
            source_url="https://source.example.org/raw-story",
            publisher="TRT",
            article_type="news_report",
            observed_at=OBSERVED_AT,
        )

    def test_ingests_common_article_html_into_immutable_version_and_passages(self):
        html = """
            <html lang="tr">
              <head>
                <link rel="canonical" href="https://news.example.org/story" />
                <meta property="og:title" content="Bakanlık yeni tedbiri açıkladı" />
                <meta property="article:published_time" content="2026-07-22T11:30:00+03:00" />
                <meta property="article:modified_time" content="2026-07-22T12:00:00+03:00" />
                <meta name="author" content="Ayşe Yılmaz" />
                <meta name="description" content="A source-provided description." />
                <meta name="keywords" content="politika, ekonomi,  haber" />
                <title>Fallback title</title>
              </head>
              <body>
                <nav><p>Navigation text must not become article content.</p></nav>
                <article>
                  <p>Bakanlık yeni tedbiri açıkladı.</p>
                  <p>Tedbir ülke genelinde uygulanacak.</p>
                  <script>Ignored script content.</script>
                </article>
              </body>
            </html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertTrue(result.version_created)
        self.assertEqual(result.article.canonical_source, "https://news.example.org/story")
        self.assertEqual(result.article.original_language, "tr")
        self.assertEqual(result.article_version.title, "Bakanlık yeni tedbiri açıkladı")
        self.assertEqual(
            result.article_version.body,
            "Bakanlık yeni tedbiri açıkladı.\n\nTedbir ülke genelinde uygulanacak.",
        )
        self.assertEqual(
            [passage.text for passage in result.passages],
            ["Bakanlık yeni tedbiri açıkladı.", "Tedbir ülke genelinde uygulanacak."],
        )
        self.assertEqual(
            result.article_version.source_published_at.isoformat(),
            "2026-07-22T11:30:00+03:00",
        )
        self.assertEqual(
            result.article_version.source_updated_at.isoformat(),
            "2026-07-22T12:00:00+03:00",
        )
        self.assertEqual(result.article_version.author, "Ayşe Yılmaz")
        self.assertEqual(result.article_version.description, "A source-provided description.")
        self.assertEqual(result.article_version.keywords, "politika, ekonomi,  haber")

    def metric_source_data(self, html):
        result = self.register.execute(self.raw_article(html))
        return self.repository.get_source_data(result.article_version.article_version_id)

    def test_heading_waits_for_real_passage_after_date_and_byline(self):
        source_data = self.metric_source_data("""
            <html lang="tr"><head><title>Başlık</title></head><body><article>
              <h1>Çocuk gelişimi</h1>
              <div itemprop="datePublished"><p>3 Ağustos 2026</p></div>
              <div itemprop="author"><p>Ayşe Yılmaz</p></div>
              <p>Çocuk gelişimi aile desteğiyle güçlenir.</p>
            </article></body></html>
        """)

        self.assertEqual(source_data.heading_passage_overlap_ratio, 1.0)

    def test_heading_ignores_non_body_recommendation_before_real_passage(self):
        source_data = self.metric_source_data("""
            <html lang="tr"><head><title>Başlık</title></head><body><main>
              <h2>Çocuk gelişimi</h2>
              <a href="/öneri"><p>İlgili öneri kartı.</p></a>
              <p>Çocuk gelişimi aile desteğiyle güçlenir.</p>
            </main></body></html>
        """)

        self.assertEqual(source_data.heading_passage_overlap_ratio, 1.0)

    def test_overlap_normalizes_unicode_punctuation_case_and_turkish_i(self):
        examples = (
            ("Çocuk?", "çocuk gelişir."),
            ("Gelişim,", "gelişim desteklenir."),
            ("ÇOCUK", "çocuk gelişir."),
            ("IŞIK İZİ I İ ı i", "ışık izi ı i."),
        )
        for index, (heading, paragraph) in enumerate(examples):
            with self.subTest(heading=heading, paragraph=paragraph):
                source_data = self.metric_source_data(f"""
                    <html lang="tr"><head><title>Başlık {index}</title></head>
                    <body><main><h2>{heading}</h2><p>{paragraph}</p></main></body></html>
                """)
                self.assertEqual(source_data.heading_passage_overlap_ratio, 1.0)

    def test_unmeasured_metrics_are_none_and_measured_zero_is_preserved(self):
        no_heading = self.metric_source_data("""
            <html lang="tr"><head><title>Başlık</title></head>
            <body><main><p>Gerçek içerik.</p></main></body></html>
        """)
        self.assertIsNone(no_heading.heading_passage_overlap_ratio)
        self.assertIsNone(no_heading.definitive_stance_ratio)

        no_overlap = self.metric_source_data("""
            <html lang="tr"><head><title>Başlık</title></head>
            <body><main><h2>Çocuk gelişimi</h2><p>Bambaşka sözcükler.</p></main></body></html>
        """)
        self.assertEqual(no_overlap.heading_passage_overlap_ratio, 0.0)
        self.assertIsNone(no_overlap.definitive_stance_ratio)

        question_without_yes_no = self.metric_source_data("""
            <html lang="tr"><head><title>Başlık</title></head>
            <body><main><h2>Çocuk gelişir mi?</h2><p>Çocuk zamanla gelişir.</p></main></body></html>
        """)
        self.assertEqual(question_without_yes_no.definitive_stance_ratio, 0.0)

    def test_trt_heading_metrics_use_article_passage_instead_of_date(self):
        html = (FIXTURES / "trt_ebeveyn_akademisi_makale.html").read_text(encoding="utf-8")
        result = self.register.execute(
            RawHtmlArticle(
                html=html,
                source_url="https://ebeveynakademisi.trtcocuk.net.tr/makale/asiri-uyumlu-cocuklar-neyi-saklar-32449390",
                publisher="TRT Çocuk Ebeveyn Akademisi",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )
        source_data = self.repository.get_source_data(result.article_version.article_version_id)

        # H1 contributes 3/5 and the later informational H5 contributes 0/2.
        self.assertEqual(source_data.heading_passage_overlap_ratio, 0.3)
        self.assertEqual(source_data.definitive_stance_ratio, 0.0)

    def test_retains_an_inventory_of_declared_structured_data(self):
        """What a page declares to machines survives text normalization."""
        html = """
            <html lang="tr"><head><title>Inventory</title>
              <script type="application/ld+json">
                {"@context": "https://schema.org", "@type": "NewsArticle",
                 "headline": "Bir başlık", "datePublished": "2026-08-03T10:00:00+03:00",
                 "author": {"@type": "Organization", "name": "TRT"}}
              </script>
            </head><body><main><p>Görünür paragraf.</p></main></body></html>
        """

        result = self.register.execute(self.raw_article(html))
        source_data = self.repository.get_source_data(
            result.article_version.article_version_id
        )

        types = [node.node_type for node in source_data.structured_data_nodes]
        self.assertIn("NewsArticle", types)
        self.assertIn("Organization", types)
        article = next(
            node for node in source_data.structured_data_nodes
            if node.node_type == "NewsArticle"
        )
        self.assertEqual(
            article.property_names, ("author", "datePublished", "headline")
        )
        self.assertTrue(article.declares("headline"))

    def test_retains_an_empty_inventory_when_a_page_declares_nothing(self):
        html = """
            <html lang="tr"><head><title>No structured data</title></head>
            <body><main><p>Görünür paragraf.</p></main></body></html>
        """

        result = self.register.execute(self.raw_article(html))
        source_data = self.repository.get_source_data(
            result.article_version.article_version_id
        )

        self.assertEqual(source_data.structured_data_nodes, ())

    def test_normalizes_date_only_json_ld_dates_to_midnight_utc(self):
        """TRT Çocuk Ebeveyn Akademisi publishes Schema.org Date, not DateTime."""
        html = (FIXTURES / "trt_ebeveyn_akademisi_makale.html").read_text(encoding="utf-8")

        result = self.register.execute(
            RawHtmlArticle(
                html=html,
                source_url="https://ebeveynakademisi.trtcocuk.net.tr/makale/asiri-uyumlu-cocuklar-neyi-saklar-32449390",
                publisher="TRT Çocuk Ebeveyn Akademisi",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )

        version = result.article_version
        self.assertEqual(
            version.source_published_at.isoformat(), "2026-08-03T00:00:00+00:00"
        )
        self.assertEqual(
            version.source_updated_at.isoformat(), "2026-08-03T00:00:00+00:00"
        )
        self.assertEqual(result.article.initial_published_at, version.source_published_at)

    def test_normalizes_a_date_only_meta_publication_date(self):
        html = """
            <html lang="tr"><head><title>Date-only meta</title>
              <meta property="article:published_time" content="2026-08-03" />
            </head><body><main><p>Görünür paragraf.</p></main></body></html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertEqual(
            result.article_version.source_published_at.isoformat(),
            "2026-08-03T00:00:00+00:00",
        )

    def test_normalizes_timezone_naive_json_ld_date_published_to_utc(self):
        html = """
            <html lang="en"><head><title>Naive datetime</title>
              <script type="application/ld+json">
                {"@type": "Article", "datePublished": "2026-08-03T10:00:00"}
              </script>
            </head><body><main><p>Visible article paragraph.</p></main></body></html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertEqual(
            result.article_version.source_published_at.isoformat(),
            "2026-08-03T10:00:00+00:00",
        )

    def test_rejects_a_malformed_date_only_value(self):
        html = """
            <html lang="en"><head><title>Impossible date</title>
              <script type="application/ld+json">
                {"@type": "Article", "datePublished": "2026-13-45"}
              </script>
            </head><body><main><p>Visible article paragraph.</p></main></body></html>
        """

        with self.assertRaisesRegex(
            DomainValidationError, "JSON-LD Article datePublished must be ISO-8601"
        ):
            self.register.execute(self.raw_article(html))

    def test_excludes_link_wrapped_recommendation_cards_from_the_body(self):
        """Recommendation cards share the article container on TRT Çocuk pages."""
        html = (FIXTURES / "trt_ebeveyn_akademisi_makale.html").read_text(encoding="utf-8")

        result = self.register.execute(
            RawHtmlArticle(
                html=html,
                source_url="https://ebeveynakademisi.trtcocuk.net.tr/makale/asiri-uyumlu-cocuklar-neyi-saklar-32449390",
                publisher="TRT Çocuk Ebeveyn Akademisi",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )

        body = result.article_version.body
        self.assertIn("Aşırı uyumlu çocuklar çoğu zaman", body)
        self.assertIn("Bu uyumun ardında çoğu zaman", body)
        self.assertNotIn("İşten sonra çocuğunuzla", body)
        self.assertNotIn("Öfke sağlıklı", body)

    def test_excludes_paragraphs_from_non_body_html_sections(self):
        html = """
            <html lang="en"><head><title>Sectioning</title></head>
            <body>
              <header><p>Site tagline.</p></header>
              <nav><p>Navigation text.</p></nav>
              <main>
                <p>Real article prose.</p>
                <aside><p>Sidebar promotion.</p></aside>
                <figure><figcaption><p>Photo caption.</p></figcaption></figure>
                <a href="/other"><p>Linked teaser card.</p></a>
              </main>
              <footer><p>Copyright notice.</p></footer>
            </body></html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertEqual(result.article_version.body, "Real article prose.")

    def test_keeps_inline_links_inside_body_paragraphs(self):
        """A paragraph containing a link is prose; a paragraph inside a link is not."""
        html = """
            <html lang="en"><head><title>Inline links</title></head>
            <body><main>
              <p>Prose with an <a href="/source">inline citation</a> inside it.</p>
            </main></body></html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertEqual(
            result.article_version.body,
            "Prose with an inline citation inside it.",
        )

    def test_falls_back_to_open_graph_locale_when_html_has_no_lang(self):
        """TRT Avaz declares the document language only through og:locale."""
        html = (FIXTURES / "trt_avaz_haber.html").read_text(encoding="utf-8")

        result = self.register.execute(
            RawHtmlArticle(
                html=html,
                source_url="https://www.trtavaz.com.tr/haber/tur/avrasyadan/aselsan-dan-2026-nin-ilk-yarisinda-rekor-buyume/6a72f74e6b61e0f45f28c685",
                publisher="TRT Avaz",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )

        self.assertEqual(result.article.original_language, "tr-TR")
        self.assertEqual([passage.language for passage in result.passages], ["tr-TR", "tr-TR"])

    def test_falls_back_to_json_ld_in_language_when_no_lang_or_locale(self):
        html = """
            <html><head><title>JSON-LD language</title>
              <script type="application/ld+json">
                {"@context": "https://schema.org", "@type": "NewsArticle",
                 "inLanguage": "en"}
              </script>
            </head><body><main><p>Visible article paragraph.</p></main></body></html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertEqual(result.article.original_language, "en")

    def test_prefers_html_lang_over_locale_and_json_ld_language(self):
        html = """
            <html lang="tr"><head><title>Language precedence</title>
              <meta property="og:locale" content="de_DE" />
              <script type="application/ld+json">
                {"@context": "https://schema.org", "@type": "Article",
                 "inLanguage": "fr"}
              </script>
            </head><body><main><p>Visible article paragraph.</p></main></body></html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertEqual(result.article.original_language, "tr")

    def test_reads_headline_description_author_and_dates_from_json_ld(self):
        """TRT Haber carries these fields only in JSON-LD, after an Organization block."""
        html = (FIXTURES / "trt_haber_json_ld_article.html").read_text(encoding="utf-8")

        result = self.register.execute(
            RawHtmlArticle(
                html=html,
                source_url="https://www.trthaber.com/haber/gundem/12-maddelik-milli-dayanisma-teklifinin-detaylari-netlesti-953155.html",
                publisher="TRT Haber",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )

        version = result.article_version
        self.assertEqual(
            version.title, "12 Maddelik Milli Dayanışma Teklifinin detayları netleşti"
        )
        self.assertEqual(
            version.description, "Kanun teklifinin maddeleri ve süreç işleyişi belli oldu."
        )
        self.assertEqual(version.author, "TRT Haber")
        self.assertEqual(
            version.source_published_at.isoformat(), "2026-08-05T12:43:00+03:00"
        )
        self.assertEqual(
            version.source_updated_at.isoformat(), "2026-08-05T14:10:44+03:00"
        )

    def test_json_ld_author_accepts_string_and_list_forms(self):
        for author_json, expected in (
            ('"Ayşe Yılmaz"', "Ayşe Yılmaz"),
            ('[{"@type": "Person", "name": "Ayşe Yılmaz"}]', "Ayşe Yılmaz"),
            ('{"@type": "Person", "name": "Ayşe Yılmaz"}', "Ayşe Yılmaz"),
        ):
            with self.subTest(author=author_json):
                html = f"""
                    <html lang="tr"><head><title>Author shapes</title>
                      <script type="application/ld+json">
                        {{"@type": "Article", "author": {author_json}}}
                      </script>
                    </head><body><main><p>Görünür paragraf.</p></main></body></html>
                """
                result = RegisterRawHtmlArticle(InMemoryContentRepository()).execute(
                    RawHtmlArticle(
                        html=html,
                        source_url=f"https://source.example.org/author-{len(author_json)}",
                        publisher="TRT",
                        article_type="news_report",
                        observed_at=OBSERVED_AT,
                    )
                )
                self.assertEqual(result.article_version.author, expected)

    def test_json_ld_metadata_takes_precedence_over_meta_tags(self):
        html = """
            <html lang="tr"><head>
              <title>Meta title</title>
              <meta name="description" content="Meta description." />
              <meta name="author" content="Meta author" />
              <meta property="article:modified_time" content="2026-07-22T12:00:00+03:00" />
              <script type="application/ld+json">
                {"@type": "NewsArticle", "headline": "JSON-LD headline",
                 "description": "JSON-LD description.", "author": "JSON-LD author",
                 "dateModified": "2026-07-22T18:00:00+03:00"}
              </script>
            </head><body><main><p>Görünür paragraf.</p></main></body></html>
        """

        result = self.register.execute(self.raw_article(html))

        version = result.article_version
        self.assertEqual(version.title, "JSON-LD headline")
        self.assertEqual(version.description, "JSON-LD description.")
        self.assertEqual(version.author, "JSON-LD author")
        self.assertEqual(
            version.source_updated_at.isoformat(), "2026-07-22T18:00:00+03:00"
        )

    def test_open_graph_title_outranks_a_json_ld_headline(self):
        """og:title is decoded by the HTML parser; a headline may be mis-escaped."""
        html = """
            <html lang="tr"><head>
              <title>Document title</title>
              <meta property="og:title" content="Open Graph title" />
              <script type="application/ld+json">
                {"@type": "NewsArticle", "headline": "JSON-LD headline"}
              </script>
            </head><body><main><p>Görünür paragraf.</p></main></body></html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertEqual(result.article_version.title, "Open Graph title")

    def test_decodes_character_references_inside_json_ld_values(self):
        """JSON-LD sits in a script element, where the parser leaves entities raw."""
        html = """
            <html lang="tr"><head><title>Entities</title>
              <script type="application/ld+json">
                {"@type": "NewsArticle",
                 "description": "&quot;Milli Dayan&#305;&#351;ma&quot; teklifi."}
              </script>
            </head><body><main><p>Görünür paragraf.</p></main></body></html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertEqual(
            result.article_version.description, '"Milli Dayanışma" teklifi.'
        )

    def test_falls_back_to_meta_tags_when_json_ld_omits_a_field(self):
        html = """
            <html lang="tr"><head>
              <title>Meta title</title>
              <meta name="description" content="Meta description." />
              <meta name="author" content="Meta author" />
              <script type="application/ld+json">
                {"@type": "NewsArticle", "headline": "JSON-LD headline"}
              </script>
            </head><body><main><p>Görünür paragraf.</p></main></body></html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertEqual(result.article_version.title, "JSON-LD headline")
        self.assertEqual(result.article_version.description, "Meta description.")
        self.assertEqual(result.article_version.author, "Meta author")

    def test_uses_only_the_document_head_title_and_ignores_svg_titles(self):
        html = """
            <html lang="en">
              <head><title>Real Article Title</title></head>
              <body>
                <svg><title>Search icon</title></svg>
                <article><p>Visible article paragraph.</p></article>
              </body>
            </html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertEqual(result.article_version.title, "Real Article Title")

    def test_prefers_the_article_heading_over_an_unrelated_site_heading(self):
        html = """
            <html lang="en">
              <head></head>
              <body>
                <header><h1>Publisher Site Name</h1></header>
                <article>
                  <h1>The Article Headline</h1>
                  <p>Visible article paragraph.</p>
                </article>
              </body>
            </html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertEqual(result.article_version.title, "The Article Headline")

    def test_uses_the_first_canonical_link_and_ignores_later_or_blank_ones(self):
        html = """
            <html lang="en"><head>
              <title>Canonical precedence</title>
              <link rel="canonical" href="https://news.example.org/first" />
              <link rel="canonical" href="" />
              <link rel="canonical" href="https://news.example.org/second" />
            </head><body><article><p>Visible article paragraph.</p></article></body></html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertEqual(
            result.article.canonical_source, "https://news.example.org/first"
        )

    def test_matches_canonical_rel_as_a_token_rather_than_a_substring(self):
        html = """
            <html lang="en"><head>
              <title>Canonical rel tokens</title>
              <link rel="noncanonical" href="https://wrong.example/ignored" />
              <link rel="Canonical" href="https://news.example.org/story" />
            </head><body><article><p>Visible article paragraph.</p></article></body></html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertEqual(
            result.article.canonical_source, "https://news.example.org/story"
        )

    def test_resolves_a_relative_canonical_href_against_the_source_url(self):
        html = """
            <html lang="en"><head>
              <title>Relative canonical</title>
              <link rel="canonical" href="/story-path" />
            </head><body><article><p>Visible article paragraph.</p></article></body></html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertTrue(result.version_created)
        self.assertEqual(
            result.article.canonical_source, "https://source.example.org/story-path"
        )

    def test_uses_title_time_language_and_canonical_fallbacks(self):
        html = """
            <html>
              <head><title>Fallback article title</title></head>
              <body><main><p>First visible paragraph.</p></main></body>
            </html>
        """
        published_at = datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc)
        raw_article = RawHtmlArticle(
            html=html,
            source_url="https://source.example.org/raw-story",
            publisher="TRT",
            article_type="news_report",
            observed_at=OBSERVED_AT,
            fallback_language="en",
            fallback_published_at=published_at,
        )

        result = self.register.execute(raw_article)

        self.assertEqual(result.article.canonical_source, raw_article.source_url)
        self.assertEqual(result.article.original_language, "en")
        self.assertEqual(result.article_version.title, "Fallback article title")
        self.assertEqual(result.article_version.source_published_at, published_at)

    def test_prefers_json_ld_article_date_published_over_all_lower_priority_sources(self):
        html = """
            <html lang="en"><head>
              <meta property="article:published_time" content="2026-07-22T08:00:00+00:00" />
              <meta name="datePublished" content="2026-07-22T09:00:00+00:00" />
              <script type="application/ld+json">
                {"@context": "https://schema.org", "@type": "NewsArticle",
                 "datePublished": "2026-07-22T10:00:00+03:00"}
              </script>
              <title>JSON-LD precedence</title>
            </head><body><article>
              <time datetime="2026-07-22T11:00:00+00:00"></time>
              <p>Visible article paragraph.</p>
            </article></body></html>
        """
        fallback_published_at = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
        raw_article = RawHtmlArticle(
            html=html,
            source_url="https://source.example.org/json-ld-precedence",
            publisher="TRT",
            article_type="news_report",
            observed_at=OBSERVED_AT,
            fallback_published_at=fallback_published_at,
        )

        result = self.register.execute(raw_article)

        self.assertEqual(
            result.article_version.source_published_at.isoformat(),
            "2026-07-22T10:00:00+03:00",
        )

    def test_prefers_open_graph_then_html_date_published_then_generic_time(self):
        open_graph_html = """
            <html lang="en"><head>
              <meta property="article:published_time" content="2026-07-22T08:00:00+00:00" />
              <meta itemprop="datePublished" content="2026-07-22T09:00:00+00:00" />
              <title>Open Graph precedence</title>
            </head><body><article><time datetime="2026-07-22T10:00:00+00:00"></time>
              <p>Visible article paragraph.</p></article></body></html>
        """
        html_date_published_html = """
            <html lang="en"><head>
              <meta name="datePublished" content="2026-07-22T09:00:00+00:00" />
              <title>HTML metadata precedence</title>
            </head><body><article><time datetime="2026-07-22T10:00:00+00:00"></time>
              <p>Visible article paragraph.</p></article></body></html>
        """

        open_graph = self.register.execute(self.raw_article(open_graph_html))
        html_date_published = self.register.execute(
            RawHtmlArticle(
                html=html_date_published_html,
                source_url="https://source.example.org/html-date-published",
                publisher="TRT",
                article_type="news_report",
                observed_at=OBSERVED_AT,
            )
        )

        self.assertEqual(
            open_graph.article_version.source_published_at.isoformat(),
            "2026-07-22T08:00:00+00:00",
        )
        self.assertEqual(
            html_date_published.article_version.source_published_at.isoformat(),
            "2026-07-22T09:00:00+00:00",
        )

    def test_normalizes_naive_selected_json_ld_date_without_falling_back(self):
        html = """
            <html lang="en"><head>
              <meta property="article:published_time" content="2026-07-22T08:00:00+00:00" />
              <script type="application/ld+json">
                {"@context": "https://schema.org", "@type": "Article",
                 "datePublished": "2026-07-22T10:00:00"}
              </script>
              <title>Invalid JSON-LD date</title>
            </head><body><article><p>Visible article paragraph.</p></article></body></html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertEqual(
            result.article_version.source_published_at.isoformat(),
            "2026-07-22T10:00:00+00:00",
        )

    def test_ingests_paragraphs_from_a_matching_server_supplied_json_payload(self):
        html = """
            <html lang="tr"><head>
              <title>Structured payload article</title>
              <script id="__NEXT_DATA__" type="application/json">
                {"props":{"pageProps":{"content":{
                  "type":"article", "path":"/structured-payload",
                  "body":[
                    {"blockType":"text", "value":"<p>İlk paragraf.</p>"},
                    {"blockType":"image", "value":"<figure>Görsel açıklaması</figure>"},
                    {"blockType":"text", "value":"<p>İkinci paragraf.</p>"}
                  ]
                }}}}
              </script>
            </head><body><article></article></body></html>
        """
        raw_article = RawHtmlArticle(
            html=html,
            source_url="https://source.example.org/structured-payload",
            publisher="TRT",
            article_type="news_report",
            observed_at=OBSERVED_AT,
            fallback_published_at=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc),
        )

        result = self.register.execute(raw_article)

        self.assertEqual(
            result.article_version.body, "İlk paragraf.\n\nİkinci paragraf."
        )
        self.assertEqual(
            [passage.text for passage in result.passages],
            ["İlk paragraf.", "İkinci paragraf."],
        )

    def test_does_not_use_an_unrelated_json_article_payload(self):
        html = """
            <html lang="tr"><head><title>Unrelated payload</title>
              <script type="application/json">
                {"type":"article", "path":"/another-article",
                 "body":[{"value":"<p>Unrelated content.</p>"}]}
              </script>
            </head><body><article></article></body></html>
        """
        raw_article = RawHtmlArticle(
            html=html,
            source_url="https://source.example.org/current-article",
            publisher="TRT",
            article_type="news_report",
            observed_at=OBSERVED_AT,
            fallback_published_at=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc),
        )

        with self.assertRaisesRegex(
            DomainValidationError, "raw article html has no visible paragraphs"
        ):
            self.register.execute(raw_article)

    def test_reprocessing_identical_html_is_idempotent(self):
        html = """
            <html lang="en"><head>
              <title>Stable story</title>
              <meta name="datePublished" content="2026-07-22T08:00:00+00:00" />
            </head><body><article><p>Stable body.</p></article></body></html>
        """

        first = self.register.execute(self.raw_article(html))
        replay = self.register.execute(self.raw_article(html))

        self.assertTrue(first.version_created)
        self.assertFalse(replay.version_created)
        self.assertEqual(first.article_version.article_version_id, replay.article_version.article_version_id)

    def test_rejects_html_without_visible_article_paragraphs(self):
        html = """
            <html lang="tr"><head>
              <title>Title</title>
              <meta property="article:published_time" content="2026-07-22T08:00:00+00:00" />
            </head><body><script>Not article text.</script></body></html>
        """

        with self.assertRaises(DomainValidationError):
            self.register.execute(self.raw_article(html))

    def test_ingests_html_without_source_time_and_preserves_missing_publication_date(self):
        html = """
            <html lang="tr"><head><title>Title</title></head>
            <body><article><p>Visible paragraph.</p></article></body></html>
        """

        result = self.register.execute(self.raw_article(html))

        self.assertTrue(result.version_created)
        self.assertIsNone(result.article.initial_published_at)
        self.assertIsNone(result.article_version.source_published_at)


if __name__ == "__main__":
    unittest.main()
