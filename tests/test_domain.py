import sys
import unittest
from dataclasses import FrozenInstanceError
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
from aether.domain.claim_candidate import (  # noqa: E402
    ClaimCandidate,
    ClaimCandidateStatus,
)
from aether.domain.claim_candidate_evidence import ClaimCandidateEvidence  # noqa: E402
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
from aether.adapters.outbound.in_memory_claim_candidate_repository import (  # noqa: E402
    InMemoryClaimCandidateRepository,
)
from aether.adapters.outbound.in_memory_claim_candidate_evidence_repository import (  # noqa: E402
    InMemoryClaimCandidateEvidenceRepository,
)
from aether.application.curation.create_claim_candidate import (  # noqa: E402
    CreateClaimCandidate,
    CreateClaimCandidateCommand,
)
from aether.application.curation.attach_claim_candidate_evidence import (  # noqa: E402
    AttachClaimCandidateEvidence,
    AttachClaimCandidateEvidenceCommand,
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

    def test_article_version_fingerprint_includes_optional_source_metadata(self):
        base = ArticleVersion(
            article_version_id="version-1",
            article_id="article-1",
            version_number=1,
            title="Title",
            body="Body",
            observed_at=NOW,
            source_published_at=NOW,
        )
        with_metadata = ArticleVersion(
            article_version_id="version-2",
            article_id="article-1",
            version_number=2,
            title="Title",
            body="Body",
            observed_at=NOW,
            source_published_at=NOW,
            author="Author",
            description="Description",
            keywords="one, two",
        )

        self.assertNotEqual(base.content_fingerprint, with_metadata.content_fingerprint)
        self.assertIsNone(base.author)
        self.assertIsNone(base.description)
        self.assertIsNone(base.keywords)

    def test_article_version_allows_missing_publication_date_with_an_updated_date(self):
        version = ArticleVersion(
            article_version_id="version-without-publication-date",
            article_id="article-1",
            version_number=1,
            title="Title",
            body="Body",
            observed_at=NOW,
            source_published_at=None,
            source_updated_at=NOW,
        )
        article = Article(
            article_id="article-without-publication-date",
            publisher="TRT",
            canonical_source="https://example.org/without-publication-date",
            original_language="tr",
            article_type="news_report",
            initial_published_at=None,
            ingested_at=NOW,
        )

        self.assertIsNone(version.source_published_at)
        self.assertEqual(version.source_updated_at, NOW)
        self.assertIsNone(article.initial_published_at)


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


class ClaimCandidateTests(unittest.TestCase):
    def passage(self, passage_id="passage-1", text="A supported source passage."):
        return Passage(
            passage_id=passage_id,
            article_version_id="version-1",
            ordinal_position=0,
            text=text,
            location_anchor="paragraph:1",
            language="tr",
        )

    def candidate(self, source_passage_ids=("passage-1",)):
        return ClaimCandidate(
            candidate_id="candidate-1",
            proposed_statement="The ministry announced a measure.",
            statement_language="tr",
            source_passage_ids=source_passage_ids,
            created_at=NOW,
        )

    def test_candidate_is_pending_and_retains_multiple_source_passages(self):
        candidate = self.candidate(("passage-1", "passage-2"))

        self.assertEqual(candidate.status, ClaimCandidateStatus.PENDING)
        self.assertEqual(candidate.source_passage_ids, ("passage-1", "passage-2"))

    def test_candidate_requires_at_least_one_source_passage(self):
        with self.assertRaises(DomainValidationError):
            self.candidate(())

    def test_candidate_rejects_duplicate_or_blank_source_passage_ids(self):
        with self.assertRaises(DomainValidationError):
            self.candidate(("passage-1", "passage-1"))
        with self.assertRaises(DomainValidationError):
            self.candidate((" ",))

    def test_candidate_requires_proposed_statement_and_language(self):
        with self.assertRaises(DomainValidationError):
            ClaimCandidate(
                candidate_id="candidate-1",
                proposed_statement=" ",
                statement_language="tr",
                source_passage_ids=("passage-1",),
                created_at=NOW,
            )
        with self.assertRaises(DomainValidationError):
            ClaimCandidate(
                candidate_id="candidate-1",
                proposed_statement="A proposal.",
                statement_language=" ",
                source_passage_ids=("passage-1",),
                created_at=NOW,
            )

    def test_candidate_is_immutable_after_creation(self):
        candidate = self.candidate()

        with self.assertRaises(FrozenInstanceError):
            candidate.proposed_statement = "Changed statement."

    def test_create_claim_candidate_derives_source_ids_from_passages_and_persists(self):
        repository = InMemoryClaimCandidateRepository()
        use_case = CreateClaimCandidate(repository)
        first_passage = self.passage("passage-1")
        second_passage = self.passage("passage-2", "A second source passage.")

        candidate = use_case.execute(
            CreateClaimCandidateCommand(
                candidate_id="candidate-1",
                proposed_statement="The ministry announced a measure.",
                statement_language="tr",
                passages=(first_passage, second_passage),
                created_at=NOW,
            )
        )

        self.assertEqual(candidate.status, ClaimCandidateStatus.PENDING)
        self.assertEqual(candidate.source_passage_ids, ("passage-1", "passage-2"))
        self.assertEqual(repository.get(candidate.candidate_id), candidate)

    def test_create_claim_candidate_rejects_empty_passage_input(self):
        use_case = CreateClaimCandidate(InMemoryClaimCandidateRepository())

        with self.assertRaises(DomainValidationError):
            use_case.execute(
                CreateClaimCandidateCommand(
                    candidate_id="candidate-1",
                    proposed_statement="The ministry announced a measure.",
                    statement_language="tr",
                    passages=(),
                    created_at=NOW,
                )
            )

    def test_candidate_repository_refuses_replacement(self):
        repository = InMemoryClaimCandidateRepository()
        repository.save(self.candidate())

        with self.assertRaises(DomainValidationError):
            repository.save(self.candidate())


class ClaimCandidateEvidenceTests(unittest.TestCase):
    def passage(self, passage_id="passage-1", text="The ministry announced a measure."):
        return Passage(
            passage_id=passage_id,
            article_version_id="version-1",
            ordinal_position=0,
            text=text,
            location_anchor="paragraph:1",
            language="tr",
        )

    def candidate(self):
        return ClaimCandidate(
            candidate_id="candidate-1",
            proposed_statement="The ministry announced a measure.",
            statement_language="tr",
            source_passage_ids=("passage-1",),
            created_at=NOW,
        )

    def evidence(self, source_passage_ids=("passage-1",)):
        return ClaimCandidateEvidence(
            evidence_id="candidate-evidence-1",
            claim_candidate_id="candidate-1",
            source_passage_ids=source_passage_ids,
            supporting_excerpt="The ministry announced a measure.",
            created_at=NOW,
        )

    def test_evidence_retains_candidate_and_multiple_passage_provenance(self):
        evidence = self.evidence(("passage-1", "passage-2"))

        self.assertEqual(evidence.claim_candidate_id, "candidate-1")
        self.assertEqual(evidence.source_passage_ids, ("passage-1", "passage-2"))

    def test_evidence_requires_candidate_id_passages_and_supporting_excerpt(self):
        with self.assertRaises(DomainValidationError):
            ClaimCandidateEvidence(
                evidence_id="candidate-evidence-1",
                claim_candidate_id=" ",
                source_passage_ids=("passage-1",),
                supporting_excerpt="A source excerpt.",
                created_at=NOW,
            )
        with self.assertRaises(DomainValidationError):
            self.evidence(())
        with self.assertRaises(DomainValidationError):
            ClaimCandidateEvidence(
                evidence_id="candidate-evidence-1",
                claim_candidate_id="candidate-1",
                source_passage_ids=("passage-1",),
                supporting_excerpt=" ",
                created_at=NOW,
            )

    def test_evidence_rejects_duplicate_or_blank_source_passage_ids(self):
        with self.assertRaises(DomainValidationError):
            self.evidence(("passage-1", "passage-1"))
        with self.assertRaises(DomainValidationError):
            self.evidence((" ",))

    def test_evidence_is_immutable_after_creation(self):
        evidence = self.evidence()

        with self.assertRaises(FrozenInstanceError):
            evidence.supporting_excerpt = "Changed excerpt."

    def test_attach_evidence_requires_existing_candidate_and_persists(self):
        candidate_repository = InMemoryClaimCandidateRepository()
        candidate_repository.save(self.candidate())
        evidence_repository = InMemoryClaimCandidateEvidenceRepository()
        use_case = AttachClaimCandidateEvidence(
            candidate_repository, evidence_repository
        )
        first_passage = self.passage()
        second_passage = self.passage("passage-2", "The measure applies nationwide.")

        evidence = use_case.execute(
            AttachClaimCandidateEvidenceCommand(
                evidence_id="candidate-evidence-1",
                claim_candidate_id="candidate-1",
                passages=(first_passage, second_passage),
                supporting_excerpt="The ministry announced a measure.",
                created_at=NOW,
            )
        )

        self.assertEqual(evidence.source_passage_ids, ("passage-1", "passage-2"))
        self.assertEqual(evidence_repository.get(evidence.evidence_id), evidence)

    def test_attach_evidence_rejects_unknown_candidate(self):
        use_case = AttachClaimCandidateEvidence(
            InMemoryClaimCandidateRepository(),
            InMemoryClaimCandidateEvidenceRepository(),
        )

        with self.assertRaises(DomainValidationError):
            use_case.execute(
                AttachClaimCandidateEvidenceCommand(
                    evidence_id="candidate-evidence-1",
                    claim_candidate_id="missing-candidate",
                    passages=(self.passage(),),
                    supporting_excerpt="The ministry announced a measure.",
                    created_at=NOW,
                )
            )

    def test_attach_evidence_rejects_excerpt_absent_from_passages(self):
        candidate_repository = InMemoryClaimCandidateRepository()
        candidate_repository.save(self.candidate())
        use_case = AttachClaimCandidateEvidence(
            candidate_repository,
            InMemoryClaimCandidateEvidenceRepository(),
        )

        with self.assertRaises(DomainValidationError):
            use_case.execute(
                AttachClaimCandidateEvidenceCommand(
                    evidence_id="candidate-evidence-1",
                    claim_candidate_id="candidate-1",
                    passages=(self.passage(),),
                    supporting_excerpt="A different statement.",
                    created_at=NOW,
                )
            )

    def test_evidence_repository_refuses_replacement(self):
        repository = InMemoryClaimCandidateEvidenceRepository()
        repository.save(self.evidence())

        with self.assertRaises(DomainValidationError):
            repository.save(self.evidence())


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

    def test_metadata_only_change_creates_a_new_article_version(self):
        first = self.register.execute(self.snapshot())
        metadata_only_change = self.register.execute(
            SourceArticleSnapshot(
                publisher="TRT",
                canonical_source="https://example.org/news/story",
                original_language="tr",
                article_type="news_report",
                title="A report",
                body="First paragraph.\n\nSecond paragraph.",
                observed_at=NOW,
                source_published_at=NOW,
                author="Reporter",
                description="A source description.",
                keywords="news, policy",
            )
        )

        self.assertEqual(metadata_only_change.article.article_id, first.article.article_id)
        self.assertTrue(metadata_only_change.version_created)
        self.assertEqual(len(metadata_only_change.article.version_ids), 2)
        self.assertEqual(metadata_only_change.article_version.author, "Reporter")


if __name__ == "__main__":
    unittest.main()
