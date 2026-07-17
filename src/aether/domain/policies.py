"""Deterministic policies that enforce answer integrity."""

from dataclasses import replace
from datetime import datetime
from typing import Iterable

from .common import DomainValidationError, require_aware
from .content import Passage
from .knowledge import (
    Claim,
    ClaimStatus,
    Evidence,
    EvidenceRelation,
    EvidenceStrength,
    ReviewState,
)


def validate_evidence_excerpt(evidence: Evidence, passage: Passage) -> None:
    """Ensure evidence points to literal text in the cited source passage."""
    if evidence.passage_id != passage.passage_id:
        raise DomainValidationError("evidence and passage identifiers do not match")
    if evidence.relevant_excerpt not in passage.text:
        raise DomainValidationError("evidence excerpt must be a literal passage substring")


def has_accepted_direct_support(evidence_records: Iterable[Evidence]) -> bool:
    return any(
        evidence.review_state is ReviewState.ACCEPTED
        and evidence.evidence_relation is EvidenceRelation.DIRECT_SUPPORT
        and evidence.evidence_strength is EvidenceStrength.DIRECT
        for evidence in evidence_records
    )


def validate_claim_for_activation(claim: Claim, evidence_records: Iterable[Evidence]) -> None:
    records = tuple(evidence_records)
    if any(evidence.claim_id != claim.claim_id for evidence in records):
        raise DomainValidationError("claim evidence must belong to the claim")
    if not has_accepted_direct_support(records):
        raise DomainValidationError("validated claim requires accepted direct-support evidence")


_ALLOWED_TRANSITIONS = {
    ClaimStatus.CANDIDATE: {ClaimStatus.VALIDATED, ClaimStatus.REJECTED},
    ClaimStatus.VALIDATED: {
        ClaimStatus.SUPERSEDED,
        ClaimStatus.DISPUTED,
        ClaimStatus.RETRACTED,
    },
    ClaimStatus.SUPERSEDED: set(),
    ClaimStatus.DISPUTED: set(),
    ClaimStatus.RETRACTED: set(),
    ClaimStatus.REJECTED: set(),
}


def transition_claim_status(
    claim: Claim, target_status: ClaimStatus, evidence_records: Iterable[Evidence]
) -> Claim:
    """Perform only auditable, allowed status transitions.

    The caller is responsible for recording the specific supporting claim relation
    for supersession, dispute, or retraction. This policy validates the evidence
    precondition common to every transition from a candidate.
    """
    if target_status not in _ALLOWED_TRANSITIONS[claim.claim_status]:
        raise DomainValidationError(
            f"cannot transition claim from {claim.claim_status.value} to {target_status.value}"
        )
    if target_status is ClaimStatus.VALIDATED:
        validate_claim_for_activation(claim, evidence_records)
    return replace(claim, claim_status=target_status)


def is_claim_eligible(
    claim: Claim, as_of: datetime, *, allow_historical: bool = False
) -> bool:
    """Determine whether a claim can support an answer at a requested time."""
    require_aware(as_of, "as_of")
    valid_at = claim.valid_time.contains(as_of)
    if valid_at is not True:
        return False
    if claim.claim_status is ClaimStatus.VALIDATED:
        return True
    return allow_historical and claim.claim_status is ClaimStatus.SUPERSEDED
