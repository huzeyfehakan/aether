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
        for absent in ("article_id", "identity", "assessment", "completeness"):
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
        self.assertIn("Metadata Completeness: missing", report)
        self.assertIn("This article does not say when it was published", report)


if __name__ == "__main__":
    unittest.main()
