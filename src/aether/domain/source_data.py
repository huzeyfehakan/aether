"""Immutable record of what a source declared to machines.

``ArticleVersion`` preserves the article as text. This sibling record preserves
what the page declared *about* that article in structured data, which text
normalization necessarily discards.

It is a separate record rather than more fields on ``ArticleVersion`` for the
same reason claim candidates are separate from claims: the two have different
lifecycles, and widening a frozen entity to carry a different concern would
disturb records and fingerprints that are already correct.

Only a normalized inventory is retained -- the type of each declared node and
the names of the properties it declares. That is what a structured-data check
needs. Retaining the raw document would store unbounded publisher data in an
immutable record and invite analyses that are no longer deterministic.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

from .common import DomainValidationError


class TitleSource(str, Enum):
    """Where in the page a title was declared."""

    DOCUMENT_TITLE = "document_title"
    OPEN_GRAPH = "open_graph"
    STRUCTURED_DATA = "structured_data"


@dataclass(frozen=True)
class DeclaredTitle:
    """One title a page declared, kept with the place it was declared.

    Ingestion picks a single title for the article record. The others are
    retained here because a page that states two different headlines is
    telling readers and machines different things, and that is only visible
    when every declaration survives.
    """

    source: TitleSource
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise DomainValidationError("declared title value is required")


@dataclass(frozen=True)
class StructuredDataNode:
    """One typed node a source declared, and the properties it carries."""

    node_type: str
    property_names: Tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.node_type or not self.node_type.strip():
            raise DomainValidationError("structured data node_type is required")
        if len(set(self.property_names)) != len(self.property_names):
            raise DomainValidationError(
                "structured data property names must be unique"
            )
        if tuple(sorted(self.property_names)) != self.property_names:
            raise DomainValidationError(
                "structured data property names must be sorted"
            )

    def declares(self, property_name: str) -> bool:
        return property_name in self.property_names


@dataclass(frozen=True)
class ArticleVersionSourceData:
    """Everything one article version declared to machines, as an inventory."""

    article_version_id: str
    structured_data_nodes: Tuple[StructuredDataNode, ...] = ()
    declared_titles: Tuple[DeclaredTitle, ...] = ()

    def __post_init__(self) -> None:
        if not self.article_version_id or not self.article_version_id.strip():
            raise DomainValidationError("source data article_version_id is required")
        sources = [title.source for title in self.declared_titles]
        if len(set(sources)) != len(sources):
            raise DomainValidationError("each title source may be declared once")
