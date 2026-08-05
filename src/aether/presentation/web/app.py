"""Minimal web UI that composes the existing deterministic MVP use cases."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Protocol
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from aether.adapters.outbound.http_html_fetcher import HtmlFetchError, HttpHtmlFetcher
from aether.adapters.outbound.in_memory_content_repository import InMemoryContentRepository
from aether.application.analysis.analyze_article_metadata import AnalyzeArticleMetadata
from aether.application.analysis.analyze_article_structure import AnalyzeArticleStructure
from aether.application.analysis.analyze_passage_quality import AnalyzePassageQuality
from aether.application.analysis.assess_ai_readiness import AssessAIReadiness
from aether.application.analysis.build_ai_readiness_report import BuildAIReadinessReport
from aether.application.analysis.build_article_analysis_report import BuildArticleAnalysisReport
from aether.application.ingestion.register_raw_html_article import (
    RawHtmlArticle,
    RegisterRawHtmlArticle,
    canonical_url_from_html,
)
from aether.domain.common import DomainValidationError
from aether.presentation.ai_readiness_report_renderers import (
    PlainTextAIReadinessReportRenderer,
)


class HtmlFetcher(Protocol):
    """The small outbound capability required by URL submission."""

    def fetch(self, url: str) -> str:
        ...


class AIReadinessPipeline:
    """Presentation-layer composition of existing application use cases only."""

    def __init__(self) -> None:
        repository = InMemoryContentRepository()
        self._register_article = RegisterRawHtmlArticle(repository)
        self._build_analysis_report = BuildArticleAnalysisReport(
            AnalyzeArticleStructure(repository),
            AnalyzeArticleMetadata(repository),
            AnalyzePassageQuality(repository),
        )
        self._assess_readiness = AssessAIReadiness()
        self._build_readiness_report = BuildAIReadinessReport()
        self._renderer = PlainTextAIReadinessReportRenderer()

    def analyze_report(
        self,
        html: str,
        source_url: str,
        publisher: str,
        article_type: str,
        fallback_language: Optional[str] = None,
        fallback_published_at: Optional[str] = None,
    ) -> Any:
        parsed_fallback_published_at = self._parse_fallback_timestamp(
            fallback_published_at
        )
        registration = self._register_article.execute(
            RawHtmlArticle(
                html=html,
                source_url=source_url,
                publisher=publisher,
                article_type=article_type,
                observed_at=datetime.now(timezone.utc),
                fallback_language=fallback_language or None,
                fallback_published_at=parsed_fallback_published_at,
            )
        )
        analysis_report = self._build_analysis_report.execute(
            registration.article, registration.article_version.article_version_id
        )
        assessment = self._assess_readiness.execute(analysis_report)
        return self._build_readiness_report.execute(assessment)

    def analyze(
        self,
        html: str,
        source_url: str,
        publisher: str,
        article_type: str,
        fallback_language: Optional[str] = None,
        fallback_published_at: Optional[str] = None,
    ) -> str:
        """Retain the existing plain-text presentation result for callers."""

        return self._renderer.render(
            self.analyze_report(
                html,
                source_url,
                publisher,
                article_type,
                fallback_language,
                fallback_published_at,
            )
        )

    @staticmethod
    def _parse_fallback_timestamp(value: Optional[str]) -> Optional[datetime]:
        if not value or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as error:
            raise DomainValidationError(
                "Fallback publication date must be ISO-8601"
            ) from error
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise DomainValidationError(
                "Fallback publication date must include a timezone"
            )
        return parsed


_TEMPLATE_PATH = Path(__file__).parent / "templates" / "index.html"


def _canonical_url_from_html(html: str) -> Optional[str]:
    """Reuse the ingestion canonical contract to derive a usable source URL.

    An uploaded file has no base URL, so a relative canonical link cannot be
    resolved here. Such a file is treated as having no usable canonical URL and
    the caller asks for an explicit source URL instead.
    """

    canonical = canonical_url_from_html(html)
    if canonical is None:
        return None
    parsed = urlparse(canonical)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return canonical


def _publisher_from(source_url: str, publisher: Optional[str]) -> str:
    if publisher and publisher.strip():
        return publisher.strip()
    hostname = urlparse(source_url).hostname
    if not hostname:
        raise DomainValidationError("source URL must be an absolute HTTP(S) URL")
    return hostname.removeprefix("www.")


def _report_view(report: Any) -> Dict[str, Any]:
    """Expose existing report facts for the web UI without re-assessing them."""

    metadata = report.metadata_summary
    structure = report.structural_summary
    coverage = report.passage_quality_summary
    assessment = report.assessment_summary
    return {
        "assessment": {
            "metadata": assessment.metadata_completeness.value,
            "coverage": assessment.passage_coverage.value,
            "structure": assessment.structural_completeness.value,
        },
        "metadata": (
            {"label": "Title", "available": metadata.title_available},
            {"label": "Canonical URL", "available": metadata.canonical_url_available},
            {"label": "Publication date", "available": metadata.publication_date_available},
            {"label": "Last modified date", "available": metadata.last_modified_date_available},
            {"label": "Language", "available": metadata.language_available},
            {"label": "Author", "available": metadata.author_available},
            {"label": "Description", "available": metadata.description_available},
            {"label": "Keywords", "available": metadata.keyword_available},
        ),
        "structure": {
            "passage_count": structure.total_passage_count,
            "word_count": structure.total_word_count,
            "paragraph_count": structure.paragraph_count,
        },
        "coverage": {
            "source_paragraph_count": coverage.source_paragraph_count,
            "covered_source_paragraph_count": coverage.covered_source_paragraph_count,
            "ratio": coverage.source_paragraph_coverage_ratio,
            "ordinals_are_contiguous": coverage.passage_ordinals_are_contiguous,
        },
        "technical": {
            "article_id": report.article_identity.article_id,
            "article_version_id": report.article_identity.article_version_id,
            "average_passage_length": structure.average_passage_length,
            "heading_count": structure.heading_count,
            "minimum_passage_word_count": coverage.minimum_passage_word_count,
            "maximum_passage_word_count": coverage.maximum_passage_word_count,
            "median_passage_word_count": coverage.median_passage_word_count,
        },
    }


def create_app(fetcher: Optional[HtmlFetcher] = None) -> FastAPI:
    """Create the standalone demonstration web application."""

    app = FastAPI(title="Aether AI Readiness", version="0.1.0")
    app.state.fetcher = fetcher or HttpHtmlFetcher()
    app.state.pipeline = AIReadinessPipeline()

    @app.get("/", response_class=FileResponse)
    def index() -> FileResponse:
        return FileResponse(_TEMPLATE_PATH, media_type="text/html")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/analyze/url")
    def analyze_url(
        url: str = Form(...),
        publisher: Optional[str] = Form(None),
        article_type: str = Form("news_report"),
        fallback_language: Optional[str] = Form(None),
        fallback_published_at: Optional[str] = Form(None),
    ) -> Dict[str, Any]:
        try:
            html = app.state.fetcher.fetch(url)
            resolved_publisher = _publisher_from(url, publisher)
            report = app.state.pipeline.analyze_report(
                html,
                url,
                resolved_publisher,
                article_type,
                fallback_language,
                fallback_published_at,
            )
            return {
                "report": PlainTextAIReadinessReportRenderer().render(report),
                "view": _report_view(report),
            }
        except (HtmlFetchError, DomainValidationError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/analyze/file")
    async def analyze_file(
        file: UploadFile = File(...),
        source_url: Optional[str] = Form(None),
        publisher: Optional[str] = Form(None),
        article_type: str = Form("news_report"),
        fallback_language: Optional[str] = Form(None),
        fallback_published_at: Optional[str] = Form(None),
    ) -> Dict[str, Any]:
        try:
            html = (await file.read()).decode("utf-8")
            resolved_source_url = source_url or _canonical_url_from_html(html)
            if not resolved_source_url:
                raise DomainValidationError(
                    "HTML file needs a source URL because no canonical URL was found"
                )
            resolved_publisher = _publisher_from(resolved_source_url, publisher)
            report = app.state.pipeline.analyze_report(
                html,
                resolved_source_url,
                resolved_publisher,
                article_type,
                fallback_language,
                fallback_published_at,
            )
            return {
                "report": PlainTextAIReadinessReportRenderer().render(report),
                "view": _report_view(report),
            }
        except UnicodeDecodeError as error:
            raise HTTPException(
                status_code=422, detail="HTML file must be UTF-8 encoded"
            ) from error
        except DomainValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    return app


app = create_app()
