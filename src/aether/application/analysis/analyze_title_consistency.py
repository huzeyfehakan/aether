"""Check whether a page states one headline or several."""

from dataclasses import dataclass
from typing import Tuple

from aether.application.analysis.title_comparison import all_titles_agree
from aether.domain.common import DomainValidationError
from aether.domain.content import Article
from aether.domain.source_data import DeclaredTitle
from aether.ports.outbound.content_repository import ContentRepository


@dataclass(frozen=True)
class TitleConsistencyAnalysis:
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

    @property
    def declared_source_count(self) -> int:
        return len(self.declared_titles)


class AnalyzeTitleConsistency:
    """Compare every title one article version declared."""

    def __init__(self, content_repository: ContentRepository) -> None:
        self._content_repository = content_repository

    def execute(
        self, article: Article, article_version_id: str
    ) -> TitleConsistencyAnalysis:
        article_version = self._content_repository.get_article_version(article_version_id)
        if article_version.article_id != article.article_id:
            raise DomainValidationError(
                "article version must belong to the article being analyzed"
            )
        source_data = self._content_repository.get_source_data(article_version_id)
        declared = source_data.declared_titles if source_data is not None else ()
        return TitleConsistencyAnalysis(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            declared_titles=declared,
            titles_agree=all_titles_agree(title.value for title in declared),
        )
