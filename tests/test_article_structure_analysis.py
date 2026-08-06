import sys
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

sys.path.insert(0, "src")

from aether.adapters.outbound.in_memory_content_repository import (  # noqa: E402
    InMemoryContentRepository,
)
from aether.application.analysis.analyze_article_structure import (  # noqa: E402
    AnalyzeArticleStructure,
)
from aether.application.ingestion.register_source_snapshot import (  # noqa: E402
    RegisterSourceSnapshot,
    SourceArticleSnapshot,
)
from aether.domain.common import DomainValidationError  # noqa: E402


NOW = datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc)


class ArticleStructuralAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryContentRepository()
        self.register = RegisterSourceSnapshot(self.repository)
        self.analyze = AnalyzeArticleStructure(self.repository)

    def register_article(self, source_url, body):
        return self.register.execute(
            SourceArticleSnapshot(
                publisher="TRT",
                canonical_source=source_url,
                original_language="tr",
                article_type="news_report",
                title="A report",
                body=body,
                observed_at=NOW,
                source_published_at=NOW,
            )
        )

    def test_returns_raw_structural_metrics_for_existing_article_version(self):
        registered = self.register_article(
            "https://example.org/news/story",
            "Bir iki.\n\nÜç dört beş.",
        )

        analysis = self.analyze.execute(
            registered.article, registered.article_version.article_version_id
        )

        self.assertEqual(analysis.article_id, registered.article.article_id)
        self.assertEqual(
            analysis.article_version_id, registered.article_version.article_version_id
        )
        self.assertEqual(analysis.total_passage_count, 2)
        self.assertEqual(analysis.total_word_count, 5)

    def test_analysis_is_deterministic_and_immutable(self):
        registered = self.register_article(
            "https://example.org/news/story",
            "One two.\n\nThree four.",
        )

        first = self.analyze.execute(
            registered.article, registered.article_version.article_version_id
        )
        second = self.analyze.execute(
            registered.article, registered.article_version.article_version_id
        )

        self.assertEqual(first, second)
        with self.assertRaises(FrozenInstanceError):
            first.total_word_count = 100

    def test_analysis_rejects_article_version_from_another_article(self):
        first = self.register_article(
            "https://example.org/news/first", "First article paragraph."
        )
        second = self.register_article(
            "https://example.org/news/second", "Second article paragraph."
        )

        with self.assertRaises(DomainValidationError):
            self.analyze.execute(
                first.article, second.article_version.article_version_id
            )

    def test_title_is_not_counted_as_body_words(self):
        registered = self.register_article(
            "https://example.org/news/story", "Only body words count."
        )

        analysis = self.analyze.execute(
            registered.article, registered.article_version.article_version_id
        )

        self.assertEqual(analysis.total_word_count, 4)


if __name__ == "__main__":
    unittest.main()
