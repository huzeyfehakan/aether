"""Discoverability metrics via internal link analysis."""

from dataclasses import dataclass

from aether.domain.common import DomainValidationError
from aether.domain.content import Article
from aether.ports.outbound.content_repository import ContentRepository


@dataclass(frozen=True)
class InternalLinkAnalysisResult:
    """Deterministic internal link counts and orphan detection."""

    article_id: str
    article_version_id: str
    outgoing_link_count: int
    unique_target_count: int
    body_link_count: int
    incoming_link_count: int
    potential_orphan: bool


class AnalyzeInternalLinks:
    """Calculate internal link metrics without applying a threshold."""

    def __init__(self, content_repository: ContentRepository) -> None:
        self._content_repository = content_repository

    def execute(self, article: Article, article_version_id: str) -> InternalLinkAnalysisResult:
        article_version = self._content_repository.get_article_version(article_version_id)
        if article_version.article_id != article.article_id:
            raise DomainValidationError(
                "article version must belong to the article being analyzed"
            )

        source_data = self._content_repository.get_source_data(article_version_id)
        if source_data is None:
            raise DomainValidationError("source data must exist for link analysis")

        links = source_data.internal_links
        outgoing_link_count = len(links)
        unique_targets = {link.target_url for link in links}
        body_link_count = sum(1 for link in links if link.is_in_body)

        # Count incoming links from other articles stored in the repository
        # Only check current versions of other articles for performance
        # (This is bound by the process-scoped ContentRepository in Aether)
        incoming_link_count = 0
        canonical_source = article.canonical_source
        
        # A simple iteration over all articles. In a real DB this would be a query.
        for other_article in self._content_repository.list_articles_by_publisher(article.publisher):
            if other_article.article_id == article.article_id:
                continue
            if other_article.current_version_id:
                other_source_data = self._content_repository.get_source_data(other_article.current_version_id)
                if other_source_data:
                    for link in other_source_data.internal_links:
                        if link.target_url == canonical_source:
                            incoming_link_count += 1
                            break

        return InternalLinkAnalysisResult(
            article_id=article.article_id,
            article_version_id=article_version.article_version_id,
            outgoing_link_count=outgoing_link_count,
            unique_target_count=len(unique_targets),
            body_link_count=body_link_count,
            incoming_link_count=incoming_link_count,
            potential_orphan=(incoming_link_count == 0),
        )
