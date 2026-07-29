"""In-memory persistence for immutable Claim Candidate records."""

from typing import Dict, Optional

from aether.domain.claim_candidate import ClaimCandidate
from aether.domain.common import DomainValidationError
from aether.ports.outbound.claim_candidate_repository import ClaimCandidateRepository


class InMemoryClaimCandidateRepository(ClaimCandidateRepository):
    def __init__(self) -> None:
        self._candidates: Dict[str, ClaimCandidate] = {}

    def save(self, candidate: ClaimCandidate) -> None:
        existing = self._candidates.get(candidate.candidate_id)
        if existing is not None:
            raise DomainValidationError("claim candidate is immutable and already exists")
        self._candidates[candidate.candidate_id] = candidate

    def get(self, candidate_id: str) -> Optional[ClaimCandidate]:
        return self._candidates.get(candidate_id)
