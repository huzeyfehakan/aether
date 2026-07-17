"""Curated, evidence-backed knowledge records."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Tuple

from .common import DomainValidationError, TimeAssertion, require_aware


def _require_non_empty(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise DomainValidationError(f"{field_name} is required")


class EntityResolutionState(str, Enum):
    CANDIDATE = "candidate"
    CANONICAL = "canonical"
    MERGED = "merged"
    DEPRECATED = "deprecated"


class EventState(str, Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    CLOSED = "closed"
    MERGED = "merged"
    ARCHIVED = "archived"


class ClaimStatus(str, Enum):
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    SUPERSEDED = "superseded"
    DISPUTED = "disputed"
    RETRACTED = "retracted"
    REJECTED = "rejected"


class EvidenceRelation(str, Enum):
    DIRECT_SUPPORT = "direct_support"
    QUALIFICATION = "qualification"
    CONTRADICTION = "contradiction"
    CORRECTION = "correction"
    CONTEXT = "context"


class EvidenceStrength(str, Enum):
    DIRECT = "direct"
    PARTIAL = "partial"
    CONTEXTUAL = "contextual"


class ReviewState(str, Enum):
    CANDIDATE = "candidate"
    ACCEPTED = "accepted"
    REVOKED = "revoked"


class ClaimRelationType(str, Enum):
    SUPERSEDES = "supersedes"
    CORRECTS = "corrects"
    CONTRADICTS = "contradicts"
    QUALIFIES = "qualifies"


@dataclass(frozen=True)
class Entity:
    entity_id: str
    canonical_name: str
    entity_type: str
    primary_language: str
    resolution_state: EntityResolutionState
    aliases: Tuple[str, ...] = ()
    successor_entity_id: Optional[str] = None

    def __post_init__(self) -> None:
        _require_non_empty(self.entity_id, "entity_id")
        _require_non_empty(self.canonical_name, "canonical_name")
        _require_non_empty(self.entity_type, "entity_type")
        _require_non_empty(self.primary_language, "primary_language")
        if len(set(self.aliases)) != len(self.aliases):
            raise DomainValidationError("entity aliases must be unique")
        if self.resolution_state is EntityResolutionState.MERGED and not self.successor_entity_id:
            raise DomainValidationError("merged entity requires successor_entity_id")


@dataclass(frozen=True)
class Event:
    event_id: str
    canonical_name: str
    event_type: str
    event_scope: str
    event_time: TimeAssertion
    event_state: EventState
    primary_location_entity_id: Optional[str] = None

    def __post_init__(self) -> None:
        _require_non_empty(self.event_id, "event_id")
        _require_non_empty(self.canonical_name, "canonical_name")
        _require_non_empty(self.event_type, "event_type")
        _require_non_empty(self.event_scope, "event_scope")


@dataclass(frozen=True)
class Claim:
    claim_id: str
    canonical_statement: str
    claim_language: str
    claim_type: str
    modality: str
    primary_event_id: str
    claim_status: ClaimStatus
    created_at: datetime
    provenance_method: str
    valid_time: TimeAssertion
    primary_subject_entity_id: Optional[str] = None
    unresolved_subject: Optional[str] = None
    related_entity_ids: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty(self.claim_id, "claim_id")
        _require_non_empty(self.canonical_statement, "canonical_statement")
        _require_non_empty(self.claim_language, "claim_language")
        _require_non_empty(self.claim_type, "claim_type")
        _require_non_empty(self.modality, "modality")
        _require_non_empty(self.primary_event_id, "primary_event_id")
        _require_non_empty(self.provenance_method, "provenance_method")
        require_aware(self.created_at, "claim created_at")
        if not self.primary_subject_entity_id and not self.unresolved_subject:
            raise DomainValidationError(
                "claim requires a primary_subject_entity_id or unresolved_subject"
            )
        if self.primary_subject_entity_id and self.unresolved_subject:
            raise DomainValidationError(
                "claim cannot have both resolved and unresolved primary subject"
            )
        if len(set(self.related_entity_ids)) != len(self.related_entity_ids):
            raise DomainValidationError("related_entity_ids must be unique")


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    claim_id: str
    passage_id: str
    evidence_relation: EvidenceRelation
    evidence_strength: EvidenceStrength
    relevant_excerpt: str
    created_at: datetime
    review_state: ReviewState

    def __post_init__(self) -> None:
        _require_non_empty(self.evidence_id, "evidence_id")
        _require_non_empty(self.claim_id, "claim_id")
        _require_non_empty(self.passage_id, "passage_id")
        _require_non_empty(self.relevant_excerpt, "relevant_excerpt")
        require_aware(self.created_at, "evidence created_at")
        if (
            self.evidence_relation is EvidenceRelation.DIRECT_SUPPORT
            and self.evidence_strength is not EvidenceStrength.DIRECT
        ):
            raise DomainValidationError(
                "direct support evidence must have direct strength"
            )


@dataclass(frozen=True)
class ClaimRelation:
    relation_id: str
    source_claim_id: str
    target_claim_id: str
    relation_type: ClaimRelationType
    basis_evidence_id: str
    created_at: datetime

    def __post_init__(self) -> None:
        _require_non_empty(self.relation_id, "relation_id")
        _require_non_empty(self.source_claim_id, "source_claim_id")
        _require_non_empty(self.target_claim_id, "target_claim_id")
        _require_non_empty(self.basis_evidence_id, "basis_evidence_id")
        require_aware(self.created_at, "claim relation created_at")
        if self.source_claim_id == self.target_claim_id:
            raise DomainValidationError("a claim cannot relate to itself")
