"""Check whether a page states one headline and one summary, or several.

A page declares its headline in the document title, in Open Graph and in
structured data, and its summary in as many places again. Ingestion keeps one
of each. This reads all of them and reports when they do not agree.
"""

from dataclasses import dataclass
from typing import Tuple

from aether.application.analysis.declared_text_comparison import all_declared_values_agree
from aether.domain.common import DomainValidationError
from aether.domain.content import Article
from aether.domain.source_data import DeclaredDescription, DeclaredTitle
from aether.ports.outbound.content_repository import ContentRepository


@dataclass(frozen=True)
class DeclaredConsistencyAnalysis:
    """The titles a page declared, and whether they carry one headline.

    Formatting differences are not disagreements: the comparison decodes
    character references, collapses whitespace, writes separators one way,
    folds case, and allows a site name to be present in some declarations and
    absent from others. Only a genuinely different headline is reported.
    """

    article_id: str
    article_version_id: str
    declared_titles: Tuple[DeclaredTitle, ...]
    titles_agree: bool
    declared_descriptions: Tuple[DeclaredDescription, ...] = ()
    descriptions_agree: bool = True

    @property
    def declared_source_count(self) -> int:
        return len(self.declared_titles)

    @property
    def declared_description_count(self) -> int:
        return len(self.declared_descriptions)


class AnalyzeDeclaredConsistency:
    """Compare every title one article version declared."""

    def __init__(self, content_repository: ContentRepository) -> None:
        self._content_repository = content_repository

    def execute(
        self, article: Article, article_version_id: str
    ) -> DeclaredConsistencyAnalysis:
        article_version = self._content_repository.get_article_version(article_version_id)
        if article_version.article_id != article.article_id:
            raise DomainValidationError(
                "article version must belong to the article being analyzed"
            )
        source_data = self._content_repository.get_source_data(article_version_id)
        declared = source_data.declared_titles if source_data is not None else ()
        described = (
            source_data.declared_descriptions if source_data is not None else ()
        )
        return DeclaredConsistencyAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            declared_titles=declared,
            titles_agree=all_declared_values_agree(title.value for title in declared),
            declared_descriptions=described,
            descriptions_agree=all_declared_values_agree(
                description.value for description in described
            ),
        )
