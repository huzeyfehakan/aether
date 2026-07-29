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
from aether.domain.content import Article, ArticleVersion, Passage  # noqa: E402


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

    def test_returns_raw_profiles_and_full_exact_paragraph_coverage(self):
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
        self.assertEqual(analysis.source_paragraph_count, 2)
        self.assertEqual(analysis.covered_source_paragraph_count, 2)
        self.assertEqual(analysis.source_paragraph_coverage_ratio, 1.0)
        self.assertTrue(analysis.passage_ordinals_are_contiguous)

    def test_reports_partial_coverage_and_noncontiguous_ordinals_without_scoring(self):
        article = Article(
            article_id="article-1",
            publisher="TRT",
            canonical_source="https://example.org/news/story",
            original_language="tr",
            article_type="news_report",
            initial_published_at=NOW,
            ingested_at=NOW,
            version_ids=("version-1",),
            current_version_id="version-1",
        )
        version = ArticleVersion(
            article_version_id="version-1",
            article_id="article-1",
            version_number=1,
            title="A report",
            body="Covered paragraph.\n\nUncovered paragraph.",
            observed_at=NOW,
            source_published_at=NOW,
        )
        self.repository.save_article(article)
        self.repository.save_article_version(version)
        self.repository.save_passages(
            (
                Passage(
                    passage_id="version-1:p0",
                    article_version_id="version-1",
                    ordinal_position=0,
                    text="Covered paragraph.",
                    location_anchor="paragraph:1",
                    language="tr",
                ),
                Passage(
                    passage_id="version-1:p2",
                    article_version_id="version-1",
                    ordinal_position=2,
                    text="Different supporting text.",
                    location_anchor="paragraph:3",
                    language="tr",
                ),
            )
        )

        analysis = self.analyze.execute(article, version.article_version_id)

        self.assertEqual(analysis.source_paragraph_count, 2)
        self.assertEqual(analysis.covered_source_paragraph_count, 1)
        self.assertEqual(analysis.source_paragraph_coverage_ratio, 0.5)
        self.assertFalse(analysis.passage_ordinals_are_contiguous)

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
            first.source_paragraph_count = 100

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
