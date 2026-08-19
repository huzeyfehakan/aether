"""Register source snapshots without mutating prior publisher content."""

from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
import json
from typing import Optional, Tuple

from aether.domain.content import Article, ArticleVersion, Passage
from aether.domain.source_data import (
    ArticleVersionSourceData,
    DeclaredDescription,
    DeclaredHeading,
    DeclaredTitle,
    StructuredDataNode,
    InternalLink,
)
from aether.ports.outbound.content_repository import ContentRepository


@dataclass(frozen=True)
class SourceArticleSnapshot:
    """Trusted input from a source connector or controlled import process."""

    publisher: str
    canonical_source: str
    original_language: str
    article_type: str
    title: str
    body: str
    observed_at: datetime
    source_published_at: Optional[datetime]
    source_updated_at: Optional[datetime] = None
    source_available: bool = True
    author: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    structured_data_nodes: Tuple[StructuredDataNode, ...] = ()
    declared_titles: Tuple[DeclaredTitle, ...] = ()
    declared_descriptions: Tuple[DeclaredDescription, ...] = ()
    declared_headings: Tuple[DeclaredHeading, ...] = ()
    internal_links: Tuple[InternalLink, ...] = ()
    table_word_count: int = 0
    list_word_count: int = 0
    blockquote_word_count: int = 0
    answered_question_heading_count: int = 0
    unanswered_question_heading_count: int = 0


@dataclass(frozen=True)
class RegistrationResult:
    article: Article
    article_version: ArticleVersion
    passages: Tuple[Passage, ...]
    version_created: bool


class RegisterSourceSnapshot:
    """Application use case for the first two pipeline stages.

    It is deliberately deterministic: the same snapshot can be delivered more
    than once without creating a second Article Version or duplicate Passages.
    """

    def __init__(self, content_repository: ContentRepository) -> None:
        self._content_repository = content_repository

    def execute(self, snapshot: SourceArticleSnapshot) -> RegistrationResult:
        existing_article = self._content_repository.find_article_by_canonical_source(
            snapshot.canonical_source
        )
        if existing_article is None:
            article = Article(
                article_id=self._article_id(snapshot.canonical_source),
                publisher=snapshot.publisher,
                canonical_source=snapshot.canonical_source,
                original_language=snapshot.original_language,
                article_type=snapshot.article_type,
                initial_published_at=snapshot.source_published_at,
                ingested_at=snapshot.observed_at,
            )
            return self._register_new_version(article, snapshot)

        current_version = self._content_repository.get_article_version(
            existing_article.current_version_id
        )
        candidate_fingerprint = self._fingerprint(
            snapshot.title,
            snapshot.body,
            snapshot.author,
            snapshot.description,
            snapshot.keywords,
        )
        if current_version.content_fingerprint == candidate_fingerprint:
            passages = self._content_repository.list_passages_for_version(
                current_version.article_version_id
            )
            return RegistrationResult(
                article=existing_article,
                article_version=current_version,
                passages=passages,
                version_created=False,
            )
        return self._register_new_version(existing_article, snapshot)

    def _register_new_version(
        self, article: Article, snapshot: SourceArticleSnapshot
    ) -> RegistrationResult:
        version_number = len(article.version_ids) + 1
        version = ArticleVersion(
            article_version_id=f"{article.article_id}:v{version_number}",
            article_id=article.article_id,
            version_number=version_number,
            title=snapshot.title,
            body=snapshot.body,
            observed_at=snapshot.observed_at,
            source_published_at=snapshot.source_published_at,
            source_updated_at=snapshot.source_updated_at,
            source_available=snapshot.source_available,
            author=snapshot.author,
            description=snapshot.description,
            keywords=snapshot.keywords,
        )
        passages = self._create_passages(version, article.original_language)
        updated_article = replace(
            article,
            version_ids=article.version_ids + (version.article_version_id,),
            current_version_id=version.article_version_id,
        )
        self._content_repository.save_article(updated_article)
        self._content_repository.save_article_version(version)
        self._content_repository.save_passages(passages)
        # Declared structured data is retained alongside the version but stays
        # out of the content fingerprint, which describes the article text.
        self._content_repository.save_source_data(
            ArticleVersionSourceData(
                article_version_id=version.article_version_id,
                structured_data_nodes=snapshot.structured_data_nodes,
                declared_titles=snapshot.declared_titles,
                declared_descriptions=snapshot.declared_descriptions,
                declared_headings=snapshot.declared_headings,
                internal_links=snapshot.internal_links,
                table_word_count=snapshot.table_word_count,
                list_word_count=snapshot.list_word_count,
                blockquote_word_count=snapshot.blockquote_word_count,
                answered_question_heading_count=snapshot.answered_question_heading_count,
                unanswered_question_heading_count=snapshot.unanswered_question_heading_count,
            )
        )
        return RegistrationResult(
            article=updated_article,
            article_version=version,
            passages=passages,
            version_created=True,
        )

    @staticmethod
    def _article_id(canonical_source: str) -> str:
        return "article_" + sha256(canonical_source.encode("utf-8")).hexdigest()

    @staticmethod
    def _fingerprint(
        title: str,
        body: str,
        author: Optional[str] = None,
        description: Optional[str] = None,
        keywords: Optional[str] = None,
    ) -> str:
        snapshot = json.dumps(
            [title, body, author, description, keywords],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return sha256(snapshot.encode("utf-8")).hexdigest()

    @staticmethod
    def _create_passages(
        article_version: ArticleVersion, language: str
    ) -> Tuple[Passage, ...]:
        paragraphs = tuple(
            paragraph.strip()
            for paragraph in article_version.body.split("\n\n")
            if paragraph.strip()
        )
        return tuple(
            Passage(
                passage_id=f"{article_version.article_version_id}:p{position}",
                article_version_id=article_version.article_version_id,
                ordinal_position=position,
                text=paragraph,
                location_anchor=f"paragraph:{position + 1}",
                language=language,
            )
            for position, paragraph in enumerate(paragraphs)
        )
