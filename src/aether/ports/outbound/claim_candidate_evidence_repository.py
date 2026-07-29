"""Persistence boundary for immutable Claim Candidate Evidence records."""

from abc import ABC, abstractmethod
from typing import Optional

from aether.domain.claim_candidate_evidence import ClaimCandidateEvidence


class ClaimCandidateEvidenceRepository(ABC):
    @abstractmethod
    def save(self, evidence: ClaimCandidateEvidence) -> None:
        """Persist new candidate evidence; replacement is forbidden."""

    @abstractmethod
    def get(self, evidence_id: str) -> Optional[ClaimCandidateEvidence]:
        """Return candidate evidence by its stable identity, if it exists."""
