"""Attach immutable provenance and supporting excerpts to Claim Candidates."""

from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

from aether.domain.claim_candidate_evidence import ClaimCandidateEvidence
from aether.domain.common import DomainValidationError
from aether.domain.content import Passage
from aether.ports.outbound.claim_candidate_evidence_repository import (
    ClaimCandidateEvidenceRepository,
)
from aether.ports.outbound.claim_candidate_repository import ClaimCandidateRepository


@dataclass(frozen=True)
class AttachClaimCandidateEvidenceCommand:
    evidence_id: str
    claim_candidate_id: str
    passages: Tuple[Passage, ...]
    supporting_excerpt: str
    created_at: datetime


class AttachClaimCandidateEvidence:
    """Attach immutable, source-verifiable evidence to an existing candidate."""

    def __init__(
        self,
        candidate_repository: ClaimCandidateRepository,
        evidence_repository: ClaimCandidateEvidenceRepository,
    ) -> None:
        self._candidate_repository = candidate_repository
        self._evidence_repository = evidence_repository

    def execute(
        self, command: AttachClaimCandidateEvidenceCommand
    ) -> ClaimCandidateEvidence:
        if self._candidate_repository.get(command.claim_candidate_id) is None:
            raise DomainValidationError("claim candidate must exist before attaching evidence")
        if not any(
            command.supporting_excerpt in passage.text for passage in command.passages
        ):
            raise DomainValidationError(
                "supporting_excerpt must be a literal substring of a source passage"
            )
        evidence = ClaimCandidateEvidence(
            evidence_id=command.evidence_id,
            claim_candidate_id=command.claim_candidate_id,
            source_passage_ids=tuple(passage.passage_id for passage in command.passages),
            supporting_excerpt=command.supporting_excerpt,
            created_at=command.created_at,
        )
        self._evidence_repository.save(evidence)
        return evidence
