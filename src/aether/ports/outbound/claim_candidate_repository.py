"""Persistence boundary for immutable Claim Candidate records."""

from abc import ABC, abstractmethod
from typing import Optional

from aether.domain.claim_candidate import ClaimCandidate


class ClaimCandidateRepository(ABC):
    @abstractmethod
    def save(self, candidate: ClaimCandidate) -> None:
        """Persist a new candidate; replacing an existing candidate is forbidden."""

    @abstractmethod
    def get(self, candidate_id: str) -> Optional[ClaimCandidate]:
        """Return a candidate by its stable identity, if it exists."""
