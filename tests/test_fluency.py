import sys
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

sys.path.insert(0, "src")

from aether.adapters.outbound.in_memory_content_repository import (  # noqa: E402
    InMemoryContentRepository,
)
from aether.application.analysis.analyze_fluency import (  # noqa: E402
    AnalyzeFluency,
)
from aether.application.ingestion.register_source_snapshot import (  # noqa: E402
    RegisterSourceSnapshot,
    SourceArticleSnapshot,
)
from aether.domain.common import DomainValidationError  # noqa: E402
from aether.domain.source_data import DeclaredHeading  # noqa: E402


NOW = datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc)


class FluencyAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryContentRepository()
        self.register = RegisterSourceSnapshot(self.repository)
        self.analyze = AnalyzeFluency(self.repository)

    def register_article(
        self,
        source_url,
        body,
        *,
        declared_headings=(),
        list_word_count=0,
        blockquote_word_count=0,
    ):
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
                declared_headings=declared_headings,
                list_word_count=list_word_count,
                blockquote_word_count=blockquote_word_count,
            )
        )

    def test_measures_sentence_lengths_deterministically(self):
        registered = self.register_article(
            "https://example.org/news/story",
            "Short sentence. This is a longer sentence with several words.",
        )

        analysis = self.analyze.execute(
            registered.article,
            registered.article_version.article_version_id,
        )

        self.assertEqual(analysis.sentence_count, 2)
        self.assertEqual(analysis.average_sentence_word_count, 5.0)
        self.assertGreater(analysis.sentence_length_variation, 0.0)
        self.assertGreater(analysis.sentence_balance_ratio, 0.0)
        self.assertLessEqual(analysis.sentence_balance_ratio, 1.0)

    def test_balanced_sentences_produce_full_balance_ratio(self):
        registered = self.register_article(
            "https://example.org/news/story",
            "One two three. Four five six.",
        )

        analysis = self.analyze.execute(
            registered.article,
            registered.article_version.article_version_id,
        )

        self.assertEqual(analysis.sentence_count, 2)
        self.assertEqual(analysis.average_sentence_word_count, 3.0)
        self.assertEqual(analysis.sentence_length_variation, 0.0)
        self.assertEqual(analysis.sentence_balance_ratio, 1.0)

    def test_structural_variety_uses_retained_structural_word_counts(self):
        registered = self.register_article(
            "https://example.org/news/story",
            "First paragraph contains several words.",
            declared_headings=(
                DeclaredHeading(level=2, text="Main topic"),
            ),
            list_word_count=6,
            blockquote_word_count=5,
        )

        analysis = self.analyze.execute(
            registered.article,
            registered.article_version.article_version_id,
        )

        self.assertGreater(analysis.structural_variety_ratio, 0.0)
        self.assertLessEqual(analysis.structural_variety_ratio, 1.0)
        self.assertEqual(analysis.structural_variety_ratio, 1.0)

    def test_content_without_sentence_punctuation_is_still_measured(self):
        registered = self.register_article(
            "https://example.org/news/story",
            "başlık",
        )

        analysis = self.analyze.execute(
            registered.article,
            registered.article_version.article_version_id,
        )

        self.assertEqual(analysis.sentence_count, 1)
        self.assertEqual(analysis.average_sentence_word_count, 1.0)
        self.assertEqual(analysis.sentence_length_variation, 0.0)
        self.assertEqual(analysis.sentence_balance_ratio, 1.0)
        self.assertEqual(analysis.structural_variety_ratio, 0.0)

    def test_analysis_is_deterministic_and_immutable(self):
        registered = self.register_article(
            "https://example.org/news/story",
            "Stable sentence. Another stable sentence.",
        )

        first = self.analyze.execute(
            registered.article,
            registered.article_version.article_version_id,
        )
        second = self.analyze.execute(
            registered.article,
            registered.article_version.article_version_id,
        )

        self.assertEqual(first, second)

        with self.assertRaises(FrozenInstanceError):
            first.sentence_count = 99

    def test_rejects_article_version_from_a_different_article(self):
        first = self.register_article(
            "https://example.org/news/first",
            "First paragraph.",
        )
        second = self.register_article(
            "https://example.org/news/second",
            "Second paragraph.",
        )

        with self.assertRaises(DomainValidationError):
            self.analyze.execute(
                first.article,
                second.article_version.article_version_id,
            )


if __name__ == "__main__":
    unittest.main()