"""Check what an article declares about itself in Schema.org structured data."""

from dataclasses import dataclass
from typing import Tuple

from aether.domain.common import DomainValidationError
from aether.domain.content import Article
from aether.ports.outbound.content_repository import ContentRepository

#: Schema.org types that identify a page as an article.
ARTICLE_NODE_TYPES = ("article", "newsarticle")

#: The Article properties this report checks for, and why each is checked.
#:
#: Each one answers a question an AI system must otherwise guess at from the
#: page text: what is this article called, what is it about, when was it
#: published, when was it last changed, who wrote it, who published it, what
#: image represents it, and what language is it in. Schema.org defines all of
#: them on Article, so the check is against a published specification rather
#: than an opinion about what an article ought to declare.
CHECKED_ARTICLE_PROPERTIES = (
    "headline",
    "description",
    "datePublished",
    "dateModified",
    "author",
    "publisher",
    "image",
    "inLanguage",
)


@dataclass(frozen=True)
class StructuredDataAnalysis:
    """Whether an article declares itself to machines, and how completely.

    This reports only what the page declares. It does not check that a declared
    value is correct, and it makes no claim about how any AI system treats the
    declaration.
    """

    article_id: str
    article_version_id: str
    article_node_present: bool
    declared_node_types: Tuple[str, ...]
    declared_article_properties: Tuple[str, ...]
    all_declared_properties: Tuple[str, ...]
    missing_article_properties: Tuple[str, ...]


class AnalyzeStructuredData:
    """Read the retained declaration inventory for one article version."""

    def __init__(self, content_repository: ContentRepository) -> None:
        self._content_repository = content_repository

    def execute(
        self, article: Article, article_version_id: str
    ) -> StructuredDataAnalysis:
        article_version = self._content_repository.get_article_version(article_version_id)
        if article_version.article_id != article.article_id:
            raise DomainValidationError(
                "article version must belong to the article being analyzed"
            )
        source_data = self._content_repository.get_source_data(article_version_id)
        nodes = source_data.structured_data_nodes if source_data is not None else ()

        article_nodes = tuple(
            node for node in nodes if node.node_type.lower() in ARTICLE_NODE_TYPES
        )
        declared: set = set()
        for node in article_nodes:
            declared.update(node.property_names)

        all_props: set = set()
        for node in nodes:
            all_props.update(node.property_names)

        return StructuredDataAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            article_node_present=bool(article_nodes),
            declared_node_types=tuple(sorted({node.node_type for node in nodes})),
            declared_article_properties=tuple(sorted(declared)),
            all_declared_properties=tuple(sorted(all_props)),
            missing_article_properties=(
                tuple(
                    name
                    for name in CHECKED_ARTICLE_PROPERTIES
                    if name not in declared
                )
                if article_nodes
                else ()
            ),
        )
