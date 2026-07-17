"""Shared domain primitives.

All timestamps used by the domain are timezone-aware.  This is intentional:
the product must not silently conflate publication, event, and evaluation time.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class DomainValidationError(ValueError):
    """Raised when a record would violate a frozen domain invariant."""


class TimeType(str, Enum):
    PUBLICATION = "publication"
    UPDATE = "update"
    EVIDENCE_AVAILABILITY = "evidence_availability"
    EVENT = "event"
    CLAIM_VALIDITY = "claim_validity"
    SYSTEM_RECORD = "system_record"
    EVALUATION_AS_OF = "evaluation_as_of"


class TimePrecision(str, Enum):
    EXACT = "exact"
    DATE = "date"
    MONTH = "month"
    APPROXIMATE = "approximate"
    UNKNOWN = "unknown"


class TimeSourceBasis(str, Enum):
    PUBLISHER_STATED = "publisher_stated"
    SOURCE_INFERRED = "source_inferred"
    MANUALLY_REVIEWED = "manually_reviewed"
    UNKNOWN = "unknown"


def require_aware(timestamp: datetime, field_name: str) -> None:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise DomainValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True)
class TimeAssertion:
    """A sourced statement about time, with unknown time represented explicitly."""

    time_type: TimeType
    precision: TimePrecision
    source_basis: TimeSourceBasis
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise DomainValidationError("time confidence must be between 0 and 1")
        if self.start is not None:
            require_aware(self.start, "time start")
        if self.end is not None:
            require_aware(self.end, "time end")
        if self.end is not None and self.start is None:
            raise DomainValidationError("time end requires a time start")
        if self.start is not None and self.end is not None and self.end < self.start:
            raise DomainValidationError("time end cannot precede time start")
        if self.precision is TimePrecision.UNKNOWN and self.start is not None:
            raise DomainValidationError("unknown time precision cannot have a start")
        if self.precision is not TimePrecision.UNKNOWN and self.start is None:
            raise DomainValidationError("known time precision requires a start")

    @property
    def is_known(self) -> bool:
        return self.start is not None

    def contains(self, instant: datetime) -> Optional[bool]:
        """Return None when the assertion is explicitly unknown."""
        require_aware(instant, "instant")
        if self.start is None:
            return None
        if instant < self.start:
            return False
        return self.end is None or instant <= self.end
