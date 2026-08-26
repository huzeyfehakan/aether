import json
import re
import sys
import unittest
from hashlib import sha256
from pathlib import Path

sys.path.insert(0, "src")

from fastapi.testclient import TestClient  # noqa: E402

from aether.presentation.web.app import create_app  # noqa: E402

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
        self.assertIn("Check a draft", response.text)
        self.assertIn('id="assessment-grid"', response.text)
        self.assertIn('id="report"', response.text)

    def test_the_editor_ui_no_longer_asks_for_a_saved_html_file(self):
        """Nobody in an editorial workflow has one; the endpoint stays for tests."""
        response = self.client.get("/")

        self.assertNotIn('data-endpoint="/analyze/file"', response.text)
        self.assertNotIn("Upload HTML", response.text)

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
        self.assertIn("enter the headline", response.json()["detail"])

    def test_a_supplied_headline_is_used_when_the_paste_has_no_heading(self):
        response = self._draft("<p>Bir paragraf.</p>", headline="Editörün başlığı")

        self.assertEqual(response.json()["draft"]["headline"], "Editörün başlığı")

    def test_a_draft_with_its_own_heading_is_not_given_a_second_one(self):
        """Injecting one made every such draft look like it had two."""
        response = self._draft("<h1>Başlık</h1><p>Bir paragraf.</p>", headline="Başka")
        findings = " ".join(
            r["headline"] for r in response.json()["draft"]["recommendations"]
        )

        self.assertNotIn("more than one main heading", findings)

    def test_a_draft_with_several_top_level_headings_is_reported(self):
        response = self._draft("<h1>Bir</h1><p>M.</p><h1>İki</h1><p>N.</p>")
        draft = response.json()["draft"]
        findings = " ".join(r["headline"] for r in draft["recommendations"])
        details = json.dumps(draft["recommendations"], ensure_ascii=False)

        self.assertIn("more than one main heading", findings)
        self.assertIn("claim to be the main heading", details)
        self.assertNotIn("other article", details)

    def test_a_plain_text_draft_says_headings_could_not_be_checked(self):
        response = self._draft(
            "Bir paragraf.\n\nİkinci paragraf.", headline="Editörün başlığı"
        )
        draft = response.json()["draft"]

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Heading structure", draft["checks_performed"])
        self.assertTrue(
            any("carried no formatting" in c for c in draft["checks_unavailable"])
        )

    def test_an_empty_draft_is_refused_with_an_editor_facing_message(self):
        response = self._draft("", headline="Bir başlık")

        self.assertEqual(response.status_code, 422)
        detail = response.json()["detail"].lower()
        for jargon in ("paragraph tag", "raw article", "parser", "none"):
            self.assertNotIn(jargon, detail)

    def test_a_draft_lists_what_needs_the_published_page(self):
        draft = self._draft("<h1>Başlık</h1><p>Bir paragraf.</p>").json()["draft"]
        unavailable = " ".join(draft["checks_unavailable"]).lower()

        self.assertIn("publication date", unavailable)
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
            "HTML file needs a source URL because no canonical URL was found",
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
            "HTML file needs a source URL because no canonical URL was found",
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
            ["Outgoing links", "Body links", "Body link ratio", "Unique targets"],
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
        self.assertEqual(rendered.count("Details"), 4)
        self.assertIn("Semantic Completeness", rendered)
        self.assertIn("Entity Authority", rendered)
        self.assertIn("Structural Richness", rendered)
        self.assertIn("Discoverability", rendered)
        self.assertIn("Statistics coverage", rendered)
        self.assertIn("Author declaration", rendered)
        self.assertIn("Citation coverage", rendered)
        self.assertIn("Claim evidence coverage", rendered)
        self.assertIn("Structured content ratio", rendered)
        self.assertIn("Body link ratio", rendered)
        self.assertIn("Not measured", rendered)

        seo_rendered = dom["#seo-score-grid"]["html"]
        self.assertEqual(seo_rendered.count('aria-expanded="false"'), 4)
        self.assertEqual(seo_rendered.count("aria-controls="), 4)
        self.assertEqual(seo_rendered.count("Details"), 4)
        for label in (
            "Publication date",
            "Last modified date",
            "Author",
            "Description",
            "Article structured data",
            "Declared expected properties",
            "Missing expected properties",
            "Property coverage",
            "Total passages",
            "Unique passages",
            "Repeated passages",
            "Unique passage ratio",
            "Title sources disagree",
            "Description sources disagree",
        ):
            self.assertIn(label, seo_rendered)

    def test_score_grids_use_natural_card_heights_and_wrap_long_signals(self):
        template = self._template()

        self.assertIn(
            "#seo-score-grid, #geo-score-grid { align-items: start; }",
            template,
        )
        self.assertIn("align-self: start", template)
        self.assertIn("min-width: 0", template)
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
            "document.querySelector('#long-signal').innerHTML = "
            f"scoreDimensionCard({json.dumps(dimension)}, 'seo');"
        )
        rendered = dom["#long-signal"]["html"]
        self.assertIn(long_value, rendered)
        for identifier in (
            "dateModified",
            "datePublished",
            "mainEntityOfPage",
        ):
            self.assertIn(identifier, rendered)
        self.assertIn("geo-signal-row-stacked", rendered)
        self.assertIn('aria-expanded="false"', rendered)
        self.assertIn("aria-controls=", rendered)

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
            f"scoreDimensionCard({json.dumps(dimension)}, 'seo');"
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
        self.assertIn("Experimental diagnostic", template)
        self.assertIn("Not included in score", template)

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
        self.assertIn("Direct Answer Coverage — Experimental diagnostic", template)
        self.assertIn("Not included in score", template)

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
        self.assertIn("Passage Balance — Experimental diagnostic", template)
        self.assertIn("Not included in score", template)

        dom = run_page_script(f"renderReport({json.dumps(view)}, 'report');")
        rendered = dom["#passage-balance-metric"]["html"]
        self.assertIn("Passage Balance", rendered)
        self.assertNotIn("good", rendered.lower())
        self.assertNotIn("bad", rendered.lower())
        self.assertNotIn("pass", rendered.lower())
        self.assertNotIn("fail", rendered.lower())

    def test_unmeasured_direct_answer_coverage_renders_not_measured(self):
        view = self._analysed_view()
        view["direct_answer_coverage"]["ratio"] = None

        dom = run_page_script(f"renderReport({json.dumps(view)}, 'report');")
        rendered = dom["#direct-answer-coverage-metric"]["html"]
        self.assertIn("Not measured", rendered)

    def test_passage_extractability_bands_render_without_classification(self):
        view = self._analysed_view()

        dom = run_page_script(f"renderReport({json.dumps(view)}, 'report');")
        rendered = dom["#passage-extractability-metrics"]["html"]
        self.assertIn("&gt;128 words", rendered)
        self.assertIn("&gt;256 words", rendered)
        self.assertIn("&gt;512 words", rendered)
        self.assertNotIn("good", rendered.lower())
        self.assertNotIn("bad", rendered.lower())

    def test_unmeasured_passage_extractability_renders_not_measured(self):
        view = self._analysed_view()
        for band in view["passage_extractability"]["bands"]:
            band["rate"] = None

        dom = run_page_script(f"renderReport({json.dumps(view)}, 'report');")
        rendered = dom["#passage-extractability-metrics"]["html"]
        self.assertEqual(rendered.count("Not measured"), 3)

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
            "Compared against previously analyzed articles from this publisher "
            "(1 article).",
        )
        recommendation = next(
            item
            for item in reuse["recommendations"]
            if item["headline"].startswith("This paragraph also appears")
        )
        self.assertEqual(
            recommendation["headline"],
            "This paragraph also appears in your other articles",
        )
        self.assertEqual(
            recommendation["occurrences"][0]["detail"],
            "Also appears in 1 other article",
        )
        self.assertIn("outside the article body", recommendation["what_to_do"])
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
        self.assertIn("Don", select)
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
            "No articles have been checked yet",
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

        self.assertIn("no publisher was chosen", unavailable)
        self.assertNotIn(
            "Text repeated in your other articles", draft["checks_performed"]
        )

    def test_a_publisher_with_nothing_checked_yet_says_so_differently(self):
        """Not the same as declining to compare, and not stated the same way."""
        draft = self._draft(
            "<h1>Başlık</h1><p>Bir paragraf.</p>", publisher="trthaber.com"
        ).json()["draft"]
        unavailable = " ".join(draft["checks_unavailable"])

        self.assertIn("have been checked yet", unavailable)
        self.assertNotIn("no publisher was chosen", unavailable)

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
        self.assertNotIn("also appears in your other articles", without_findings)

        with_publisher = self._draft(draft, publisher=publisher).json()["draft"]
        findings = " ".join(r["headline"] for r in with_publisher["recommendations"])
        self.assertIn("also appears in your other articles", findings)

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
                "Text repeated in your other articles", draft["checks_performed"]
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
            "No previously analyzed articles from this publisher, so repeated "
            "text could not be checked.",
        )

        second = self._publish("ikinci", "Ikinci metin.", publisher=publisher)
        self.assertEqual(
            second.json()["view"]["editor"]["compared_articles"],
            "Compared against previously analyzed articles from this publisher "
            "(1 article).",
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

        self.assertIn("This paragraph also appears in your other articles", findings)
        self.assertIn(shared, findings)
        self.assertIn("What to do.", findings)
        self.assertNotIn("Nothing to change", findings)

    def test_a_draft_with_nothing_to_report_still_says_so(self):
        """The branch that did work must keep working."""
        draft = self._draft("<h1>Başlık</h1><p>Bir paragraf.</p>").json()["draft"]

        dom = run_page_script(f"renderDraft({json.dumps(draft)});")

        self.assertIn("Nothing to change", dom["#draft-findings"]["html"])

    def test_index_shows_both_audience_sections(self):
        response = self.client.get("/")

        self.assertIn('id="editor-section"', response.text)
        self.assertIn('id="technical-section"', response.text)
        self.assertIn("Editor Recommendations", response.text)
        self.assertIn("Technical AI Readiness", response.text)

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
        self.assertIn("No article text was found", outcome["headline"])
        self.assertIn("nothing is wrong", outcome["what_to_do"])
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
        self.assertIn("says it is an article", outcome["headline"])
        self.assertIn("maintains the site", outcome["what_to_do"])

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
        self.assertEqual(response.json()["detail"], "URL must be an absolute HTTP(S) URL")

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
        self.assertIn("This article does not say when it was published", report)


if __name__ == "__main__":
    unittest.main()
