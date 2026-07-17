"""Immutable publisher-source records."""

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from typing import Optional, Tuple
from urllib.parse import urlparse

from .common import DomainValidationError, require_aware


def _require_non_empty(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise DomainValidationError(f"{field_name} is required")


def _validate_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise DomainValidationError("canonical_source must be an absolute HTTP(S) URL")


@dataclass(frozen=True)
class ArticleVersion:
    """An immutable source snapshot for a logical article."""

    article_version_id: str
    article_id: str
    version_number: int
    title: str
    body: str
    observed_at: datetime
    source_published_at: datetime
    source_updated_at: Optional[datetime] = None
    source_available: bool = True
    content_fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        _require_non_empty(self.article_version_id, "article_version_id")
        _require_non_empty(self.article_id, "article_id")
        _require_non_empty(self.title, "title")
        _require_non_empty(self.body, "body")
        if self.version_number < 1:
            raise DomainValidationError("version_number must be positive")
        require_aware(self.observed_at, "observed_at")
        require_aware(self.source_published_at, "source_published_at")
        if self.source_updated_at is not None:
            require_aware(self.source_updated_at, "source_updated_at")
            if self.source_updated_at < self.source_published_at:
                raise DomainValidationError(
                    "source_updated_at cannot precede source_published_at"
                )
        snapshot = f"{self.title}\n{self.body}".encode("utf-8")
        object.__setattr__(self, "content_fingerprint", sha256(snapshot).hexdigest())


@dataclass(frozen=True)
class Article:
    """Stable identity for a publisher work; content lives in ArticleVersion."""

    article_id: str
    publisher: str
    canonical_source: str
    original_language: str
    article_type: str
    initial_published_at: datetime
    ingested_at: datetime
    version_ids: Tuple[str, ...] = ()
    current_version_id: Optional[str] = None

    def __post_init__(self) -> None:
        _require_non_empty(self.article_id, "article_id")
        _require_non_empty(self.publisher, "publisher")
        _validate_url(self.canonical_source)
        _require_non_empty(self.original_language, "original_language")
        _require_non_empty(self.article_type, "article_type")
        require_aware(self.initial_published_at, "initial_published_at")
        require_aware(self.ingested_at, "ingested_at")
        if len(set(self.version_ids)) != len(self.version_ids):
            raise DomainValidationError("article version_ids must be unique")
        if self.current_version_id is not None and self.current_version_id not in self.version_ids:
            raise DomainValidationError("current_version_id must reference an article version")


@dataclass(frozen=True)
class Passage:
    """An exact, citeable excerpt from a single article version."""

    passage_id: str
    article_version_id: str
    ordinal_position: int
    text: str
    location_anchor: str
    language: str
    content_fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        _require_non_empty(self.passage_id, "passage_id")
        _require_non_empty(self.article_version_id, "article_version_id")
        if self.ordinal_position < 0:
            raise DomainValidationError("ordinal_position cannot be negative")
        _require_non_empty(self.text, "passage text")
        _require_non_empty(self.location_anchor, "location_anchor")
        _require_non_empty(self.language, "language")
        object.__setattr__(
            self, "content_fingerprint", sha256(self.text.encode("utf-8")).hexdigest()
        )
