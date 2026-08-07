import re
import sys
import unittest
from hashlib import sha256
from pathlib import Path

sys.path.insert(0, "src")

from fastapi.testclient import TestClient  # noqa: E402

from aether.presentation.web.app import create_app  # noqa: E402


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

    def test_index_displays_url_and_html_file_submission_forms(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-endpoint="/analyze/url"', response.text)
        self.assertIn('data-endpoint="/analyze/file"', response.text)
        self.assertIn("Advanced source details", response.text)
        self.assertIn('id="assessment-grid"', response.text)
        self.assertIn('id="report"', response.text)

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

    def test_template_only_reads_view_fields_the_server_sends(self):
        """Guards the drift that removing a report field previously caused."""
        template = (
            Path(__file__).parent.parent
            / "src/aether/presentation/web/templates/index.html"
        ).read_text(encoding="utf-8")
        referenced = set(re.findall(r"view\.([a-z_]+)", template))

        response = self.client.post(
            "/analyze/url",
            data={"url": "https://www.trtworld.com/article/3e946db45c45"},
        )
        provided = set(response.json()["view"])

        self.assertTrue(
            referenced <= provided,
            f"template reads {sorted(referenced - provided)} which the view does not send",
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

    def test_index_shows_both_audience_sections(self):
        response = self.client.get("/")

        self.assertIn('id="editor-section"', response.text)
        self.assertIn('id="technical-section"', response.text)
        self.assertIn("Editor Recommendations", response.text)
        self.assertIn("Technical AI Readiness", response.text)

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
