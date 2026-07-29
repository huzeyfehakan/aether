"""Immutable candidate claims awaiting future curation review."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Tuple

from .common import DomainValidationError, require_aware


class ClaimCandidateStatus(str, Enum):
    """The only lifecycle state supported in this increment."""

    PENDING = "pending"


@dataclass(frozen=True)
class ClaimCandidate:
    """A proposed claim derived from one or more immutable source passages.

    Candidates intentionally do not reuse ``Claim``. A Claim requires reviewed
    event, temporal, and subject data, whereas a candidate is only a proposed
    statement plus its source provenance. Future review may accept, reject, or
    transform this record without mutating it.
    """

    candidate_id: str
    proposed_statement: str
    statement_language: str
    source_passage_ids: Tuple[str, ...]
    created_at: datetime
    status: ClaimCandidateStatus = ClaimCandidateStatus.PENDING

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise DomainValidationError("candidate_id is required")
        if not self.proposed_statement.strip():
            raise DomainValidationError("proposed_statement is required")
        if not self.statement_language.strip():
            raise DomainValidationError("statement_language is required")
        if not self.source_passage_ids:
            raise DomainValidationError(
                "claim candidate requires at least one source passage"
            )
        if any(not passage_id.strip() for passage_id in self.source_passage_ids):
            raise DomainValidationError("claim candidate source passage ids are required")
        if len(set(self.source_passage_ids)) != len(self.source_passage_ids):
            raise DomainValidationError("claim candidate source passage ids must be unique")
        require_aware(self.created_at, "claim candidate created_at")
        if not isinstance(self.status, ClaimCandidateStatus):
            raise DomainValidationError("claim candidate status must be a valid status")
        if self.status is not ClaimCandidateStatus.PENDING:
            raise DomainValidationError("new claim candidates must start pending")
