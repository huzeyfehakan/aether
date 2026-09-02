import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, "src")

from aether.adapters.outbound.in_memory_content_repository import (  # noqa: E402
    InMemoryContentRepository,
)
from aether.application.analysis.analyze_internal_links import (  # noqa: E402
    AnalyzeInternalLinks,
)
from aether.application.ingestion.register_source_snapshot import (  # noqa: E402
    RegisterSourceSnapshot,
    SourceArticleSnapshot,
)
from aether.domain.source_data import InternalLink  # noqa: E402


NOW = datetime(2026, 9, 2, 9, 0, tzinfo=timezone.utc)


class InternalLinkAnalysisTests(unittest.TestCase):
    def analyze(self, links):
        repository = InMemoryContentRepository()
        registered = RegisterSourceSnapshot(repository).execute(
            SourceArticleSnapshot(
                publisher="Example",
                canonical_source="https://example.org/article",
                original_language="en",
                article_type="news_report",
                title="A report",
                body="Article body.",
                observed_at=NOW,
                source_published_at=NOW,
                internal_links=tuple(links),
            )
        )
        return AnalyzeInternalLinks(repository).execute(
            registered.article, registered.article_version.article_version_id
        )

    def test_counts_distinct_body_targets(self):
        result = self.analyze(
            InternalLink("https://example.org/body/{}".format(index), True)
            for index in range(5)
        )

        self.assertEqual(result.body_link_count, 5)
        self.assertEqual(result.unique_body_target_count, 5)
        self.assertEqual(result.unique_target_count, 5)

    def test_duplicate_body_links_reduce_body_unique_target_count(self):
        result = self.analyze(
            InternalLink("https://example.org/repeated", True) for _ in range(5)
        )

        self.assertEqual(result.body_link_count, 5)
        self.assertEqual(result.unique_body_target_count, 1)
        self.assertEqual(result.unique_target_count, 1)

    def test_non_body_links_do_not_affect_body_unique_targets(self):
        result = self.analyze(
            [
                InternalLink("https://example.org/body", True),
                InternalLink("https://example.org/header", False),
                InternalLink("https://example.org/footer", False),
                InternalLink("https://example.org/footer", False),
            ]
        )

        self.assertEqual(result.body_link_count, 1)
        self.assertEqual(result.unique_body_target_count, 1)
        self.assertEqual(result.unique_target_count, 3)

    def test_zero_body_links_preserves_all_link_unique_target_count(self):
        result = self.analyze(
            [
                InternalLink("https://example.org/header", False),
                InternalLink("https://example.org/footer", False),
            ]
        )

        self.assertEqual(result.body_link_count, 0)
        self.assertEqual(result.unique_body_target_count, 0)
        self.assertEqual(result.unique_target_count, 2)


if __name__ == "__main__":
    unittest.main()
