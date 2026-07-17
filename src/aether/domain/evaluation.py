"""Frozen evaluation records and their reviewed runs."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Tuple

from .common import DomainValidationError, TimeAssertion, TimeType, require_aware


class QuestionType(str, Enum):
    DIRECT_FACT = "direct_fact"
    TEMPORAL_UPDATE = "temporal_update"
    MULTI_SOURCE = "multi_source"
    CONFLICT = "conflict"
    UNSUPPORTED = "unsupported"
    FALSE_PREMISE = "false_premise"


class ExpectedDisposition(str, Enum):
    ANSWER = "answer"
    QUALIFIED_ANSWER = "qualified_answer"
    ABSTAIN = "abstain"


class EvaluationStatus(str, Enum):
    DRAFT = "draft"
    FROZEN = "frozen"
    EXECUTED = "executed"
    REVIEWED = "reviewed"
    RETIRED = "retired"


@dataclass(frozen=True)
class EvaluationRecord:
    evaluation_id: str
    question: str
    question_language: str
    question_type: QuestionType
    as_of_time: TimeAssertion
    expected_disposition: ExpectedDisposition
    evaluation_status: EvaluationStatus
    created_by: str
    created_at: datetime
    expected_claim_ids: Tuple[str, ...] = ()
    accepted_evidence_ids: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.evaluation_id.strip() or not self.question.strip():
            raise DomainValidationError("evaluation_id and question are required")
        if not self.question_language.strip() or not self.created_by.strip():
            raise DomainValidationError("question_language and created_by are required")
        require_aware(self.created_at, "evaluation created_at")
        if self.as_of_time.time_type is not TimeType.EVALUATION_AS_OF:
            raise DomainValidationError("evaluation as_of_time must use evaluation_as_of type")
        if not self.as_of_time.is_known:
            raise DomainValidationError("evaluation as_of_time must be known")
        if self.expected_disposition is ExpectedDisposition.ANSWER:
            if not self.expected_claim_ids or not self.accepted_evidence_ids:
                raise DomainValidationError(
                    "answer evaluations require expected claims and accepted evidence"
                )
        if self.expected_disposition is ExpectedDisposition.ABSTAIN:
            if self.expected_claim_ids or self.accepted_evidence_ids:
                raise DomainValidationError(
                    "abstention evaluations cannot specify expected claims or evidence"
                )
