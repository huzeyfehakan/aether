"""In-memory persistence for immutable Claim Candidate Evidence."""

from typing import Dict, Optional

from aether.domain.claim_candidate_evidence import ClaimCandidateEvidence
from aether.domain.common import DomainValidationError
from aether.ports.outbound.claim_candidate_evidence_repository import (
    ClaimCandidateEvidenceRepository,
)


class InMemoryClaimCandidateEvidenceRepository(ClaimCandidateEvidenceRepository):
    def __init__(self) -> None:
        self._evidence: Dict[str, ClaimCandidateEvidence] = {}

    def save(self, evidence: ClaimCandidateEvidence) -> None:
        if evidence.evidence_id in self._evidence:
            raise DomainValidationError(
                "claim candidate evidence is immutable and already exists"
            )
        self._evidence[evidence.evidence_id] = evidence

    def get(self, evidence_id: str) -> Optional[ClaimCandidateEvidence]:
        return self._evidence.get(evidence_id)
