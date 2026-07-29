"""Immutable provenance attached to pending Claim Candidates."""

from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

from .common import DomainValidationError, require_aware


@dataclass(frozen=True)
class ClaimCandidateEvidence:
    """Source-grounded supporting information for one Claim Candidate.

    This is intentionally distinct from ``Evidence``, whose lifecycle begins
    only after a Claim has been formed. Candidate evidence contains no review,
    confidence, or status fields: it records only the provenance and literal
    supporting information provided at creation time.
    """

    evidence_id: str
    claim_candidate_id: str
    source_passage_ids: Tuple[str, ...]
    supporting_excerpt: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise DomainValidationError("candidate evidence_id is required")
        if not self.claim_candidate_id.strip():
            raise DomainValidationError("claim_candidate_id is required")
        if not self.source_passage_ids:
            raise DomainValidationError(
                "candidate evidence requires at least one source passage"
            )
        if any(not passage_id.strip() for passage_id in self.source_passage_ids):
            raise DomainValidationError(
                "candidate evidence source passage ids are required"
            )
        if len(set(self.source_passage_ids)) != len(self.source_passage_ids):
            raise DomainValidationError(
                "candidate evidence source passage ids must be unique"
            )
        if not self.supporting_excerpt.strip():
            raise DomainValidationError("supporting_excerpt is required")
        require_aware(self.created_at, "candidate evidence created_at")
