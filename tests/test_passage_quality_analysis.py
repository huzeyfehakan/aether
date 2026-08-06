import sys
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

sys.path.insert(0, "src")

from aether.adapters.outbound.in_memory_content_repository import (  # noqa: E402
    InMemoryContentRepository,
)
from aether.application.analysis.analyze_passage_quality import (  # noqa: E402
    AnalyzePassageQuality,
)
from aether.application.ingestion.register_source_snapshot import (  # noqa: E402
    RegisterSourceSnapshot,
    SourceArticleSnapshot,
)
from aether.domain.common import DomainValidationError  # noqa: E402


NOW = datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc)


class PassageQualityAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryContentRepository()
        self.register = RegisterSourceSnapshot(self.repository)
        self.analyze = AnalyzePassageQuality(self.repository)

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

    def test_returns_raw_passage_profiles_and_word_count_bounds(self):
        registered = self.register_article(
            "https://example.org/news/story",
            "One two.\n\nThree four five.",
        )

        analysis = self.analyze.execute(
            registered.article, registered.article_version.article_version_id
        )

        self.assertEqual(len(analysis.passage_profiles), 2)
        self.assertEqual(
            [(profile.word_count, profile.character_count) for profile in analysis.passage_profiles],
            [(2, len("One two.")), (3, len("Three four five."))],
        )
        self.assertEqual(analysis.minimum_passage_word_count, 2)
        self.assertEqual(analysis.maximum_passage_word_count, 3)
        self.assertEqual(analysis.median_passage_word_count, 2.5)

    def test_analysis_is_deterministic_and_immutable(self):
        registered = self.register_article(
            "https://example.org/news/story", "Stable paragraph."
        )

        first = self.analyze.execute(
            registered.article, registered.article_version.article_version_id
        )
        second = self.analyze.execute(
            registered.article, registered.article_version.article_version_id
        )

        self.assertEqual(first, second)
        with self.assertRaises(FrozenInstanceError):
            first.minimum_passage_word_count = 100

    def test_rejects_article_version_from_a_different_article(self):
        first = self.register_article(
            "https://example.org/news/first", "First paragraph."
        )
        second = self.register_article(
            "https://example.org/news/second", "Second paragraph."
        )

        with self.assertRaises(DomainValidationError):
            self.analyze.execute(
                first.article, second.article_version.article_version_id
            )


if __name__ == "__main__":
    unittest.main()
