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
    PassageProfile,
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
        self.assertEqual(
            [profile.text for profile in analysis.passage_profiles],
            ["One two.", "Three four five."],
        )

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
            first.passage_profiles = ()

    def test_oversized_passage_rates_use_strict_experimental_word_bounds(self):
        def rates(word_counts):
            profiles = tuple(
                PassageProfile(
                    passage_id=f"p-{index}",
                    ordinal_position=index,
                    word_count=word_count,
                    character_count=word_count,
                    contains_statistics=False,
                    contains_citation=False,
                )
                for index, word_count in enumerate(word_counts)
            )
            return self.analyze._calculate_oversized_rates(profiles)

        examples = (
            ((100, 100, 100, 100), (0.0, 0.0, 0.0)),
            ((100, 100, 100, 500), (0.25, 0.25, 0.0)),
            ((500, 500, 500, 500), (1.0, 1.0, 0.0)),
            ((600,), (1.0, 1.0, 1.0)),
            ((128, 256, 512), (2 / 3, 1 / 3, 0.0)),
            ((), (None, None, None)),
        )
        for word_counts, expected in examples:
            with self.subTest(word_counts=word_counts):
                self.assertEqual(rates(word_counts), expected)

    def test_analysis_exposes_measured_oversized_rates(self):
        registered = self.register_article(
            "https://example.org/news/oversized",
            " ".join(["word"] * 129),
        )

        analysis = self.analyze.execute(
            registered.article, registered.article_version.article_version_id
        )

        self.assertEqual(analysis.oversized_passage_rate_128, 1.0)
        self.assertEqual(analysis.oversized_passage_rate_256, 0.0)
        self.assertEqual(analysis.oversized_passage_rate_512, 0.0)

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
