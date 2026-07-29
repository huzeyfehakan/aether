"""Create immutable Pending Claim Candidates from source passages."""

from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

from aether.domain.claim_candidate import ClaimCandidate
from aether.domain.content import Passage
from aether.ports.outbound.claim_candidate_repository import ClaimCandidateRepository


@dataclass(frozen=True)
class CreateClaimCandidateCommand:
    candidate_id: str
    proposed_statement: str
    statement_language: str
    passages: Tuple[Passage, ...]
    created_at: datetime


class CreateClaimCandidate:
    """The first curation workflow use case.

    The use case accepts actual Passage records rather than bare identifiers so
    its provenance guarantee is enforced at the application boundary. It does
    not infer, review, validate, or otherwise alter the proposed statement.
    """

    def __init__(self, candidate_repository: ClaimCandidateRepository) -> None:
        self._candidate_repository = candidate_repository

    def execute(self, command: CreateClaimCandidateCommand) -> ClaimCandidate:
        candidate = ClaimCandidate(
            candidate_id=command.candidate_id,
            proposed_statement=command.proposed_statement,
            statement_language=command.statement_language,
            source_passage_ids=tuple(passage.passage_id for passage in command.passages),
            created_at=command.created_at,
        )
        self._candidate_repository.save(candidate)
        return candidate
