import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "src")

from aether.domain.common import (  # noqa: E402
    DomainValidationError,
    TimeAssertion,
    TimePrecision,
    TimeSourceBasis,
    TimeType,
)
from aether.domain.content import Article, ArticleVersion, Passage  # noqa: E402
from aether.domain.evaluation import (  # noqa: E402
    EvaluationRecord,
    EvaluationStatus,
    ExpectedDisposition,
    QuestionType,
)
from aether.domain.knowledge import (  # noqa: E402
    Claim,
    ClaimStatus,
    Evidence,
    EvidenceRelation,
    EvidenceStrength,
    ReviewState,
)
from aether.domain.policies import (  # noqa: E402
    is_claim_eligible,
    transition_claim_status,
    validate_evidence_excerpt,
)
from aether.application.ingestion.register_source_snapshot import (  # noqa: E402
    RegisterSourceSnapshot,
    SourceArticleSnapshot,
)
from aether.adapters.outbound.in_memory_content_repository import (  # noqa: E402
    InMemoryContentRepository,
)


NOW = datetime(2026, 7, 17, 10, 0, tzinfo=timezone.utc)


def claim_time(start=NOW, end=None):
    return TimeAssertion(
        time_type=TimeType.CLAIM_VALIDITY,
        precision=TimePrecision.EXACT,
        source_basis=TimeSourceBasis.MANUALLY_REVIEWED,
        start=start,
        end=end,
    )


def candidate_claim(status=ClaimStatus.CANDIDATE, valid_time=None):
    return Claim(
        claim_id="claim-1",
        canonical_statement="The ministry announced the measure.",
        claim_language="tr",
        claim_type="event_fact",
        modality="reported",
        primary_event_id="event-1",
        claim_status=status,
        created_at=NOW,
        provenance_method="extracted_and_reviewed",
        valid_time=valid_time or claim_time(),
        unresolved_subject="The ministry",
    )


def accepted_evidence():
    return Evidence(
        evidence_id="evidence-1",
        claim_id="claim-1",
        passage_id="passage-1",
        evidence_relation=EvidenceRelation.DIRECT_SUPPORT,
        evidence_strength=EvidenceStrength.DIRECT,
        relevant_excerpt="The ministry announced the measure today.",
        created_at=NOW,
        review_state=ReviewState.ACCEPTED,
    )


class TimeModelTests(unittest.TestCase):
    def test_unknown_time_is_explicit_and_not_contained(self):
        assertion = TimeAssertion(
            time_type=TimeType.EVENT,
            precision=TimePrecision.UNKNOWN,
            source_basis=TimeSourceBasis.UNKNOWN,
        )
        self.assertIsNone(assertion.contains(NOW))

    def test_time_end_cannot_precede_start(self):
        with self.assertRaises(DomainValidationError):
            TimeAssertion(
                time_type=TimeType.EVENT,
                precision=TimePrecision.EXACT,
                source_basis=TimeSourceBasis.PUBLISHER_STATED,
                start=NOW,
                end=NOW - timedelta(seconds=1),
            )


class ContentTests(unittest.TestCase):
    def test_article_current_version_must_be_known(self):
        with self.assertRaises(DomainValidationError):
            Article(
                article_id="article-1",
                publisher="TRT",
                canonical_source="https://example.org/story",
                original_language="tr",
                article_type="news_report",
                initial_published_at=NOW,
                ingested_at=NOW,
                version_ids=("version-1",),
                current_version_id="version-2",
            )

    def test_article_version_fingerprint_is_deterministic(self):
        version = ArticleVersion(
            article_version_id="version-1",
            article_id="article-1",
            version_number=1,
            title="Title",
            body="Body",
            observed_at=NOW,
            source_published_at=NOW,
        )
        self.assertEqual(len(version.content_fingerprint), 64)


class KnowledgePolicyTests(unittest.TestCase):
    def test_direct_evidence_must_reference_literal_passage_text(self):
        passage = Passage(
            passage_id="passage-1",
            article_version_id="version-1",
            ordinal_position=0,
            text="The ministry announced the measure today.",
            location_anchor="paragraph:1",
            language="tr",
        )
        validate_evidence_excerpt(accepted_evidence(), passage)

    def test_claim_cannot_validate_without_direct_accepted_evidence(self):
        with self.assertRaises(DomainValidationError):
            transition_claim_status(candidate_claim(), ClaimStatus.VALIDATED, ())

    def test_claim_validates_with_accepted_direct_evidence(self):
        validated = transition_claim_status(
            candidate_claim(), ClaimStatus.VALIDATED, (accepted_evidence(),)
        )
        self.assertEqual(validated.claim_status, ClaimStatus.VALIDATED)

    def test_only_historical_queries_may_use_superseded_claim(self):
        superseded = candidate_claim(
            status=ClaimStatus.SUPERSEDED,
            valid_time=claim_time(NOW - timedelta(days=1), NOW + timedelta(days=1)),
        )
        self.assertFalse(is_claim_eligible(superseded, NOW))
        self.assertTrue(is_claim_eligible(superseded, NOW, allow_historical=True))


class EvaluationTests(unittest.TestCase):
    def test_answer_evaluation_requires_gold_claim_and_evidence(self):
        as_of = TimeAssertion(
            time_type=TimeType.EVALUATION_AS_OF,
            precision=TimePrecision.EXACT,
            source_basis=TimeSourceBasis.MANUALLY_REVIEWED,
            start=NOW,
        )
        with self.assertRaises(DomainValidationError):
            EvaluationRecord(
                evaluation_id="eval-1",
                question="What happened?",
                question_language="tr",
                question_type=QuestionType.DIRECT_FACT,
                as_of_time=as_of,
                expected_disposition=ExpectedDisposition.ANSWER,
                evaluation_status=EvaluationStatus.DRAFT,
                created_by="reviewer",
                created_at=NOW,
            )

    def test_abstention_evaluation_cannot_have_gold_claims(self):
        as_of = TimeAssertion(
            time_type=TimeType.EVALUATION_AS_OF,
            precision=TimePrecision.EXACT,
            source_basis=TimeSourceBasis.MANUALLY_REVIEWED,
            start=NOW,
        )
        with self.assertRaises(DomainValidationError):
            EvaluationRecord(
                evaluation_id="eval-1",
                question="What happened?",
                question_language="tr",
                question_type=QuestionType.UNSUPPORTED,
                as_of_time=as_of,
                expected_disposition=ExpectedDisposition.ABSTAIN,
                evaluation_status=EvaluationStatus.DRAFT,
                created_by="reviewer",
                created_at=NOW,
                expected_claim_ids=("claim-1",),
            )


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryContentRepository()
        self.register = RegisterSourceSnapshot(self.repository)

    def snapshot(self, body="First paragraph.\n\nSecond paragraph."):
        return SourceArticleSnapshot(
            publisher="TRT",
            canonical_source="https://example.org/news/story",
            original_language="tr",
            article_type="news_report",
            title="A report",
            body=body,
            observed_at=NOW,
            source_published_at=NOW,
        )

    def test_registers_immutable_version_and_ordered_passages(self):
        result = self.register.execute(self.snapshot())

        self.assertTrue(result.version_created)
        self.assertEqual(result.article.version_ids, (result.article_version.article_version_id,))
        self.assertEqual([p.text for p in result.passages], ["First paragraph.", "Second paragraph."])

    def test_replayed_snapshot_is_idempotent(self):
        first = self.register.execute(self.snapshot())
        replay = self.register.execute(self.snapshot())

        self.assertTrue(first.version_created)
        self.assertFalse(replay.version_created)
        self.assertEqual(first.article_version.article_version_id, replay.article_version.article_version_id)

    def test_changed_content_creates_a_new_article_version(self):
        first = self.register.execute(self.snapshot())
        changed = self.register.execute(self.snapshot(body="Corrected paragraph."))

        self.assertEqual(changed.article.article_id, first.article.article_id)
        self.assertTrue(changed.version_created)
        self.assertEqual(len(changed.article.version_ids), 2)
        self.assertNotEqual(changed.article_version.article_version_id, first.article_version.article_version_id)


if __name__ == "__main__":
    unittest.main()
