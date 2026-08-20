import sys
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

sys.path.insert(0, "src")

from aether.adapters.outbound.in_memory_content_repository import (  # noqa: E402
    InMemoryContentRepository,
)
from aether.application.analysis.analyze_claim_evidence import (  # noqa: E402
    AnalyzeClaimEvidence,
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


class ClaimEvidenceAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryContentRepository()
        self.register = RegisterSourceSnapshot(self.repository)

        self.passage_quality = AnalyzePassageQuality(
            self.repository
        )

        self.analyze = AnalyzeClaimEvidence(
            self.repository,
            self.passage_quality,
        )

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

    def test_counts_statistical_passages_as_detectable_claims(self):
        registered = self.register_article(
            "https://example.org/news/story",
            (
                "The rate increased by 40%.\n\n"
                "The project started in 2026.\n\n"
                "This paragraph contains no measurable claim."
            ),
        )

        analysis = self.analyze.execute(
            registered.article,
            registered.article_version.article_version_id,
        )

        self.assertEqual(
            analysis.detectable_claim_count,
            2,
        )

    def test_counts_statistical_passages_with_citations_as_supported(self):
        registered = self.register_article(
            "https://example.org/news/story",
            (
                "The rate increased by 40% [1].\n\n"
                "The project started in 2026.\n\n"
                "Revenue reached $500 [2]."
            ),
        )

        analysis = self.analyze.execute(
            registered.article,
            registered.article_version.article_version_id,
        )

        self.assertEqual(
            analysis.detectable_claim_count,
            3,
        )
        self.assertEqual(
            analysis.supported_claim_count,
            2,
        )
        self.assertEqual(
            analysis.claim_evidence_coverage,
            2 / 3,
        )

    def test_citation_without_statistical_claim_is_not_counted_as_supported_claim(self):
        registered = self.register_article(
            "https://example.org/news/story",
            (
                "Researchers published the report [1].\n\n"
                "The rate increased by 40%."
            ),
        )

        analysis = self.analyze.execute(
            registered.article,
            registered.article_version.article_version_id,
        )

        self.assertEqual(
            analysis.detectable_claim_count,
            1,
        )
        self.assertEqual(
            analysis.supported_claim_count,
            0,
        )
        self.assertEqual(
            analysis.claim_evidence_coverage,
            0.0,
        )

    def test_all_detectable_claims_with_citations_produce_full_coverage(self):
        registered = self.register_article(
            "https://example.org/news/story",
            (
                "The rate increased by 40% [1].\n\n"
                "The project started in 2026 [2]."
            ),
        )

        analysis = self.analyze.execute(
            registered.article,
            registered.article_version.article_version_id,
        )

        self.assertEqual(
            analysis.detectable_claim_count,
            2,
        )
        self.assertEqual(
            analysis.supported_claim_count,
            2,
        )
        self.assertEqual(
            analysis.claim_evidence_coverage,
            1.0,
        )

    def test_no_detectable_claims_produce_zero_coverage(self):
        registered = self.register_article(
            "https://example.org/news/story",
            (
                "This is a descriptive paragraph.\n\n"
                "This paragraph contains no measurable claim."
            ),
        )

        analysis = self.analyze.execute(
            registered.article,
            registered.article_version.article_version_id,
        )

        self.assertEqual(
            analysis.detectable_claim_count,
            0,
        )
        self.assertEqual(
            analysis.supported_claim_count,
            0,
        )
        self.assertEqual(
            analysis.claim_evidence_coverage,
            0.0,
        )

    def test_analysis_is_deterministic_and_immutable(self):
        registered = self.register_article(
            "https://example.org/news/story",
            "The rate increased by 40% [1].",
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
            first.detectable_claim_count = 99

    def test_rejects_article_version_from_a_different_article(self):
        first = self.register_article(
            "https://example.org/news/first",
            "The rate increased by 40% [1].",
        )

        second = self.register_article(
            "https://example.org/news/second",
            "The rate increased by 50% [2].",
        )

        with self.assertRaises(DomainValidationError):
            self.analyze.execute(
                first.article,
                second.article_version.article_version_id,
            )


if __name__ == "__main__":
    unittest.main()