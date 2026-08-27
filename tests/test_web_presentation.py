import json
import re
import sys
import unittest
from hashlib import sha256
from pathlib import Path

sys.path.insert(0, "src")

from fastapi.testclient import TestClient  # noqa: E402

from aether.presentation.web.app import create_app  # noqa: E402
from aether.application.ingestion.prepare_draft import prepare_draft  # noqa: E402

from tests.page_script import run_page_script  # noqa: E402


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "trt_world_erdogan_kazakhstan.html"
AA_NAIVE_MODIFIED_FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "aa_naive_date_modified.html"
)


class StubHtmlFetcher:
    def __init__(self, html: str) -> None:
        self.html = html
        self.urls = []

    def fetch(self, url: str) -> str:
        self.urls.append(url)
        return self.html


class WebPresentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.html = FIXTURE_PATH.read_text(encoding="utf-8")
        self.fetcher = StubHtmlFetcher(self.html)
        self.client = TestClient(create_app(self.fetcher))

    def test_index_offers_a_published_article_and_a_draft_flow(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-endpoint="/analyze/url"', response.text)
        self.assertIn('data-endpoint="/analyze/draft"', response.text)
        self.assertIn("Yayınlanmamış içeriği kontrol et", response.text)
        self.assertIn('id="assessment-grid"', response.text)
        self.assertIn('id="report"', response.text)

    def test_the_editor_ui_no_longer_asks_for_a_saved_html_file(self):
        """Nobody in an editorial workflow has one; the endpoint stays for tests."""
        response = self.client.get("/")

        self.assertNotIn('data-endpoint="/analyze/file"', response.text)
        self.assertNotIn("Upload HTML", response.text)

    def test_index_leads_with_the_editor_workflow_and_hides_advanced_comparison(self):
        page = self.client.get("/").text

        self.assertIn("İçeriğinizin SEO ve AI görünürlüğünü ölçün", page)
        self.assertIn("Yayındaki sayfayı kontrol et", page)
        self.assertIn("Yayınlanmamış içeriği kontrol et", page)
        self.assertIn('id="draft-tab" type="button" aria-controls="draft-fields" aria-expanded="false"', page)
        self.assertIn('<summary>Gelişmiş seçenekler</summary>', page)

    def test_published_result_information_architecture_is_summary_first(self):
        page = self.client.get("/").text

        labels = [
            "Analiz Sonucu",
            "SEO Skoru",
            "SEO Detayları",
            "GEO Skoru",
            "GEO Detayları",
            "Öneriler",
            "Analiz Edilen Metni Gör",
            "Teknik detaylar",
        ]
        positions = [page.index(label) for label in labels]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("En önemli 3 iyileştirme", page)
        self.assertNotIn("Tüm önerileri göster", page)
        self.assertNotIn("Tüm detayları göster", page)

    def test_each_score_owns_its_visible_dimension_grid(self):
        page = self.client.get("/").text

        seo_card = page[page.index('id="seo-summary-card"'):page.index('id="geo-summary-card"')]
        geo_card = page[page.index('id="geo-summary-card"'):page.index("<!-- BİTİŞ")]
        self.assertIn('id="seo-score-grid"', seo_card)
        self.assertNotIn('id="geo-score-grid"', seo_card)
        self.assertIn('id="geo-score-grid"', geo_card)
        self.assertNotIn('class="collapsible-panel hidden"', seo_card + geo_card)

    def test_dimension_and_signal_names_are_turkish_first_with_technical_secondary_text(self):
        page = self.client.get("/").text

        for key, friendly in (
            ("entity_coverage", "Varlık Kapsamı"),
            ("semantic_quality", "Anlamsal Kalite"),
            ("entity_authority", "Kaynak ve Güvenilirlik"),
            ("semantic_completeness", "İçerik Bütünlüğü"),
        ):
            self.assertIn(f"{key}: '{friendly}'", page)
        for technical, friendly in (
            ("Publication date", "Yayın tarihi"),
            ("Declared expected properties", "Tanımlanan alanlar"),
            ("Citation coverage", "Kaynaklandırma kapsamı"),
        ):
            self.assertIn(f"'{technical}': '{friendly}'", page)
        self.assertIn('class="technical-name"', page)
        self.assertIn('class="signal-technical-name"', page)

    def test_score_meaning_colors_remain_independent_from_burgundy_theme(self):
        page = self.client.get("/").text

        self.assertIn("background: #B4232F", page)
        self.assertIn(".score-good .score-total", page)
        self.assertIn("color: #167448", page)
        self.assertIn(".score-warn .score-total", page)
        self.assertIn("color: #a66100", page)
        self.assertIn(".score-low .score-total", page)

    def test_all_recommendation_categories_share_one_visible_section(self):
        page = self.client.get("/").text
        section = page[page.index('id="recommendations-heading"'):page.index('id="analysed-text-heading"')]

        self.assertIn('id="editor-list"', section)
        self.assertIn('id="technical-list"', section)
        self.assertIn("İçerikte Yapılabilecekler", section)
        self.assertIn("Teknik / Site Düzeyinde Yapılabilecekler", section)
        self.assertNotIn("hidden", section)

    def test_published_recommendations_are_fully_turkish_at_the_web_boundary(self):
        view = self._analysed_view()
        recommendations = (
            (view["editor"] or {"recommendations": []})["recommendations"]
            + (view["technical"] or {"recommendations": []})["recommendations"]
        )
        self.assertTrue(recommendations)
        self.assertIn("Bu öneriler sayfa şablonu veya CMS üzerinde", view["technical"]["subtitle"])

        combined = " ".join(
            value
            for item in recommendations
            for value in (item["headline"], item["what_to_do"], item["why_it_matters"])
        ).lower()
        for fragment in ("your article", "what to do", "why it matters", "things that need"):
            self.assertNotIn(fragment, combined)
        self.assertTrue(all(item["impact"] != "Structured Data" for item in recommendations))

    def test_draft_result_copy_does_not_reintroduce_english_guidance(self):
        draft = self._draft("# Başlık\n\nKısa taslak.", publisher="").json()["draft"]
        combined = " ".join(
            draft["checks_performed"]
            + draft["checks_unavailable"]
            + [
                text
                for item in draft["recommendations"]
                for text in (item["headline"], item["what_to_do"], item["why_it_matters"])
            ]
        ).lower()
        for fragment in ("your article", "publication date", "heading structure", "what to do"):
            self.assertNotIn(fragment, combined)

    def test_the_editor_ui_no_longer_shows_controls_that_do_nothing(self):
        """Content type never reached an analysis; publisher is derived."""
        response = self.client.get("/")

        self.assertNotIn("article_type_override", response.text)
        self.assertNotIn("Content type", response.text)
        self.assertNotIn("Publisher override", response.text)

    def test_recovery_fields_use_human_controls_not_iso_timestamps(self):
        response = self.client.get("/")

        self.assertNotIn("2026-05-14T14:00:00+03:00", response.text)
        self.assertIn('name="fallback_published_at" type="date"', response.text)
        self.assertIn('<select name="fallback_language">', response.text)

    def _draft(self, content, headline="", publisher="TRT Çocuk"):
        return self.client.post(
            "/analyze/draft",
            data={"content": content, "headline": headline,
                  "language": "tr", "publisher": publisher},
        )

    def test_a_draft_never_reports_published_page_fields(self):
        """A draft has no metadata, identity or structured data to be missing."""
        response = self._draft("<h1>Başlık</h1><p>Bir paragraf.</p>")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(list(body), ["draft"])
        draft = body["draft"]
        # Naming a check as unavailable is correct; reporting a page field as
        # missing, or carrying page-level structure at all, is not.
        self.assertNotIn("metadata", json.dumps(draft["recommendations"]).lower())
        for absent in ("article_id", "identity", "assessment", "metadata_completeness"):
            self.assertNotIn(absent, json.dumps(draft).lower())
        self.assertNotIn("missing", " ".join(draft["checks_unavailable"]).lower())

    def test_a_draft_uses_the_heading_from_the_pasted_markup(self):
        response = self._draft("<h1>Ekran süresi</h1><p>Bir paragraf.</p>")

        self.assertEqual(response.json()["draft"]["headline"], "Ekran süresi")

    def test_a_draft_without_a_heading_asks_for_the_headline(self):
        """Never invented, and never taken from the first paragraph."""
        response = self._draft("<p>Bu ilk paragraftır.</p><p>İkinci.</p>")

        self.assertEqual(response.status_code, 422)
        self.assertIn("başlığı girin", response.json()["detail"])

    def test_a_supplied_headline_is_used_when_the_paste_has_no_heading(self):
        response = self._draft("<p>Bir paragraf.</p>", headline="Editörün başlığı")

        self.assertEqual(response.json()["draft"]["headline"], "Editörün başlığı")

    def test_a_draft_with_its_own_heading_is_not_given_a_second_one(self):
        """Injecting one made every such draft look like it had two."""
        response = self._draft("<h1>Başlık</h1><p>Bir paragraf.</p>", headline="Başka")
        findings = " ".join(
            r["headline"] for r in response.json()["draft"]["recommendations"]
        )

        self.assertNotIn("birden fazla ana başlık", findings)

    def test_a_draft_with_several_top_level_headings_is_reported(self):
        response = self._draft("<h1>Bir</h1><p>M.</p><h1>İki</h1><p>N.</p>")
        draft = response.json()["draft"]
        findings = " ".join(r["headline"] for r in draft["recommendations"])
        details = json.dumps(draft["recommendations"], ensure_ascii=False)

        self.assertIn("birden fazla ana başlık", findings)
        self.assertIn("başlık ana başlık olarak kullanılmış", details)
        self.assertNotIn("başka makale", details)

    def test_a_plain_text_draft_says_headings_could_not_be_checked(self):
        response = self._draft(
            "Bir paragraf.\n\nİkinci paragraf.", headline="Editörün başlığı"
        )
        draft = response.json()["draft"]

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Başlık yapısı", draft["checks_performed"])
        self.assertTrue(
            any("biçimlendirme içermediği" in c for c in draft["checks_unavailable"])
        )

    def test_markdown_draft_preserves_atx_outline_and_paragraphs(self):
        content = """# Çocuk İçin Belgeseller ve Sinema Filmleri

Intro paragraph one.

Intro paragraph two.

## Doğa ve Hayvanlar Üzerine Belgeseller

### Our Planet – Gezegenimiz

Passage.

### Inside the Mind of a Cat

Passage.

## Duygular Üzerine Filmler

### Inside Out

Passage."""
        draft = self._draft(content, publisher="").json()["draft"]

        self.assertEqual(draft["paragraph_count"], 5)
        # Heading text and its Markdown markers are outside passage word count.
        self.assertEqual(draft["word_count"], 9)
        self.assertIn("Başlık yapısı", draft["checks_performed"])
        self.assertFalse(
            any("biçimlendirme içermediği" in item for item in draft["checks_unavailable"])
        )

    def test_clipboard_fragment_excludes_the_183_paragraph_wrapper(self):
        """The rich clipboard wrapper, not passage collection, caused 183."""
        words = [f"word{i}" for i in range(343)]
        article_paragraphs = [
            " ".join(words[index * 31 : (index + 1) * 31])
            for index in range(10)
        ] + [" ".join(words[310:])]
        fragment = (
            "<h1>Çocuk İçin Belgeseller ve Sinema Filmleri</h1>"
            + "".join(f"<p>{paragraph}</p>" for paragraph in article_paragraphs)
        )
        contaminating_words = " ".join(f"chrome{i}" for i in range(1128))
        wrapper_paragraphs = "".join(
            f"<p>{part}</p>" for part in (
                " ".join(contaminating_words.split()[index * 6 : (index + 1) * 6])
                for index in range(171)
            )
        ) + f"<p>{' '.join(contaminating_words.split()[1026:])}</p>"
        clipboard_html = (
            "<html><head><style>p { color: red; }</style>"
            "<script>window.unrelated = true;</script></head><body>"
            + wrapper_paragraphs
            + "<!--StartFragment-->"
            + fragment
            + "<!--EndFragment--><div>footer contamination</div></body></html>"
        )

        # Before fragment precedence this exact payload exposed 183 wrapper +
        # article paragraphs and 1471 corresponding words to ingestion.
        self.assertEqual(clipboard_html.count("<p>"), 183)
        unbounded_html = clipboard_html.replace("<!--StartFragment-->", "").replace(
            "<!--EndFragment-->", ""
        )
        inflated = self._draft(unbounded_html, publisher="").json()["draft"]
        self.assertEqual(inflated["paragraph_count"], 183)
        self.assertEqual(inflated["word_count"], 1471)

        prepared = prepare_draft(clipboard_html, "", "tr")
        self.assertNotIn("chrome0", prepared.html)
        self.assertNotIn("window.unrelated", prepared.html)
        self.assertNotIn("footer contamination", prepared.html)

        draft = self._draft(clipboard_html, publisher="").json()["draft"]
        self.assertEqual(draft["paragraph_count"], 11)
        self.assertEqual(draft["word_count"], 343)

    def test_draft_previews_preserve_unmeasured_dimensions_as_null(self):
        draft = self._draft(
            "# Başlık\n\nİlk paragraf.\n\n## Bölüm\n\nİkinci paragraf.",
            publisher="",
        ).json()["draft"]

        seo = draft["seo_preview"]
        geo = draft["geo_preview"]
        self.assertIsNone(seo["total"])
        for key in ("entity_coverage", "structured_data", "semantic_quality", "technical_access"):
            self.assertIsNone(seo[key]["val"])
            self.assertNotEqual(seo[key]["val"], 0.0)
            self.assertTrue(
                all(signal["value"] is None for signal in seo[key]["detail"]["signals"])
            )
        self.assertIsNotNone(geo["total"])
        self.assertIsNone(geo["discoverability"]["val"])
        self.assertNotEqual(geo["discoverability"]["val"], 0.0)

        measured = [geo[key] for key in (
            "semantic_completeness", "entity_authority", "structural_richness",
            "discoverability",
        ) if geo[key]["val"] is not None]
        expected = round(
            sum(item["val"] * item["weight"] / 100.0 for item in measured)
            / (sum(item["weight"] for item in measured) / 100.0)
        )
        self.assertEqual(geo["total"], expected)

    def test_draft_seo_preview_uses_measurable_corpus_comparison(self):
        pipeline = self.client.app.state.pipeline
        pipeline.analyze_report(
            self.html,
            "https://trt.example/published",
            "TRT Çocuk",
            "news_report",
        )
        review = pipeline.analyze_draft(
            "# Yeni başlık\n\nÖzgün bir giriş paragrafı.\n\n## Bölüm\n\nÖzgün devam paragrafı.",
            "",
            "tr",
            "TRT Çocuk",
        )

        self.assertEqual(review.seo_preview.semantic_quality.dimension_score, 100.0)
        self.assertEqual(review.seo_preview.total, 100)
        self.assertIsNone(review.seo_preview.entity_coverage.dimension_score)
        self.assertIsNone(review.seo_preview.structured_data.dimension_score)
        self.assertIsNone(review.seo_preview.technical_access.dimension_score)

    def test_draft_result_page_labels_scores_as_previews(self):
        page = self.client.get("/").text

        self.assertIn("SEO Önizleme", page)
        self.assertIn("GEO Önizleme", page)
        self.assertIn("yalnızca yayınlanmadan önce ölçülebilen sinyallere", page)
        self.assertIn("Yayınlandıktan sonra ölçülebilecekler", page)
        self.assertIn("Henüz ölçülemiyor", page)

    def test_an_empty_draft_is_refused_with_an_editor_facing_message(self):
        response = self._draft("", headline="Bir başlık")

        self.assertEqual(response.status_code, 422)
        detail = response.json()["detail"].lower()
        for jargon in ("paragraph tag", "raw article", "parser", "none"):
            self.assertNotIn(jargon, detail)

    def test_a_draft_lists_what_needs_the_published_page(self):
        draft = self._draft("<h1>Başlık</h1><p>Bir paragraf.</p>").json()["draft"]
        unavailable = " ".join(draft["checks_unavailable"]).lower()

        self.assertIn("yayın tarihi", unavailable)
        self.assertIn("schema.org", unavailable)
        self.assertNotIn("missing", unavailable)

    def test_a_draft_is_never_compared_against_another_draft(self):
        """An unpublished draft is not part of what a publisher has published."""
        first = self._draft("<h1>Bir</h1><p>Paylaşılan bir paragraf.</p>", publisher="TRT")
        second = self._draft("<h1>İki</h1><p>Paylaşılan bir paragraf.</p>", publisher="TRT")

        self.assertEqual(second.json()["draft"]["compared_article_count"], 0)
        findings = " ".join(
            r["headline"] for r in second.json()["draft"]["recommendations"]
        )
        self.assertNotIn("appears in your other articles", findings)

    def test_the_draft_template_reads_only_fields_the_draft_response_sends(self):
        """The seam where the last two regressions lived."""
        template = self._template()
        draft = self._draft("<h1>Başlık</h1><p>Bir paragraf.</p>").json()["draft"]
        referenced = set(re.findall(r"\bdraft\.([a-z_]+)", template))

        missing = sorted(referenced - set(draft))
        self.assertEqual(missing, [], f"template reads {missing} which the draft omits")

    def _submit_handler(self):
        template = self._template()
        begin = template.index("form.addEventListener('submit'")
        return template[begin : template.index("\n        });", begin)]

    def test_the_loading_state_is_cleared_in_finally(self):
        """A draft rendered its result beneath a stale "Analyzing article…".

        The clear sat on one success path and the draft branch returned before
        reaching it. Asserted structurally, so a branch added later cannot
        skip it: the loading text is cleared where the button is re-enabled.
        """
        handler = self._submit_handler()

        finally_block = handler[handler.index("finally {") :]
        self.assertIn("status.textContent", finally_block)
        self.assertIn("button.disabled = false", finally_block)

    def test_the_loading_state_is_not_cleared_on_a_single_success_path(self):
        """Clearing it inline is how the draft branch came to bypass it."""
        handler = self._submit_handler()

        self.assertNotIn("status.textContent = '';", handler)

    def test_a_successful_draft_leaves_no_loading_message(self):
        """The draft branch returns early, so the clear must survive a return."""
        response = self._draft("<h1>Başlık</h1><p>Bir paragraf.</p>")
        self.assertEqual(response.status_code, 200)

        handler = self._submit_handler()
        draft_branch = handler[handler.index("if (data.draft) {") : handler.index("if (data.outcome)")]

        self.assertIn("return;", draft_branch)
        self.assertNotIn("status.textContent", draft_branch)

    def test_drafts_are_not_offered_as_something_to_compare_against(self):
        self.client.post(
            "/analyze/draft",
            data={"content": "<p>Bir paragraf.</p>", "headline": "Başlık",
                  "language": "tr", "publisher": "Taslaklar"},
        )

        names = self.client.get("/publishers").json()["publishers"]

        self.assertNotIn("Taslaklar", names)

    def test_published_trt_url_populates_same_process_corpus_then_draft_uses_it(self):
        """One published article is enough; only an app restart loses it."""
        source_url = (
            "https://ebeveynakademisi.trtcocuk.net.tr/makale/"
            "cocuk-icin-belgeseller-ve-sinema-filmleri-29038861"
        )
        html = (
            Path(__file__).parent / "fixtures" / "trt_ebeveyn_belgeseller_nuxt.html"
        ).read_text(encoding="utf-8")
        app = create_app(StubHtmlFetcher(html))
        client = TestClient(app)

        self.assertEqual(client.get("/publishers").json()["publishers"], [])
        published = client.post("/analyze/url", data={"url": source_url})
        self.assertEqual(published.status_code, 200)
        passage_details = published.json()["view"]["passage_details"]
        expected_word_counts = [33, 8, 43, 3, 34, 5, 41, 75, 3, 95, 3]
        self.assertEqual(passage_details["passage_count"], 11)
        self.assertEqual(passage_details["word_count"], 343)
        self.assertEqual(
            [passage["position"] for passage in passage_details["passages"]],
            list(range(1, 12)),
        )
        self.assertEqual(
            [passage["word_count"] for passage in passage_details["passages"]],
            expected_word_counts,
        )
        self.assertEqual(sum(expected_word_counts), passage_details["word_count"])
        extracted_text = "\n".join(
            passage["text"] for passage in passage_details["passages"]
        )
        self.assertIn("Bilimsel verilere dayanan Our Planet", extracted_text)
        for excluded in (
            "24 Aralık 2025",
            "TRT Çocuk\n",
            "Önemli Hatırlatma",
            "Hazırlayan:",
            "AİLECE İZLENECEK",
        ):
            self.assertNotIn(excluded, extracted_text)
        publisher = "ebeveynakademisi.trtcocuk.net.tr"
        self.assertEqual(client.get("/publishers").json()["publishers"], [publisher])

        repository = app.state.pipeline.repository
        version_id = published.json()["view"]["identity"]["article_version_id"]
        shared = repository.list_passages_for_version(
            version_id
        )[0].text
        content = f"# Yeni taslak\n\n{shared}"
        standalone_response = client.post(
            "/analyze/draft",
            data={
                "content": content,
                "headline": "",
                "language": "tr",
                "publisher": "",
            },
        )
        self.assertEqual(standalone_response.status_code, 200)
        standalone = standalone_response.json()["draft"]

        compared_response = client.post(
            "/analyze/draft",
            data={
                "content": content,
                "headline": "",
                "language": "tr",
                "publisher": publisher,
            },
        )
        self.assertEqual(compared_response.status_code, 200)
        draft = compared_response.json()["draft"]

        self.assertEqual(draft["paragraph_count"], standalone["paragraph_count"])
        self.assertEqual(draft["word_count"], standalone["word_count"])
        self.assertIsNone(standalone["seo_preview"]["semantic_quality"]["val"])
        self.assertEqual(draft["compared_article_count"], 1)
        self.assertEqual(draft["seo_preview"]["semantic_quality"]["val"], 0.0)
        self.assertEqual(draft["seo_preview"]["total"], 0)
        self.assertTrue(
            any(
                "diğer makalelerinizde de yer alıyor" in item["headline"]
                for item in draft["recommendations"]
            )
        )

        # create_app owns the repository. Development --reload creates a new
        # app and therefore an intentionally empty process-scoped corpus.
        restarted = TestClient(create_app(StubHtmlFetcher(html)))
        self.assertEqual(restarted.get("/publishers").json()["publishers"], [])

    def test_url_submission_fetches_html_and_returns_existing_plain_text_report(self):
        response = self.client.post(
            "/analyze/url",
            data={"url": "https://www.trtworld.com/article/3e946db45c45"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.fetcher.urls, ["https://www.trtworld.com/article/3e946db45c45"])
        report = response.json()["report"]
        self.assertIn("AI Readiness Report", report)
        self.assertIn("Metadata Completeness: complete", report)
        self.assertNotIn("raw_html", report)
        self.assertEqual(response.json()["view"]["assessment"]["metadata"], "complete")
        self.assertNotIn("article_id", response.json()["view"])

    def test_file_submission_returns_existing_plain_text_report(self):
        response = self.client.post(
            "/analyze/file",
            data={},
            files={"file": ("article.html", self.html, "text/html")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Metadata Completeness: complete", response.json()["report"])

    def test_aa_style_naive_json_ld_modified_date_still_produces_a_report(self):
        html = AA_NAIVE_MODIFIED_FIXTURE_PATH.read_text(encoding="utf-8")

        response = self.client.post(
            "/analyze/file",
            data={},
            files={"file": ("aa.html", html, "text/html")},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNotNone(payload["report"])
        self.assertIn("Last Modified Date Available: False", payload["report"])
        metadata = {
            field["label"]: field["available"]
            for field in payload["view"]["metadata"]
        }
        self.assertTrue(metadata["Publication date"])
        self.assertFalse(metadata["Last modified date"])
        semantic_signals = {
            signal["label"]: signal["value"]
            for signal in payload["view"]["assessment"]["geo_score"][
                "semantic_completeness"
            ]["detail"]["signals"]
        }
        self.assertNotIn("Direct answer coverage", semantic_signals)
        self.assertEqual(
            payload["view"]["direct_answer_coverage"]["ratio"], 1.0
        )
        self.assertFalse(
            payload["view"]["direct_answer_coverage"]["included_in_score"]
        )

    def test_file_submission_requires_source_url_only_when_canonical_is_absent(self):
        html = """
            <html lang="en"><head><title>No canonical URL</title></head>
            <body><article><p>Visible article content.</p></article></body></html>
        """

        response = self.client.post(
            "/analyze/file",
            data={},
            files={"file": ("article.html", html, "text/html")},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "canonical URL bulunamadığı için HTML dosyası bir kaynak URL gerektirir.",
        )

    def test_file_submission_resolves_the_same_canonical_link_as_ingestion(self):
        html = """
            <html lang="en"><head><title>Canonical agreement</title>
              <link rel="canonical" href="https://news.example.org/first" />
              <link rel="canonical" href="https://news.example.org/second" />
            </head><body><article><p>Visible article content.</p></article></body></html>
        """
        expected_article_id = "article_" + sha256(
            b"https://news.example.org/first"
        ).hexdigest()

        response = self.client.post(
            "/analyze/file",
            data={},
            files={"file": ("article.html", html, "text/html")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(f"Article ID: {expected_article_id}", response.json()["report"])

    def test_file_submission_requires_a_source_url_for_a_relative_canonical(self):
        html = """
            <html lang="en"><head><title>Relative canonical</title>
              <link rel="canonical" href="/story-path" />
            </head><body><article><p>Visible article content.</p></article></body></html>
        """

        response = self.client.post(
            "/analyze/file",
            data={},
            files={"file": ("article.html", html, "text/html")},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "canonical URL bulunamadığı için HTML dosyası bir kaynak URL gerektirir.",
        )

    def test_page_shell_is_not_cached_so_it_cannot_outlive_the_payload(self):
        """A cached shell running against a newer payload broke the report."""
        response = self.client.get("/")

        self.assertEqual(response.headers["cache-control"], "no-store")

    def _template(self):
        return (
            Path(__file__).parent.parent
            / "src/aether/presentation/web/templates/index.html"
        ).read_text(encoding="utf-8")

    def _analysed_view(self):
        response = self.client.post(
            "/analyze/url",
            data={"url": "https://www.trtworld.com/article/3e946db45c45"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["view"]

    def test_entity_authority_detail_is_exposed_from_report_signals(self):
        entity_authority = self._analysed_view()["assessment"]["geo_score"][
            "entity_authority"
        ]
        detail = entity_authority["detail"]

        self.assertEqual(detail["label"], "Entity Authority")
        self.assertEqual(detail["dimension_score"], entity_authority["val"])
        self.assertEqual(
            [signal["label"] for signal in detail["signals"]],
            [
                "Author declaration",
                "Outbound body sources",
                "Trust index",
                "Third-party source ratio",
                "Supported entities",
                "Citation coverage",
                "Claim evidence coverage",
            ],
        )

    def test_all_geo_dimension_details_are_exposed_from_report_signals(self):
        geo_score = self._analysed_view()["assessment"]["geo_score"]

        self.assertEqual(
            [
                signal["label"]
                for signal in geo_score["semantic_completeness"]["detail"]["signals"]
            ],
            [
                "Statistics coverage",
                "Heading-passage overlap",
                "Sentence balance",
                "Structural variety",
            ],
        )
        self.assertEqual(
            [
                signal["label"]
                for signal in geo_score["structural_richness"]["detail"]["signals"]
            ],
            [
                "Table word share",
                "List word share",
                "Blockquote word share",
                "Structured content ratio",
                "Answered question ratio",
            ],
        )
        self.assertEqual(
            [
                signal["label"]
                for signal in geo_score["discoverability"]["detail"]["signals"]
            ],
            ["Body link saturation", "Unique target ratio"],
        )

    def test_all_score_cards_have_accessible_toggles_and_detail_rows(self):
        template = self._template()
        self.assertIn("data-score-detail-toggle", template)
        self.assertIn('aria-expanded="false"', template)
        self.assertIn('aria-controls="${detailId}"', template)

        view = self._analysed_view()
        dom = run_page_script(
            f"renderReport({json.dumps(view)}, 'report');"
        )
        rendered = dom["#geo-score-grid"]["html"]
        self.assertEqual(rendered.count('aria-expanded="false"'), 4)
        self.assertEqual(rendered.count("aria-controls="), 4)
        self.assertEqual(rendered.count("Detayları gör"), 4)
        self.assertIn("Semantic Completeness", rendered)
        self.assertIn("Entity Authority", rendered)
        self.assertIn("Structural Richness", rendered)
        self.assertIn("Discoverability", rendered)
        geo_details = dom["#geo-details"]["html"]
        self.assertEqual(geo_details.count("dimension-detail-panel hidden"), 4)
        for label in (
            "Statistics coverage", "Author declaration", "Citation coverage",
            "Claim evidence coverage", "Structured content ratio", "Body link ratio",
        ):
            self.assertIn(label, geo_details)
        self.assertIn("Henüz ölçülemiyor", geo_details)

        seo_rendered = dom["#seo-score-grid"]["html"]
        self.assertEqual(seo_rendered.count('aria-expanded="false"'), 4)
        self.assertEqual(seo_rendered.count("aria-controls="), 4)
        self.assertEqual(seo_rendered.count("Detayları gör"), 4)
        seo_details = dom["#seo-details"]["html"]
        for label in (
            "Publication date", "Last modified date", "Author", "Description",
            "Article structured data", "Declared expected properties",
            "Missing expected properties", "Property coverage", "Total passages",
            "Unique passages", "Repeated passages", "Unique passage ratio",
            "Title sources disagree", "Description sources disagree",
        ):
            self.assertIn(label, seo_details)

    def test_draft_score_cards_use_unique_matching_detail_targets(self):
        draft = self._draft(
            "# Başlık\n\nGiriş.\n\n## Bölüm\n\nİkinci paragraf.",
            publisher="",
        ).json()["draft"]
        self.assertTrue(draft["geo_preview"]["semantic_completeness"]["detail"]["signals"])
        self.assertTrue(draft["geo_preview"]["entity_authority"]["detail"]["signals"])
        self.assertTrue(draft["geo_preview"]["structural_richness"]["detail"]["signals"])
        self.assertTrue(draft["geo_preview"]["discoverability"]["detail"]["signals"])

        template = self._template()
        self.assertIn("renderDimensionGroup(score, dimensions, `draft-${kind}`)", template)
        self.assertIn("`${scoreType}-${dimension.key.replaceAll('_', '-')}-detail`", template)
        self.assertIn('aria-controls="${detailId}"', template)
        self.assertIn('id="${detailId}" class="dimension-detail-panel hidden"', template)
        self.assertIn("document.addEventListener('click'", template)
        self.assertIn("event.target.closest('[data-score-detail-toggle]')", template)
        self.assertNotIn("querySelectorAll('[data-score-detail-toggle]').forEach", template)

    def test_passage_details_use_shared_accessible_toggle_contract(self):
        template = self._template()

        self.assertIn('type="button"', template)
        self.assertIn('aria-controls="passage-details-panel"', template)
        self.assertIn('id="passage-details-panel" class="geo-dimension-detail hidden"', template)
        self.assertIn('data-score-detail-toggle aria-expanded="false"', template)
        self.assertIn("passage.word_count", template)
        self.assertIn("escapeHtml(passage.text)", template)

    def test_compact_score_grids_keep_detail_panels_outside_cards(self):
        template = self._template()

        self.assertIn(".dimension-grid { align-items: stretch", template)
        self.assertIn("min-height: 174px", template)
        self.assertIn("min-width: 0", template)
        self.assertIn('class="dimension-detail-panel hidden"', template)
        self.assertIn('class="dimension-detail-stack"', template)
        self.assertIn("overflow-wrap: normal", template)
        self.assertIn("word-break: normal", template)
        self.assertNotIn("overflow-wrap: anywhere", template)
        self.assertNotIn("word-break: break-word", template)
        self.assertIn("white-space: normal", template)
        self.assertIn("flex-direction: column", template)
        self.assertIn("geo-signal-row-stacked", template)

    def test_long_structured_data_value_remains_complete_in_card_html(self):
        long_value = (
            "author, dateModified, datePublished, description, headline, image, "
            "mainEntityOfPage, publisher"
        )
        dimension = {
            "key": "structured_data",
            "val": 100.0,
            "label": "Yapısal Veri",
            "weight": 25,
            "detail": {
                "label": "Structured Data",
                "dimension_score": 100.0,
                "signals": [
                    {
                        "label": "Declared expected properties",
                        "value": long_value,
                        "explanation": "Existing score inputs",
                    }
                ],
            },
        }

        dom = run_page_script(
            "document.querySelector('#long-card').innerHTML = "
            f"scoreDimensionCard({json.dumps(dimension)}, 'seo');"
            "document.querySelector('#long-detail').innerHTML = "
            f"scoreDimensionDetail({json.dumps(dimension)}, 'seo');"
        )
        card_rendered = dom["#long-card"]["html"]
        rendered = dom["#long-detail"]["html"]
        self.assertNotIn(long_value, card_rendered)
        self.assertIn("8 / 8 mevcut", rendered)
        self.assertIn("Tam liste", rendered)
        self.assertIn(long_value, rendered)
        for identifier in (
            "dateModified",
            "datePublished",
            "mainEntityOfPage",
        ):
            self.assertIn(identifier, rendered)
        self.assertIn("geo-signal-row-stacked", rendered)
        self.assertIn('aria-expanded="false"', card_rendered)
        self.assertIn("aria-controls=", card_rendered)

    def test_short_signal_value_keeps_compact_row_markup(self):
        dimension = {
            "key": "technical_access",
            "val": 100.0,
            "label": "Teknik Erişim",
            "weight": 20,
            "detail": {
                "label": "Technical Access",
                "dimension_score": 100.0,
                "signals": [
                    {
                        "label": "Title sources disagree",
                        "value": "No",
                        "explanation": "Existing score input",
                    }
                ],
            },
        }

        dom = run_page_script(
            "document.querySelector('#short-signal').innerHTML = "
            f"scoreDimensionDetail({json.dumps(dimension)}, 'seo');"
        )
        rendered = dom["#short-signal"]["html"]
        self.assertIn('class="geo-signal-row"', rendered)
        self.assertNotIn("geo-signal-row-stacked", rendered)

    def test_technical_access_web_detail_matches_consistency_score(self):
        html = """
            <html lang="tr"><head>
              <title>Birinci başlık</title>
              <meta property="og:title" content="Tamamen farklı başlık">
              <meta name="description" content="Birinci açıklama">
              <meta property="og:description" content="Tamamen farklı açıklama">
            </head><body><main><p>Özgün paragraf.</p></main></body></html>
        """
        response = self.client.post(
            "/analyze/file",
            data={"source_url": "https://example.com/tutarsiz"},
            files={"file": ("article.html", html, "text/html")},
        )

        self.assertEqual(response.status_code, 200)
        technical = response.json()["view"]["assessment"]["seo_score"][
            "technical_access"
        ]
        signals = {
            signal["label"]: signal["value"]
            for signal in technical["detail"]["signals"]
        }
        self.assertEqual(technical["val"], 0.0)
        self.assertEqual(
            signals,
            {
                "Title sources disagree": "Yes",
                "Description sources disagree": "Yes",
            },
        )

    def test_passage_extractability_is_a_separate_unscored_diagnostic(self):
        view = self._analysed_view()
        diagnostic = view["passage_extractability"]

        self.assertEqual(
            [band["bound"] for band in diagnostic["bands"]],
            [128, 256, 512],
        )
        self.assertFalse(diagnostic["included_in_score"])
        self.assertNotIn(
            "passage_extractability", view["assessment"]["geo_score"]
        )

        template = self._template()
        self.assertIn('aria-labelledby="passage-extractability-heading"', template)
        self.assertIn("Deneysel tanı", template)
        self.assertIn("Skora dahil değildir", template)

    def test_direct_answer_coverage_is_a_separate_unscored_diagnostic(self):
        view = self._analysed_view()
        diagnostic = view["direct_answer_coverage"]

        self.assertFalse(diagnostic["included_in_score"])
        self.assertNotIn(
            "Direct answer coverage",
            {
                signal["label"]
                for signal in view["assessment"]["geo_score"][
                    "semantic_completeness"
                ]["detail"]["signals"]
            },
        )
        template = self._template()
        self.assertIn('aria-labelledby="direct-answer-coverage-heading"', template)
        self.assertIn("Doğrudan Cevaplama — Deneysel tanı", template)
        self.assertIn("Skora dahil değildir", template)

    def test_passage_balance_is_a_separate_neutral_unscored_diagnostic(self):
        view = self._analysed_view()
        diagnostic = view["passage_balance"]

        self.assertIsInstance(diagnostic["ratio"], float)
        self.assertFalse(diagnostic["included_in_score"])
        semantic_signals = {
            signal["label"]
            for signal in view["assessment"]["geo_score"][
                "semantic_completeness"
            ]["detail"]["signals"]
        }
        self.assertNotIn("Passage balance", semantic_signals)

        template = self._template()
        self.assertIn('aria-labelledby="passage-balance-heading"', template)
        self.assertIn("Paragraf Dengesi — Deneysel tanı", template)
        self.assertIn("Skora dahil değildir", template)

        dom = run_page_script(f"renderReport({json.dumps(view)}, 'report');")
        rendered = dom["#passage-balance-metric"]["html"]
        self.assertIn("Paragraf Dengesi", rendered)
        self.assertNotIn("good", rendered.lower())
        self.assertNotIn("bad", rendered.lower())
        self.assertNotIn("pass", rendered.lower())
        self.assertNotIn("fail", rendered.lower())

    def test_unmeasured_direct_answer_coverage_renders_not_measured(self):
        view = self._analysed_view()
        view["direct_answer_coverage"]["ratio"] = None

        dom = run_page_script(f"renderReport({json.dumps(view)}, 'report');")
        rendered = dom["#direct-answer-coverage-metric"]["html"]
        self.assertIn("Henüz ölçülemiyor", rendered)

    def test_passage_extractability_bands_render_without_classification(self):
        view = self._analysed_view()

        dom = run_page_script(f"renderReport({json.dumps(view)}, 'report');")
        rendered = dom["#passage-extractability-metrics"]["html"]
        self.assertIn("&gt;128 kelime", rendered)
        self.assertIn("&gt;256 kelime", rendered)
        self.assertIn("&gt;512 kelime", rendered)
        self.assertNotIn("good", rendered.lower())
        self.assertNotIn("bad", rendered.lower())

    def test_unmeasured_passage_extractability_renders_not_measured(self):
        view = self._analysed_view()
        for band in view["passage_extractability"]["bands"]:
            band["rate"] = None

        dom = run_page_script(f"renderReport({json.dumps(view)}, 'report');")
        rendered = dom["#passage-extractability-metrics"]["html"]
        self.assertEqual(rendered.count("Henüz ölçülemiyor"), 3)

    def test_seo_and_geo_dimension_panels_toggle_independently(self):
        dom = run_page_script("""
          const seoOne = document.querySelector('#seo-one-button');
          const seoTwo = document.querySelector('#seo-two-button');
          const geoOne = document.querySelector('#geo-one-button');
          for (const [button, panel] of [[seoOne, 'seo-one-panel'], [seoTwo, 'seo-two-panel'], [geoOne, 'geo-one-panel']]) {
            button.setAttribute('aria-controls', panel);
            button.setAttribute('aria-expanded', 'false');
            document.querySelector(`#${panel}`).classList.add('hidden');
          }

          toggleScoreDetail(seoOne);
          toggleScoreDetail(seoTwo);
          toggleScoreDetail(geoOne);
          document.querySelector('#both-open').textContent = [
            seoOne.getAttribute('aria-expanded'),
            seoTwo.getAttribute('aria-expanded'),
            geoOne.getAttribute('aria-expanded'),
            document.querySelector('#seo-one-panel').classList.contains('hidden'),
            document.querySelector('#seo-two-panel').classList.contains('hidden'),
            document.querySelector('#geo-one-panel').classList.contains('hidden')
          ].join(',');

          toggleScoreDetail(seoOne);
          document.querySelector('#one-closed').textContent = [
            seoOne.getAttribute('aria-expanded'),
            seoTwo.getAttribute('aria-expanded'),
            geoOne.getAttribute('aria-expanded'),
            document.querySelector('#seo-one-panel').classList.contains('hidden'),
            document.querySelector('#seo-two-panel').classList.contains('hidden'),
            document.querySelector('#geo-one-panel').classList.contains('hidden')
          ].join(',');
        """)

        self.assertEqual(dom["#both-open"]["text"], "true,true,true,false,false,false")
        self.assertEqual(dom["#one-closed"]["text"], "false,true,true,true,false,false")

    def test_template_only_reads_view_fields_the_server_sends(self):
        """Guards the drift that removing a report field previously caused."""
        referenced = set(re.findall(r"view\.([a-z_]+)", self._template()))
        provided = set(self._analysed_view())

        self.assertTrue(
            referenced <= provided,
            f"template reads {sorted(referenced - provided)} which the view does not send",
        )

    def test_template_only_reads_nested_view_fields_the_server_sends(self):
        """A top-level key existing is not enough; its contents must match too.

        A duplicate key in the view once let the identity block silently
        replace the technical recommendations. The top-level name was still
        present, so a shallow check passed while the page crashed reading a
        field inside it.
        """
        template = self._template()
        view = self._analysed_view()

        missing = []
        for alias, key in re.findall(r"const (\w+) = view\.([a-z_]+);", template):
            block = view.get(key)
            if not isinstance(block, dict):
                continue
            for field in set(re.findall(rf"\b{alias}\.([a-z_]+)", template)):
                if field not in block:
                    missing.append(f"view.{key}.{field}")

        self.assertEqual(
            missing,
            [],
            f"template reads {sorted(missing)} which the view does not send",
        )
    def test_web_view_separates_editor_and_technical_recommendations(self):
        """A second article from the same publisher makes reuse visible."""
        html = """
            <html lang="tr"><head><title>{slug}</title></head>
            <body><main><p>{unique}</p><p>Bu icerik bilgilendirme amacli hazirlanmistir.</p></main></body></html>
        """
        for slug, unique in (("birinci", "Ozgun paragraf."), ("ikinci", "Baska paragraf.")):
            response = self.client.post(
                "/analyze/file",
                data={"source_url": f"https://ebeveynakademisi.trtcocuk.net.tr/makale/{slug}"},
                files={"file": ("a.html", html.format(slug=slug, unique=unique), "text/html")},
            )
            self.assertEqual(response.status_code, 200)

        reuse = response.json()["view"]["editor"]
        self.assertEqual(
            reuse["compared_articles"],
            "Bu yayıncıdan daha önce analiz edilen makalelerle karşılaştırıldı "
            "(1 makale).",
        )
        recommendation = next(
            item
            for item in reuse["recommendations"]
            if item["headline"].startswith("Bu paragraf diğer makalelerinizde")
        )
        self.assertEqual(
            recommendation["headline"],
            "Bu paragraf diğer makalelerinizde de yer alıyor",
        )
        self.assertEqual(
            recommendation["occurrences"][0]["detail"],
            "1 başka makalede de yer alıyor",
        )
        self.assertIn("makale gövdesinin dışında", recommendation["what_to_do"])
        self.assertEqual(len(recommendation["occurrences"]), 1)
        self.assertIn(
            "Bu icerik bilgilendirme", recommendation["occurrences"][0]["excerpt"]
        )

    def _publish(self, slug, paragraph, publisher="ebeveynakademisi.trtcocuk.net.tr"):
        """Put one article into the corpus a draft can be compared against."""
        html = (
            f'<html lang="tr"><head><title>{slug}</title></head><body><main>'
            f"<p>{paragraph}</p></main></body></html>"
        )
        response = self.client.post(
            "/analyze/file",
            data={"source_url": f"https://{publisher}/makale/{slug}"},
            files={"file": ("a.html", html, "text/html")},
        )
        self.assertEqual(response.status_code, 200)
        return response

    def test_the_draft_review_names_checks_as_codes_not_sentences(self):
        """Application decides whether a check applies; presentation words it.

        These were English sentences built inside the use case, which fixed the
        report to one language and put copy in application logic.
        """
        from aether.application.analysis.build_draft_review import (
            DraftCheck,
            UnavailableCheck,
        )

        review = self.client.app.state.pipeline.analyze_draft(
            "<h1>Başlık</h1><p>Bir paragraf.</p>", "", "tr", ""
        )

        for check in review.checks_performed:
            self.assertIsInstance(check, DraftCheck)
        for check in review.checks_unavailable:
            self.assertIsInstance(check, UnavailableCheck)

    def test_every_draft_check_code_has_wording(self):
        """A code with no entry would reach an editor as an enum name."""
        from aether.application.analysis.build_draft_review import (
            DraftCheck,
            UnavailableCheck,
        )
        from aether.presentation.draft_check_text import (
            performed_check_text,
            unavailable_check_text,
        )

        for check in DraftCheck:
            self.assertTrue(performed_check_text(check))
        for check in UnavailableCheck:
            self.assertTrue(unavailable_check_text(check))

    def test_not_choosing_a_publisher_is_offered_and_never_chosen_for_you(self):
        """Being first in the list is not a choice the editor made."""
        dom = run_page_script(
            "await refreshPublishers();",
            publishers=["trthaber.com", "trtworld.com"],
        )
        select = dom["#draft-publisher"]["html"]

        self.assertIn('<option value="">', select)
        self.assertIn("Karşılaştırma", select)
        self.assertLess(select.index('value=""'), select.index("trthaber.com"))

    def test_the_editor_is_told_what_comparing_will_do(self):
        chosen = run_page_script(
            "await refreshPublishers();"
            "document.querySelector('#draft-publisher').value = 'trthaber.com';"
            "describeComparison();",
            publishers=["trthaber.com"],
        )
        self.assertIn(
            "trthaber.com", chosen["#draft-compare-state"]["text"]
        )

        not_chosen = run_page_script(
            "await refreshPublishers();", publishers=["trthaber.com"]
        )
        self.assertIn(
            "checked on its own", not_chosen["#draft-compare-state"]["text"]
        )

        nothing_yet = run_page_script("await refreshPublishers();", publishers=[])
        self.assertIn(
            "Sunucu başladığından beri makale analiz edilmediği",
            nothing_yet["#draft-compare-state"]["text"],
        )

    def test_the_chosen_publisher_survives_a_submission(self):
        """The list is rebuilt after every submit, which discarded the choice."""
        dom = run_page_script(
            "await refreshPublishers();"
            "document.querySelector('#draft-publisher').value = 'trtworld.com';"
            "await refreshPublishers();",
            publishers=["trthaber.com", "trtworld.com"],
        )

        self.assertIn("trtworld.com", dom["#draft-compare-state"]["text"])

    def test_a_draft_with_no_publisher_says_repetition_was_not_checked(self):
        draft = self._draft("<h1>Başlık</h1><p>Bir paragraf.</p>", publisher="").json()[
            "draft"
        ]
        unavailable = " ".join(draft["checks_unavailable"])

        self.assertIn("yayıncı seçilmediği", unavailable)
        self.assertNotIn(
            "Diğer makalelerinizde tekrarlanan metin", draft["checks_performed"]
        )

    def test_a_publisher_with_nothing_checked_yet_says_so_differently(self):
        """Not the same as declining to compare, and not stated the same way."""
        draft = self._draft(
            "<h1>Başlık</h1><p>Bir paragraf.</p>", publisher="trthaber.com"
        ).json()["draft"]
        unavailable = " ".join(draft["checks_unavailable"])

        self.assertIn("henüz makale analiz edilmediği", unavailable)
        self.assertNotIn("yayıncı seçilmediği", unavailable)

    def test_no_publisher_display_name_is_invented_from_a_hostname(self):
        dom = run_page_script(
            "await refreshPublishers();",
            publishers=["ebeveynakademisi.trtcocuk.net.tr"],
        )
        select = dom["#draft-publisher"]["html"]

        self.assertIn("ebeveynakademisi.trtcocuk.net.tr", select)
        self.assertNotIn("Ebeveynakademisi<", select)

    def test_choosing_a_publisher_after_a_first_check_takes_effect(self):
        """A draft was identified by its text alone, so it kept the publisher
        it was first checked against. Checking it again after choosing one
        compared it against the earlier choice, silently and permanently.
        """
        publisher = "ebeveynakademisi.trtcocuk.net.tr"
        shared = "Bu icerik bilgilendirme amacli hazirlanmistir."
        self._publish("birinci", shared, publisher=publisher)
        draft = f"<h1>Yeni makale</h1><p>{shared}</p><p>Ozgun paragraf.</p>"

        without = self._draft(draft, publisher="").json()["draft"]
        without_findings = " ".join(r["headline"] for r in without["recommendations"])
        self.assertNotIn("diğer makalelerinizde de yer alıyor", without_findings)

        with_publisher = self._draft(draft, publisher=publisher).json()["draft"]
        findings = " ".join(r["headline"] for r in with_publisher["recommendations"])
        self.assertIn("diğer makalelerinizde de yer alıyor", findings)

    def test_the_same_draft_and_publisher_stay_one_draft(self):
        publisher = "ebeveynakademisi.trtcocuk.net.tr"
        self._publish("birinci", "Birinci metin.", publisher=publisher)
        draft = "<h1>Taslak</h1><p>Ozgun bir paragraf.</p>"

        self._draft(draft, publisher=publisher)
        self._draft(draft, publisher=publisher)

        repository = self.client.app.state.pipeline.repository
        drafts = [a for a in repository.all_articles() if a.article_type == "draft"]
        self.assertEqual(len(drafts), 1)

    def test_the_same_draft_checked_against_two_publishers_is_two_drafts(self):
        draft = "<h1>Taslak</h1><p>Ozgun bir paragraf.</p>"

        self._draft(draft, publisher="TRT Haber")
        self._draft(draft, publisher="TRT World")

        repository = self.client.app.state.pipeline.repository
        publishers = {
            a.publisher for a in repository.all_articles() if a.article_type == "draft"
        }
        self.assertEqual(publishers, {"TRT Haber", "TRT World"})

    def test_a_draft_counts_every_published_article_it_was_compared_with(self):
        """One published article is one article compared against, not none.

        The count subtracted the article being analysed, which is right for a
        published article because it is in the corpus. A draft never is, so the
        subtraction removed a real article instead.
        """
        publisher = "ebeveynakademisi.trtcocuk.net.tr"
        for index, (slug, paragraph) in enumerate(
            (("birinci", "Birinci metin."), ("ikinci", "Ikinci metin.")), start=1
        ):
            self._publish(slug, paragraph, publisher=publisher)
            draft = self._draft(
                f"<h1>Taslak {index}</h1><p>Tamamen ozgun bir paragraf {index}.</p>",
                publisher=publisher,
            ).json()["draft"]

            self.assertEqual(draft["compared_article_count"], index)
            self.assertIn(
                "Diğer makalelerinizde tekrarlanan metin", draft["checks_performed"]
            )

    def test_drafts_are_never_counted_as_articles_to_compare_against(self):
        publisher = "ebeveynakademisi.trtcocuk.net.tr"
        self._publish("birinci", "Birinci metin.", publisher=publisher)
        for index in range(3):
            draft = self._draft(
                f"<h1>Taslak {index}</h1><p>Ozgun paragraf {index}.</p>",
                publisher=publisher,
            ).json()["draft"]

        self.assertEqual(draft["compared_article_count"], 1)

    def test_a_published_article_still_excludes_itself_from_the_comparison(self):
        """The published path must be unchanged; it was already correct."""
        publisher = "ebeveynakademisi.trtcocuk.net.tr"
        first = self._publish("birinci", "Birinci metin.", publisher=publisher)
        self.assertEqual(
            first.json()["view"]["editor"]["compared_articles"],
            "Bu yayıncıdan daha önce analiz edilmiş makale olmadığı için "
            "tekrarlanan metin kontrol edilemedi.",
        )

        second = self._publish("ikinci", "Ikinci metin.", publisher=publisher)
        self.assertEqual(
            second.json()["view"]["editor"]["compared_articles"],
            "Bu yayıncıdan daha önce analiz edilen makalelerle karşılaştırıldı "
            "(1 makale).",
        )

    def test_a_draft_finding_reaches_the_page_instead_of_throwing(self):
        """The whole seam: a real repeated paragraph, rendered by the real page.

        renderDraft called a card() that only existed inside renderReport, so a
        draft with anything to report threw a ReferenceError and showed nothing.
        A draft with no findings took the other branch and rendered, which is
        why every earlier check of this flow looked correct.

        Asserted by running the page, because the two static template checks
        above both passed while this was broken.
        """
        shared = "Bu icerik bilgilendirme amacli hazirlanmistir."
        self._publish("birinci", shared)
        draft = self._draft(
            f"<h1>Yeni makale</h1><p>{shared}</p><p>Bu paragraf ozgundur.</p>",
            publisher="ebeveynakademisi.trtcocuk.net.tr",
        ).json()["draft"]

        self.assertTrue(
            draft["recommendations"], "the draft must have a finding to render"
        )

        dom = run_page_script(f"renderDraft({json.dumps(draft)});")
        findings = dom["#draft-findings"]["html"]

        self.assertIn("Bu paragraf diğer makalelerinizde de yer alıyor", findings)
        self.assertIn(shared, findings)
        self.assertIn("Ne yapmalısınız?", findings)
        self.assertNotIn("değişiklik önerisi yok", findings)

    def test_a_draft_with_nothing_to_report_still_says_so(self):
        """The branch that did work must keep working."""
        draft = self._draft("<h1>Başlık</h1><p>Bir paragraf.</p>").json()["draft"]

        dom = run_page_script(f"renderDraft({json.dumps(draft)});")

        self.assertIn("değişiklik önerisi yok", dom["#draft-findings"]["html"])

    def test_index_shows_both_audience_sections(self):
        response = self.client.get("/")

        self.assertIn('id="editor-section"', response.text)
        self.assertIn('id="technical-section"', response.text)
        self.assertIn("İçerikte Yapılabilecekler", response.text)
        self.assertIn("Teknik / Site Düzeyinde Yapılabilecekler", response.text)

    def test_a_page_with_no_article_text_is_explained_not_rejected(self):
        """A video or listing page is an expected outcome, not an error."""
        html = """
            <html lang="tr"><head><title>Video</title>
              <meta property="og:type" content="website" />
            </head><body><main><div>Video oynatıcı</div></main></body></html>
        """

        response = self.client.post(
            "/analyze/file",
            data={"source_url": "https://www.trtspor.com.tr/videolar/x"},
            files={"file": ("v.html", html, "text/html")},
        )

        self.assertEqual(response.status_code, 200)
        outcome = response.json()["outcome"]
        self.assertEqual(outcome["outcome"], "no_article_text_found")
        self.assertIn("makale metni bulunamadı", outcome["headline"])
        self.assertIn("sorun yoktur", outcome["what_to_do"])
        self.assertIsNone(response.json()["report"])

    def test_an_article_whose_text_cannot_be_read_is_named_as_a_problem(self):
        """A page declaring itself an article with no text contradicts itself."""
        html = """
            <html lang="tr"><head><title>Makale</title>
              <script type="application/ld+json">
                {"@type": "NewsArticle", "headline": "Bir başlık"}
              </script>
            </head><body><main><div>İçerik tarayıcıda yükleniyor</div></main></body></html>
        """

        response = self.client.post(
            "/analyze/file",
            data={"source_url": "https://publisher.example/makale"},
            files={"file": ("a.html", html, "text/html")},
        )

        self.assertEqual(response.status_code, 200)
        outcome = response.json()["outcome"]
        self.assertEqual(outcome["outcome"], "article_text_unreadable")
        self.assertIn("kendisini makale olarak tanımlıyor", outcome["headline"])
        self.assertIn("teknik ekiple", outcome["what_to_do"])

    def test_no_outcome_exposes_parser_wording(self):
        """An editor never sees why the parser stopped."""
        for html in (
            '<html lang="tr"><head><title>V</title></head><body><div>x</div></body></html>',
            '<html lang="tr"><head><title>A</title>'
            '<script type="application/ld+json">{"@type": "Article"}</script>'
            "</head><body><div>x</div></body></html>",
        ):
            response = self.client.post(
                "/analyze/file",
                data={"source_url": "https://publisher.example/p"},
                files={"file": ("p.html", html, "text/html")},
            )
            outcome = response.json()["outcome"]
            blob = " ".join(
                [outcome["headline"], outcome["what_happened"], outcome["what_to_do"]]
            ).lower()
            for jargon in ("parser", "paragraph tag", "html", "passage", "raw article"):
                self.assertNotIn(jargon, blob)

    def test_invalid_url_submission_returns_a_user_facing_validation_error(self):
        response = TestClient(create_app()).post(
            "/analyze/url",
            data={"url": "not-a-url", "publisher": "TRT World", "article_type": "news_report"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "URL, http veya https ile başlayan geçerli bir adres olmalıdır.")

    def test_file_submission_can_use_existing_optional_metadata_fallbacks(self):
        html = """
            <html><head><title>Fallback article</title></head>
            <body><article><p>Visible content for the fallback path.</p></article></body>
            </html>
        """

        response = self.client.post(
            "/analyze/file",
            data={
                "source_url": "https://example.org/fallback-article",
                "publisher": "Example Publisher",
                "article_type": "news_report",
                "fallback_language": "en",
                "fallback_published_at": "2026-05-14T14:00:00+03:00",
            },
            files={"file": ("article.html", html, "text/html")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Publication Date Available: True", response.json()["report"])

    def test_file_submission_reports_a_missing_publication_date(self):
        html = """
            <html lang="en"><head><title>Undated article</title></head>
            <body><article><p>Visible content without a publication date.</p></article></body>
            </html>
        """

        response = self.client.post(
            "/analyze/file",
            data={
                "source_url": "https://example.org/undated-article",
                "publisher": "Example Publisher",
                "article_type": "news_report",
            },
            files={"file": ("undated.html", html, "text/html")},
        )

        self.assertEqual(response.status_code, 200)
        report = response.json()["report"]
        self.assertIn("Publication Date Available: False", report)
        # With the always-true fields gone, a page carrying none of the four
        # fields that can vary is correctly "missing" rather than "partial".
        self.assertIn("Metadata Completeness: partial", report)
        self.assertIn("Makalenin yayın tarihi belirtilmemiş", report)


if __name__ == "__main__":
    unittest.main()
