import sys
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

sys.path.insert(0, "src")

from aether.adapters.outbound.in_memory_content_repository import (  # noqa: E402
    InMemoryContentRepository,
)
from aether.application.analysis.analyze_article_metadata import (  # noqa: E402
    AnalyzeArticleMetadata,
)
from aether.application.ingestion.register_source_snapshot import (  # noqa: E402
    RegisterSourceSnapshot,
    SourceArticleSnapshot,
)
from aether.domain.common import DomainValidationError  # noqa: E402


PUBLISHED_AT = datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc)
UPDATED_AT = datetime(2026, 7, 23, 10, 0, tzinfo=timezone.utc)


class ArticleMetadataAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryContentRepository()
        self.register = RegisterSourceSnapshot(self.repository)
        self.analyze = AnalyzeArticleMetadata(self.repository)

    def register_article(
        self,
        source_url,
        *,
        title="  A stored title  ",
        published_at=PUBLISHED_AT,
        updated_at=None,
        author=None,
        description=None,
        keywords=None,
    ):
        return self.register.execute(
            SourceArticleSnapshot(
                publisher="TRT",
                canonical_source=source_url,
                original_language="tr",
                article_type="news_report",
                title=title,
                body="Article body.",
                observed_at=PUBLISHED_AT,
                source_published_at=published_at,
                source_updated_at=updated_at,
                author=author,
                description=description,
                keywords=keywords,
            )
        )

    def test_returns_available_stored_metadata_without_inference(self):
        registered = self.register_article(
            "https://example.org/news/story",
            updated_at=UPDATED_AT,
            author="Reporter",
            description="A source description.",
            keywords="news, policy",
        )

        analysis = self.analyze.execute(
            registered.article, registered.article_version.article_version_id
        )

        self.assertEqual(analysis.article_id, registered.article.article_id)
        self.assertEqual(
            analysis.article_version_id, registered.article_version.article_version_id
        )
        self.assertTrue(analysis.title_available)
        self.assertEqual(analysis.title_length, len("A stored title"))
        self.assertTrue(analysis.canonical_url_available)
        self.assertTrue(analysis.publication_date_available)
        self.assertTrue(analysis.last_modified_date_available)
        self.assertTrue(analysis.language_available)
        self.assertTrue(analysis.author_available)
        self.assertTrue(analysis.description_available)
        self.assertTrue(analysis.keyword_available)

    def test_reports_missing_modified_metadata_without_guessing(self):
        registered = self.register_article("https://example.org/news/story")

        analysis = self.analyze.execute(
            registered.article, registered.article_version.article_version_id
        )

        self.assertFalse(analysis.last_modified_date_available)
        self.assertFalse(analysis.author_available)
        self.assertFalse(analysis.description_available)
        self.assertFalse(analysis.keyword_available)

    def test_reports_missing_publication_date_without_rejecting_the_article(self):
        registered = self.register_article(
            "https://example.org/news/without-publication-date", published_at=None
        )

        analysis = self.analyze.execute(
            registered.article, registered.article_version.article_version_id
        )

        self.assertIsNone(registered.article.initial_published_at)
        self.assertIsNone(registered.article_version.source_published_at)
        self.assertFalse(analysis.publication_date_available)

    def test_analysis_is_deterministic_and_immutable(self):
        registered = self.register_article("https://example.org/news/story")

        first = self.analyze.execute(
            registered.article, registered.article_version.article_version_id
        )
        second = self.analyze.execute(
            registered.article, registered.article_version.article_version_id
        )

        self.assertEqual(first, second)
        with self.assertRaises(FrozenInstanceError):
            first.title_length = 100

    def test_rejects_article_version_from_a_different_article(self):
        first = self.register_article("https://example.org/news/first")
        second = self.register_article("https://example.org/news/second")

        with self.assertRaises(DomainValidationError):
            self.analyze.execute(
                first.article, second.article_version.article_version_id
            )


if __name__ == "__main__":
    unittest.main()
