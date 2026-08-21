"""Deterministically normalize raw article HTML into existing source snapshots."""

from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from aether.application.ingestion.register_source_snapshot import (
    RegisterSourceSnapshot,
    RegistrationResult,
    SourceArticleSnapshot,
)
from aether.domain.common import DomainValidationError, require_aware
from aether.domain.source_data import (
    DeclaredDescription,
    DeclaredHeading,
    DeclaredTitle,
    DescriptionSource,
    StructuredDataNode,
    TitleSource,
    InternalLink,
)
from aether.ports.outbound.content_repository import ContentRepository


@dataclass(frozen=True)
class RawHtmlArticle:
    """Raw source input plus the source context HTML cannot reliably provide."""

    html: str
    source_url: str
    publisher: str
    article_type: str
    observed_at: datetime
    fallback_language: Optional[str] = None
    fallback_published_at: Optional[datetime] = None
    fallback_updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.html.strip():
            raise DomainValidationError("raw article html is required")
        if not self.source_url.strip():
            raise DomainValidationError("raw article source_url is required")
        if not self.publisher.strip():
            raise DomainValidationError("raw article publisher is required")
        if not self.article_type.strip():
            raise DomainValidationError("raw article article_type is required")
        require_aware(self.observed_at, "raw article observed_at")
        if self.fallback_published_at is not None:
            require_aware(self.fallback_published_at, "fallback_published_at")
        if self.fallback_updated_at is not None:
            require_aware(self.fallback_updated_at, "fallback_updated_at")


@dataclass(frozen=True)
class NormalizedHtmlArticle:
    """Deterministic source fields ready for the existing ingestion use case."""

    canonical_source: str
    title: str
    body: str
    language: str
    published_at: Optional[datetime]
    updated_at: Optional[datetime]
    author: Optional[str]
    description: Optional[str]
    keywords: Optional[str]
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


class _ArticleHtmlCollector(HTMLParser):
    """Collect common publication metadata and visible paragraph text only."""

    _SKIPPED_TAGS = {"script", "style", "noscript", "template"}

    # HTML sectioning and link elements whose paragraphs are, by specification,
    # not article prose: navigation, complementary content, page banners,
    # footers, media captions, and link-wrapped teaser cards. Publishers place
    # recommendation cards and legal boilerplate in these containers, and they
    # otherwise share the article's container. This is markup semantics only:
    # no class names, publisher names, or URL patterns are consulted.
    _NON_BODY_TAGS = {"a", "aside", "figcaption", "footer", "header", "nav"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.metadata: Dict[str, str] = {}
        self.canonical_source: Optional[str] = None
        self.html_language: Optional[str] = None
        self.time_values: List[str] = []
        self.json_ld_documents: List[str] = []
        self.application_json_documents: List[str] = []
        self.title_parts: List[str] = []
        # (containment priority, heading level, text)
        self.headings: List[Tuple[int, int, str]] = []
        self.paragraphs: List[Tuple[int, str]] = []
        self._article_depth = 0
        self._main_depth = 0
        self._head_depth = 0
        self._skip_depth = 0
        self._non_body_depth = 0
        self._in_title = False
        self._title_captured = False
        self._heading_parts: Optional[List[str]] = None
        self._heading_priority = 0
        self._heading_level = 0
        self._heading_is_body = True
        self._paragraph_parts: Optional[List[str]] = None
        self._paragraph_priority = 0
        self._paragraph_is_body = True
        self._json_ld_parts: Optional[List[str]] = None
        self._application_json_parts: Optional[List[str]] = None

        self._table_depth = 0
        self._list_depth = 0
        self._blockquote_depth = 0
        self.table_word_count = 0
        self.list_word_count = 0
        self.blockquote_word_count = 0
        self.links: List[Tuple[str, bool]] = []
        
        self._pending_question_heading = False
        self.answered_question_heading_count = 0
        self.unanswered_question_heading_count = 0

    def _containment_priority(self) -> int:
        return 3 if self._article_depth else 2 if self._main_depth else 1

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attributes = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag in self._SKIPPED_TAGS:
            script_type = attributes.get("type", "").lower().split(";", 1)[0].strip()
            if tag == "script" and script_type == "application/ld+json":
                self._json_ld_parts = []
            elif tag == "script" and script_type == "application/json":
                self._application_json_parts = []
            self._skip_depth += 1
            return
        if tag == "html" and attributes.get("lang"):
            self.html_language = attributes["lang"].strip()
        if tag == "meta":
            key = (
                attributes.get("property")
                or attributes.get("name")
                or attributes.get("itemprop")
            )
            if key and attributes.get("content"):
                self.metadata[key.lower()] = attributes["content"]
        if tag == "link" and self.canonical_source is None:
            if "canonical" in _rel_tokens(attributes.get("rel", "")):
                self.canonical_source = attributes.get("href", "").strip() or None
        if tag == "time" and attributes.get("datetime"):
            self.time_values.append(attributes["datetime"].strip())
        if tag in self._NON_BODY_TAGS:
            self._non_body_depth += 1
        if tag == "article":
            self._article_depth += 1
        elif tag == "main":
            self._main_depth += 1
        elif tag == "head":
            self._head_depth += 1
        elif tag == "title" and self._head_depth and not self._title_captured:
            self._in_title = True
        elif tag in _HEADING_TAGS:
            self._heading_parts = []
            self._heading_priority = self._containment_priority()
            self._heading_level = int(tag[1])
            self._heading_is_body = self._non_body_depth == 0
        elif tag == "p":
            self._paragraph_parts = []
            self._paragraph_priority = self._containment_priority()
            self._paragraph_is_body = self._non_body_depth == 0

        if self._pending_question_heading:
            if tag in {"p", "ul", "ol"}:
                self.answered_question_heading_count += 1
                self._pending_question_heading = False
            elif tag not in {"a", "strong", "em", "span", "br", "i", "b", "u"}:
                self.unanswered_question_heading_count += 1
                self._pending_question_heading = False

        if tag == "table":
            self._table_depth += 1
        elif tag in {"ul", "ol", "dl"}:
            self._list_depth += 1
        elif tag == "blockquote":
            self._blockquote_depth += 1
        elif tag == "a":
            href = attributes.get("href")
            if href:
                self.links.append((href, self._non_body_depth == 0))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._SKIPPED_TAGS:
            if tag == "script" and self._json_ld_parts is not None:
                self.json_ld_documents.append("".join(self._json_ld_parts))
                self._json_ld_parts = None
            if tag == "script" and self._application_json_parts is not None:
                self.application_json_documents.append(
                    "".join(self._application_json_parts)
                )
                self._application_json_parts = None
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag in self._NON_BODY_TAGS:
            self._non_body_depth = max(0, self._non_body_depth - 1)
        if tag == "p" and self._paragraph_parts is not None:
            text = _normalize_text(" ".join(self._paragraph_parts))
            if text and self._paragraph_is_body:
                self.paragraphs.append((self._paragraph_priority, text))
            self._paragraph_parts = None
            self._paragraph_priority = 0
            self._paragraph_is_body = True
        elif tag in _HEADING_TAGS and self._heading_parts is not None:
            text = _normalize_text(" ".join(self._heading_parts))
            if text and self._heading_is_body:
                self.headings.append(
                    (self._heading_priority, self._heading_level, text)
                )
            self._heading_parts = None
            self._heading_priority = 0
            self._heading_level = 0
            self._heading_is_body = True
            
            if text and text.strip().endswith("?"):
                self._pending_question_heading = True
        elif tag == "title" and self._in_title:
            self._in_title = False
            self._title_captured = True
        elif tag == "head":
            self._head_depth = max(0, self._head_depth - 1)
        elif tag == "article":
            self._article_depth = max(0, self._article_depth - 1)
        elif tag == "main":
            self._main_depth = max(0, self._main_depth - 1)
            
        if tag == "table":
            self._table_depth = max(0, self._table_depth - 1)
        elif tag in {"ul", "ol", "dl"}:
            self._list_depth = max(0, self._list_depth - 1)
        elif tag == "blockquote":
            self._blockquote_depth = max(0, self._blockquote_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            if self._json_ld_parts is not None:
                self._json_ld_parts.append(data)
            if self._application_json_parts is not None:
                self._application_json_parts.append(data)
            return
        if self._in_title:
            self.title_parts.append(data)
        if self._heading_parts is not None:
            self._heading_parts.append(data)
        if self._paragraph_parts is not None:
            self._paragraph_parts.append(data)
            
        words = len(data.split())
        if self._table_depth > 0:
            self.table_word_count += words
        if self._list_depth > 0:
            self.list_word_count += words
        if self._blockquote_depth > 0:
            self.blockquote_word_count += words


#: Heading tags, in outline order.
_HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _normalize_json_ld_text(value: str) -> str:
    """Decode character references in a JSON-LD string value.

    JSON-LD lives inside a ``<script>`` element, where the HTML parser does not
    resolve character references. Every other text source in this module
    arrives already decoded, so a single decode keeps JSON-LD values consistent
    with them. Only one pass is applied: repeating it would corrupt text that
    legitimately contains an escaped entity.
    """
    return _normalize_text(unescape(value))


def _rel_tokens(value: str) -> Tuple[str, ...]:
    """Split an HTML ``rel`` attribute into its space-separated link types."""
    return tuple(token.lower() for token in value.split())


def canonical_url_from_html(html: str, base_url: Optional[str] = None) -> Optional[str]:
    """Return the first declared canonical URL, resolved against ``base_url``.

    This is the single canonical-link contract for the whole system: ``rel`` is
    matched as a link-type token rather than a substring, the first non-blank
    declaration in document order wins, and a relative href is resolved only
    when a base URL is supplied.
    """

    collector = _ArticleHtmlCollector()
    collector.feed(html)
    collector.close()
    if collector.canonical_source is None:
        return None
    if base_url is None:
        return collector.canonical_source
    return urljoin(base_url, collector.canonical_source)


# The ISO-8601 extended calendar date, matched exactly. The pattern is used in
# preference to date.fromisoformat because that function accepts progressively
# more ISO-8601 spellings from Python 3.11 onwards, which would make extraction
# depend on the interpreter version rather than on the published value.
_DATE_ONLY_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def _parse_source_timestamp(
    value: str, field_name: str, *, normalize_naive_to_utc: bool = False
) -> datetime:
    """Parse a publisher timestamp, normalizing a date-only value to midnight UTC.

    Schema.org types ``datePublished`` and ``dateModified`` as Date or DateTime,
    and publishers such as TRT Çocuk Ebeveyn Akademisi publish the Date form. A
    date states no time of day, so it is anchored at midnight UTC. This records
    an instant the publisher did not state, which is acceptable here because the
    product exposes only the calendar date and whether one is available.

    A value that states a time of day without a timezone remains an error unless
    the caller explicitly opts into deterministic UTC normalization.
    """
    normalized = value.strip().replace("Z", "+00:00")
    if _DATE_ONLY_PATTERN.match(normalized):
        try:
            parsed_date = datetime.strptime(normalized, "%Y-%m-%d")
        except ValueError as error:
            raise DomainValidationError(f"{field_name} must be ISO-8601") from error
        return parsed_date.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise DomainValidationError(f"{field_name} must be ISO-8601") from error
    if normalize_naive_to_utc and parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    require_aware(parsed, field_name)
    return parsed


class HtmlArticleNormalizer:
    """Normalize common publisher HTML conventions without semantic inference."""

    _PUBLISHED_META_KEYS = ("article:published_time", "datepublished")
    _UPDATED_META_KEYS = ("article:modified_time", "datemodified")
    _TITLE_META_KEYS = ("og:title", "twitter:title")
    _AUTHOR_META_KEYS = ("article:author", "author")
    _DESCRIPTION_META_KEYS = ("og:description", "description", "twitter:description")
    _KEYWORD_META_KEYS = ("keywords",)

    def normalize(self, raw_article: RawHtmlArticle) -> NormalizedHtmlArticle:
        collector = _ArticleHtmlCollector()
        collector.feed(raw_article.html)
        collector.close()

        # og:title outranks a JSON-LD headline deliberately. Both are declared
        # by the publisher, but og:title arrives through the HTML parser with
        # its character references already resolved, whereas a headline is only
        # as well-formed as the publisher's own JSON-LD escaping.
        title = self._first_metadata(collector.metadata, self._TITLE_META_KEYS)
        title = title or self._json_ld_text(collector.json_ld_documents, "headline")
        title = title or _normalize_text(" ".join(collector.title_parts))
        title = title or self._innermost_heading(collector.headings)
        if not title:
            raise DomainValidationError("raw article html has no title")

        body = self._body_from(collector.paragraphs)
        if not body:
            body = self._body_from_application_json(
                collector.application_json_documents, raw_article.source_url
            )
        if not body:
            raise DomainValidationError("raw article html has no visible paragraphs")

        language = self._language(collector, raw_article)
        if not language or not language.strip():
            raise DomainValidationError("raw article html has no language or fallback_language")

        published_at = self._published_at(collector, raw_article)
        updated_at = self._updated_at(collector, raw_article)
        canonical_source = self._canonical_source(
            collector.canonical_source, raw_article.source_url
        )
        
        base_domain = urlparse(canonical_source).netloc
        internal_links_list = []
        for href, is_body in collector.links:
            parsed_href = urlparse(href)
            if not parsed_href.netloc or parsed_href.netloc == base_domain:
                resolved_url = urljoin(canonical_source, href)
                internal_links_list.append(InternalLink(target_url=resolved_url, is_in_body=is_body))
                
        return NormalizedHtmlArticle(
            canonical_source=canonical_source,
            title=title,
            body=body,
            language=language.strip(),
            published_at=published_at,
            updated_at=updated_at,
            author=(
                self._json_ld_author(collector.json_ld_documents)
                or self._first_metadata(collector.metadata, self._AUTHOR_META_KEYS)
            ),
            description=(
                self._json_ld_text(collector.json_ld_documents, "description")
                or self._first_metadata(collector.metadata, self._DESCRIPTION_META_KEYS)
            ),
            keywords=self._first_metadata(collector.metadata, self._KEYWORD_META_KEYS),
            structured_data_nodes=self._structured_data_nodes(
                collector.json_ld_documents
            ),
            declared_titles=self._declared_titles(collector),
            declared_descriptions=self._declared_descriptions(collector),
            declared_headings=self._declared_headings(collector),
            internal_links=tuple(internal_links_list),
            table_word_count=collector.table_word_count,
            list_word_count=collector.list_word_count,
            blockquote_word_count=collector.blockquote_word_count,
            answered_question_heading_count=collector.answered_question_heading_count,
            unanswered_question_heading_count=collector.unanswered_question_heading_count,
        )

    @staticmethod
    def _declared_headings(
        collector: "_ArticleHtmlCollector",
    ) -> Tuple[DeclaredHeading, ...]:
        """Headings from the article's own container, in document order.

        The same containment ranking that selects body paragraphs selects
        headings, so a site banner heading is not mistaken for the article's.
        """
        if not collector.headings:
            return ()
        top = max(priority for priority, _, _ in collector.headings)
        return tuple(
            DeclaredHeading(level=level, text=text)
            for priority, level, text in collector.headings
            if priority == top
        )

    @classmethod
    def _declared_descriptions(
        cls, collector: "_ArticleHtmlCollector"
    ) -> Tuple[DeclaredDescription, ...]:
        """Keep every summary the page declared, not just the one that wins."""
        candidates = (
            (
                DescriptionSource.META_DESCRIPTION,
                collector.metadata.get("description") or "",
            ),
            (DescriptionSource.OPEN_GRAPH, collector.metadata.get("og:description") or ""),
            (
                DescriptionSource.TWITTER,
                collector.metadata.get("twitter:description") or "",
            ),
            (
                DescriptionSource.STRUCTURED_DATA,
                cls._json_ld_text(collector.json_ld_documents, "description") or "",
            ),
        )
        return tuple(
            DeclaredDescription(source=source, value=value)
            for source, value in candidates
            if value and value.strip()
        )

    @classmethod
    def _declared_titles(
        cls, collector: "_ArticleHtmlCollector"
    ) -> Tuple[DeclaredTitle, ...]:
        """Keep every title the page declared, not just the one that wins.

        Ingestion selects a single title for the article record. A page that
        states two different headlines is telling readers and machines
        different things, and that is only visible if the losing declarations
        survive.
        """
        candidates = (
            (
                TitleSource.DOCUMENT_TITLE,
                _normalize_text(" ".join(collector.title_parts)),
            ),
            (TitleSource.OPEN_GRAPH, collector.metadata.get("og:title") or ""),
            (
                TitleSource.STRUCTURED_DATA,
                cls._json_ld_text(collector.json_ld_documents, "headline") or "",
            ),
        )
        return tuple(
            DeclaredTitle(source=source, value=value)
            for source, value in candidates
            if value and value.strip()
        )

    @classmethod
    def _structured_data_nodes(
        cls, documents: List[str]
    ) -> Tuple[StructuredDataNode, ...]:
        """Inventory the typed nodes a page declares, in document order.

        Only the node type and its property names are retained. Values are not,
        because a structured-data check asks what a publisher declared, not what
        the declaration said, and the values already reach the report through
        the fields that read them.
        """
        nodes = []
        for document in documents:
            try:
                payload = json.loads(document)
            except json.JSONDecodeError:
                continue
            for value in cls._json_values_in_document_order(payload):
                node_type = cls._node_type_of(value)
                if node_type is None:
                    continue
                property_names = tuple(
                    sorted(key for key in value if not key.startswith("@"))
                )
                nodes.append(
                    StructuredDataNode(
                        node_type=node_type, property_names=property_names
                    )
                )
        return tuple(nodes)

    @staticmethod
    def _node_type_of(value: Any) -> Optional[str]:
        if not isinstance(value, dict):
            return None
        raw_type = value.get("@type")
        candidates = raw_type if isinstance(raw_type, list) else (raw_type,)
        for item in candidates:
            if isinstance(item, str) and item.strip():
                return item.rsplit("/", 1)[-1].rsplit("#", 1)[-1].strip()
        return None

    @classmethod
    def _language(
        cls, collector: "_ArticleHtmlCollector", raw_article: RawHtmlArticle
    ) -> Optional[str]:
        """Resolve the document language from publisher-declared sources only.

        The precedence is fixed: the ``lang`` attribute on ``<html>``, then the
        Open Graph ``og:locale`` property, then a JSON-LD Article
        ``inLanguage``, then the explicitly supplied fallback. Nothing is
        inferred from the text, the host name, or the URL.
        """
        if collector.html_language and collector.html_language.strip():
            return collector.html_language
        locale = collector.metadata.get("og:locale")
        if locale and locale.strip():
            # og:locale uses language_TERRITORY; BCP 47 uses a hyphen. The
            # separator is rewritten, the declared value is otherwise kept.
            return locale.strip().replace("_", "-")
        in_language = cls._json_ld_in_language(collector.json_ld_documents)
        if in_language:
            return in_language
        return raw_article.fallback_language

    @classmethod
    def _json_ld_text(cls, documents: List[str], key: str) -> Optional[str]:
        """Return the first Article string value for ``key`` in document order."""
        for value in cls._json_ld_article_values(documents, key):
            if isinstance(value, str) and value.strip():
                return _normalize_json_ld_text(value)
        return None

    @classmethod
    def _json_ld_author(cls, documents: List[str]) -> Optional[str]:
        """Return the first Article author name in document order.

        Schema.org allows a bare string, a Person/Organization object, or a
        list of either. Only the declared name is read; nothing is composed.
        """
        for value in cls._json_ld_article_values(documents, "author"):
            candidates = value if isinstance(value, list) else [value]
            for candidate in candidates:
                if isinstance(candidate, str) and candidate.strip():
                    return _normalize_text(candidate)
                if isinstance(candidate, dict):
                    name = candidate.get("name")
                    if isinstance(name, str) and name.strip():
                        return _normalize_text(name)
        return None

    @classmethod
    def _json_ld_in_language(cls, documents: List[str]) -> Optional[str]:
        """Return the first Article ``inLanguage`` value in document order."""
        for value in cls._json_ld_article_values(documents, "inLanguage"):
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                name = value.get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
        return None

    @classmethod
    def _json_ld_article_values(cls, documents: List[str], key: str):
        """Yield ``key`` from each Article/NewsArticle object, in source order."""
        for document in documents:
            try:
                payload = json.loads(document)
            except json.JSONDecodeError:
                continue
            for value in cls._json_values_in_document_order(payload):
                if cls._is_article(value) and key in value:
                    yield value[key]

    @staticmethod
    def _canonical_source(canonical_href: Optional[str], source_url: str) -> str:
        """Resolve the declared canonical link against the fetched source URL."""
        if not canonical_href:
            return source_url
        return urljoin(source_url, canonical_href)

    @staticmethod
    def _innermost_heading(headings: List[Tuple[int, int, str]]) -> str:
        """Return the first heading from the most article-specific container.

        Headings are ranked exactly like paragraphs: article-contained first,
        then main-contained, then any other. This keeps a site or section
        heading from displacing the heading of the article being ingested.
        """
        if not headings:
            return ""
        top_level = [item for item in headings if item[1] == 1]
        if not top_level:
            return ""
        highest_priority = max(priority for priority, _, _ in top_level)
        return next(
            text for priority, _, text in top_level if priority == highest_priority
        )

    @staticmethod
    def _first_metadata(metadata: Dict[str, str], keys: Tuple[str, ...]) -> Optional[str]:
        for key in keys:
            value = metadata.get(key)
            if value:
                return value
        return None

    @staticmethod
    def _body_from(paragraphs: List[Tuple[int, str]]) -> str:
        if not paragraphs:
            return ""
        highest_priority = max(priority for priority, _ in paragraphs)
        return "\n\n".join(
            text for priority, text in paragraphs if priority == highest_priority
        )

    @classmethod
    def _body_from_application_json(
        cls, documents: List[str], source_url: str
    ) -> str:
        """Read paragraph HTML from a matching server-supplied JSON payload.

        Some applications deliver article content in an ``application/json``
        hydration payload and let the browser render it later. The extraction
        remains deterministic: JSON documents and objects are considered in
        source order, and a candidate must identify the current source path,
        declare ``type: article``, and contain a list of body blocks.
        """

        source_path = urlparse(source_url).path
        for document in documents:
            try:
                payload = json.loads(document)
            except json.JSONDecodeError:
                continue
            for value in cls._json_values_in_document_order(payload):
                if not cls._is_matching_article_payload(value, source_path):
                    continue
                paragraphs = cls._paragraphs_from_body_blocks(value["body"])
                if paragraphs:
                    return "\n\n".join(paragraphs)
        return ""

    @classmethod
    def _paragraphs_from_body_blocks(cls, blocks: List[Any]) -> Tuple[str, ...]:
        paragraphs: List[str] = []
        for block in blocks:
            if not isinstance(block, dict) or not isinstance(block.get("value"), str):
                continue
            collector = _ArticleHtmlCollector()
            collector.feed(block["value"])
            collector.close()
            paragraphs.extend(text for _, text in collector.paragraphs)
        return tuple(paragraphs)

    @staticmethod
    def _is_matching_article_payload(value: Any, source_path: str) -> bool:
        return (
            isinstance(value, dict)
            and isinstance(value.get("type"), str)
            and value["type"].lower() == "article"
            and value.get("path") == source_path
            and isinstance(value.get("body"), list)
        )

    def _published_at(
        self, collector: _ArticleHtmlCollector, raw_article: RawHtmlArticle
    ) -> Optional[datetime]:
        json_ld_published_value = self._json_ld_date_published(
            collector.json_ld_documents
        )
        if json_ld_published_value is not None:
            return _parse_source_timestamp(
                json_ld_published_value,
                "JSON-LD Article datePublished",
                normalize_naive_to_utc=True,
            )
        published_value = self._first_metadata(
            collector.metadata, ("article:published_time",)
        )
        if published_value:
            return _parse_source_timestamp(published_value, "article:published_time")
        published_value = self._first_metadata(collector.metadata, ("datepublished",))
        if published_value:
            return _parse_source_timestamp(published_value, "datePublished")
        if collector.time_values:
            return _parse_source_timestamp(collector.time_values[0], "published_at")
        if raw_article.fallback_published_at is not None:
            return raw_article.fallback_published_at
        return None

    @classmethod
    def _json_ld_date_published(cls, documents: List[str]) -> Optional[str]:
        """Return the first Article JSON-LD publication value in source order.

        Malformed JSON-LD is not an Article candidate and is ignored. Once a
        valid Article/NewsArticle object exposes ``datePublished``, its value
        is authoritative and timestamp validation must either succeed or fail
        explicitly; this method never falls back to a lower-priority source.
        """

        for document in documents:
            try:
                payload = json.loads(document)
            except json.JSONDecodeError:
                continue
            for value in cls._json_values_in_document_order(payload):
                if not cls._is_article(value) or "datePublished" not in value:
                    continue
                date_published = value["datePublished"]
                if not isinstance(date_published, str) or not date_published.strip():
                    raise DomainValidationError(
                        "JSON-LD Article datePublished must be a non-empty string"
                    )
                return date_published.strip()
        return None

    @classmethod
    def _json_values_in_document_order(cls, value: Any):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from cls._json_values_in_document_order(child)
        elif isinstance(value, list):
            for child in value:
                yield from cls._json_values_in_document_order(child)

    @staticmethod
    def _is_article(value: Dict[str, Any]) -> bool:
        raw_type = value.get("@type")
        types = raw_type if isinstance(raw_type, list) else (raw_type,)
        return any(
            isinstance(item, str)
            and item.rsplit("/", 1)[-1].rsplit("#", 1)[-1].lower()
            in {"article", "newsarticle"}
            for item in types
        )

    def _updated_at(
        self, collector: _ArticleHtmlCollector, raw_article: RawHtmlArticle
    ) -> Optional[datetime]:
        """Mirror the documented published-at precedence for the modified date.

        A JSON-LD Article ``dateModified`` outranks the meta tags, matching the
        precedence already documented for ``datePublished``. As with the
        published date, a selected value must parse or fail explicitly; this
        never falls back to a lower-priority source.
        """
        json_ld_updated_value = self._json_ld_text(
            collector.json_ld_documents, "dateModified"
        )
        if json_ld_updated_value is not None:
            return _parse_source_timestamp(
                json_ld_updated_value, "JSON-LD Article dateModified"
            )
        updated_value = self._first_metadata(collector.metadata, self._UPDATED_META_KEYS)
        if updated_value:
            return _parse_source_timestamp(updated_value, "updated_at")
        return raw_article.fallback_updated_at


class RegisterRawHtmlArticle:
    """Ingest raw HTML through the existing immutable source registration flow."""

    def __init__(
        self,
        content_repository: ContentRepository,
        normalizer: Optional[HtmlArticleNormalizer] = None,
    ) -> None:
        self._normalizer = normalizer or HtmlArticleNormalizer()
        self._register_snapshot = RegisterSourceSnapshot(content_repository)

    def execute(self, raw_article: RawHtmlArticle) -> RegistrationResult:
        normalized = self._normalizer.normalize(raw_article)
        return self._register_snapshot.execute(
            SourceArticleSnapshot(
                publisher=raw_article.publisher,
                canonical_source=normalized.canonical_source,
                original_language=normalized.language,
                article_type=raw_article.article_type,
                title=normalized.title,
                body=normalized.body,
                observed_at=raw_article.observed_at,
                source_published_at=normalized.published_at,
                source_updated_at=normalized.updated_at,
                author=normalized.author,
                description=normalized.description,
                keywords=normalized.keywords,
                structured_data_nodes=normalized.structured_data_nodes,
                declared_titles=normalized.declared_titles,
                declared_descriptions=normalized.declared_descriptions,
                declared_headings=normalized.declared_headings,
                internal_links=normalized.internal_links,
                table_word_count=normalized.table_word_count,
                list_word_count=normalized.list_word_count,
                blockquote_word_count=normalized.blockquote_word_count,
                answered_question_heading_count=normalized.answered_question_heading_count,
                unanswered_question_heading_count=normalized.unanswered_question_heading_count,
            )
        )
