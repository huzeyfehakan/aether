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
from aether.application.analysis.analyze_content_duplication import AnalyzeContentDuplication
from aether.application.analysis.analyze_passage_quality import AnalyzePassageQuality
from aether.application.analysis.analyze_internal_links import AnalyzeInternalLinks
from aether.application.analysis.analyze_heading_structure import AnalyzeHeadingStructure
from aether.application.analysis.analyze_structured_data import AnalyzeStructuredData
from aether.application.analysis.analyze_declared_consistency import AnalyzeDeclaredConsistency
from aether.application.analysis.assess_ai_readiness import AssessAIReadiness
from aether.application.analysis.build_ai_readiness_report import BuildAIReadinessReport
from aether.application.analysis.build_article_analysis_report import BuildArticleAnalysisReport
from aether.application.analysis.build_draft_review import BuildDraftReview
from aether.application.analysis.derive_editor_recommendations import (
    DeriveEditorRecommendations,
    RecommendationCode,
)
from aether.application.ingestion.prepare_draft import (
    DraftContentRequired,
    DraftHeadlineRequired,
    prepare_draft,
)
from aether.application.ingestion.assess_page_content import (
    AssessPageContent,
    PageAssessment,
)
from aether.application.analysis.analyze_topic_introduction import (
    AnalyzeTopicIntroduction,
)
from aether.application.analysis.analyze_fluency import AnalyzeFluency
from aether.application.analysis.analyze_claim_evidence import AnalyzeClaimEvidence
from aether.application.ingestion.register_raw_html_article import (
    RawHtmlArticle,
    RegisterRawHtmlArticle,
    canonical_url_from_html,
)
from aether.domain.common import DomainValidationError
from aether.presentation.draft_check_text import (
    performed_check_text,
    unavailable_check_text,
)
from aether.presentation.page_outcome_text import outcome_view
from aether.presentation.ai_readiness_report_renderers import (
    PlainTextAIReadinessReportRenderer,
)
from aether.application.analysis.derive_editor_recommendations import (
    RecommendationCategory,
)
from aether.presentation.draft_check_text import (
    performed_check_text,
    unavailable_check_text,
)
from aether.presentation.editor_recommendation_text import (
    category_subtitle,
    compared_articles_phrase,
    heading_count_phrase,
    impact_label,
    missing_properties_phrase,
    recommendation_text,
    repeated_in_phrase,
    shared_words_phrase,
    title_source_label,
)
from aether.presentation.score_dimension_text import seo_dimension_text, geo_dimension_text


class HtmlFetcher(Protocol):
    """The small outbound capability required by URL submission."""

    def fetch(self, url: str) -> str:
        ...


class AIReadinessPipeline:
    """Presentation-layer composition of existing application use cases only."""

    def __init__(self) -> None:
        repository = InMemoryContentRepository()
        self.repository = repository
        self._register_article = RegisterRawHtmlArticle(repository)
        passage_quality_analysis = AnalyzePassageQuality(repository)

        self._build_analysis_report = BuildArticleAnalysisReport(
            AnalyzeArticleStructure(repository),
            AnalyzeArticleMetadata(repository),
            passage_quality_analysis,
            AnalyzeContentDuplication(repository),
            AnalyzeStructuredData(repository),
            AnalyzeDeclaredConsistency(repository),
            AnalyzeHeadingStructure(repository),
            internal_link_analysis=AnalyzeInternalLinks(repository),
            topic_introduction_analysis=AnalyzeTopicIntroduction(repository),
            fluency_analysis=AnalyzeFluency(repository),
            claim_evidence_analysis=AnalyzeClaimEvidence(
                repository,
                passage_quality_analysis,
            ),
        )
        # A draft composes only the analyses its own text can answer.
        draft_passage_quality_analysis = AnalyzePassageQuality(repository)
        self._build_draft_report = BuildArticleAnalysisReport(
            AnalyzeArticleStructure(repository),
            AnalyzeArticleMetadata(repository),
            draft_passage_quality_analysis,
            AnalyzeContentDuplication(repository),
            heading_structure_analysis=AnalyzeHeadingStructure(repository),
            is_draft=True,
            fluency_analysis=AnalyzeFluency(repository),
        )
        self._build_draft_review = BuildDraftReview()
        self._assess_page = AssessPageContent()
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
        # Decide first whether this page can be analysed at all, so a page
        # that was never an article gets an explanation rather than an error.
        assessment = self._assess_page.execute(html)
        if not assessment.is_analyzable:
            return assessment
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

    def analyze_draft(
        self,
        content: str,
        headline: str,
        language: str,
        publisher: str,
    ) -> Any:
        """Analyse an unpublished draft, running only the checks it supports.

        An empty ``publisher`` is an editor who chose not to compare, not a
        publisher named nothing. The draft is still stored, under a name of its
        own, and the review says the comparison was not run.
        """
        comparison_requested = bool(publisher.strip())
        publisher = publisher.strip() or _DRAFTS_WITHOUT_A_PUBLISHER
        prepared = prepare_draft(content, headline, language, publisher)
        registration = self._register_article.execute(
            RawHtmlArticle(
                html=prepared.html,
                source_url=prepared.source_url,
                publisher=publisher,
                article_type="draft",
                observed_at=datetime.now(timezone.utc),
                fallback_language=language,
            )
        )
        analysis_report = self._build_draft_report.execute(
            registration.article, registration.article_version.article_version_id
        )
        comparison_available = bool(
            comparison_requested
            and analysis_report.content_duplication_analysis is not None
            and analysis_report.content_duplication_analysis.compared_article_count > 0
        )
        preview_report = self._build_readiness_report.execute(
            self._assess_readiness.execute_draft(
                analysis_report, comparison_available=comparison_available
            )
        )
        return self._build_draft_review.execute(
            analysis_report,
            prepared.headline,
            prepared.heading_check_available,
            comparison_requested,
            preview_report.assessment_summary.seo_score,
            preview_report.assessment_summary.geo_score,
        )

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

#: Where a draft is kept when the editor chose not to compare it. The domain
#: requires a publisher, and this is not one: no draft filed here is ever
#: compared against anything, because drafts are excluded from every corpus.
_DRAFTS_WITHOUT_A_PUBLISHER = "Unpublished drafts"


_USER_ERROR_TEXT = {}


def _user_error_text(error: Exception) -> str:
    """Translate known validation messages at the web presentation boundary."""
    return _USER_ERROR_TEXT.get(str(error), str(error))


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


_IMPACT_MAP = {
    RecommendationCode.NO_ARTICLE_STRUCTURED_DATA: "Structured Data",
    RecommendationCode.INCOMPLETE_ARTICLE_STRUCTURED_DATA: "Structured Data",
    RecommendationCode.MISSING_LAST_MODIFIED_DATE: "Metadata",
    RecommendationCode.MISSING_PUBLICATION_DATE: "Metadata",
    RecommendationCode.MISSING_AUTHOR: "Metadata",
    RecommendationCode.MISSING_SUMMARY: "Metadata",
    RecommendationCode.TITLE_SOURCES_DISAGREE: "Semantic Quality",
    RecommendationCode.DESCRIPTION_SOURCES_DISAGREE: "Semantic Quality",
    RecommendationCode.NO_OUTBOUND_LINKS: "Entity Authority",
    RecommendationCode.NO_CITATIONS: "Entity Authority",
    RecommendationCode.NO_STATISTICS: "Semantic Completeness",
    RecommendationCode.ORPHAN_PAGE: "Discoverability",
    RecommendationCode.NO_INTERNAL_BODY_LINKS: "Discoverability",
    RecommendationCode.NO_TOP_LEVEL_HEADING: "Structural Richness",
    RecommendationCode.MULTIPLE_TOP_LEVEL_HEADINGS: "Structural Richness",
    RecommendationCode.WEAK_ARTICLE_OPENING: "Semantic Completeness",
    RecommendationCode.WEAK_TOPIC_INTRODUCTION: "Semantic Completeness",
    RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY: "Semantic Quality",
    RecommendationCode.BODY_MOSTLY_REPEATED_TEXT: "Semantic Quality",
    RecommendationCode.CONTENT_BLOAT: "Semantic Completeness",
    RecommendationCode.SKIPPED_HEADING_LEVEL: "Structural Richness",
    RecommendationCode.CONFLICTING_PUBLISHED_DATES: "Metadata",
    RecommendationCode.UNSUPPORTED_ENTITIES: "Entity Authority",
    RecommendationCode.LOW_TRUST_INDEX: "Entity Authority",
    RecommendationCode.MISSING_SAME_AS_SCHEMA: "Semantic Completeness",
}


def _recommendation_views(report: Any, category, language: str = "en") -> list:
    """Shape one category of recommendations for display.

    Findings of the same kind are grouped so their explanation is given once
    and the occurrences are listed under it.
    """
    grouped: Dict[Any, Dict[str, Any]] = {}
    for recommendation in report.editor_recommendations:
        if recommendation.category is not category:
            continue
        text = recommendation_text(recommendation, language)
        group = grouped.setdefault(
            recommendation.code,
            {
                "headline": text.headline,
                "why_it_matters": text.why_it_matters,
                "what_to_do": text.what_to_do,
                "impact": impact_label(_IMPACT_MAP.get(recommendation.code, "")),
                "translations": {
                    item_language: {
                        "headline": recommendation_text(
                            recommendation, item_language
                        ).headline,
                        "why_it_matters": recommendation_text(
                            recommendation, item_language
                        ).why_it_matters,
                        "what_to_do": recommendation_text(
                            recommendation, item_language
                        ).what_to_do,
                    }
                    for item_language in ("tr", "en")
                },
                "occurrences": [],
            },
        )
        occurrence: Dict[str, Any] = {}
        if recommendation.excerpt:
            occurrence["excerpt"] = recommendation.excerpt
        if recommendation.other_article_count:
            occurrence["detail"] = repeated_in_phrase(
                recommendation.other_article_count
            )
        if recommendation.heading_count:
            occurrence["detail"] = heading_count_phrase(recommendation.heading_count)
        if recommendation.total_word_count:
            occurrence["detail"] = shared_words_phrase(
                recommendation.repeated_word_count, recommendation.total_word_count
            )
        if recommendation.missing_properties:
            occurrence["detail"] = missing_properties_phrase(
                recommendation.missing_properties
            )
        if recommendation.declared_values:
            occurrence["declared"] = [
                {"label": title_source_label(source), "value": value}
                for source, value in recommendation.declared_values
            ]
        related_passages = _related_passage_views(
            report, recommendation.passage_ids
        )

        if related_passages:
            occurrence["related_passages"] = related_passages
        group["occurrences"].append(occurrence)
    return list(grouped.values())


def _related_passage_views(report: Any, passage_ids) -> list:
    """Resolve recommendation provenance from canonical production profiles."""

    profiles_by_id = {
        profile.passage_id: profile
        for profile in report.passage_quality_summary.passage_profiles
    }
    profiles = []
    seen = set()
    for passage_id in passage_ids:
        if passage_id in seen or passage_id not in profiles_by_id:
            continue
        seen.add(passage_id)
        profiles.append(profiles_by_id[passage_id])
    profiles.sort(key=lambda profile: profile.ordinal_position)
    return [
        {
            "id": profile.passage_id,
            "ordinal": profile.ordinal_position,
            "text": profile.text,
            "word_count": profile.word_count,
        }
        for profile in profiles
    ]


def _score_dimension_view(
    name: str, dimension: Any, detail: Any, label: str
) -> Dict[str, Any]:
    return {
        "key": name,
        "val": dimension.dimension_score,
        "label": label,
        "weight": dimension.weight_percentage,
        "detail": {
            "label": detail.label,
            "dimension_score": detail.dimension_score,
            "signals": [
                {
                    "label": signal.label,
                    "value": signal.value,
                    "explanation": signal.explanation,
                    "kind": signal.kind.value if signal.kind is not None else None,
                    "is_context": signal.is_context,
                }
                for signal in detail.signals
            ],
        },
    }


def _limiting_factor_views(score: Any, dimension_text) -> list:
    return [
        {
            "key": factor.dimension_key,
            "label": dimension_text(factor.dimension_key)["label"],
            "score": factor.dimension_score,
            "configured_weight": factor.configured_weight_percentage,
            "effective_weight": factor.effective_weight_percentage,
            "maximum_contribution": factor.maximum_contribution,
            "actual_contribution": factor.actual_contribution,
            "lost_contribution": factor.lost_contribution,
        }
        for factor in score.limiting_factors
    ]


def _report_view(report: Any) -> Dict[str, Any]:
    """Expose existing report facts for the web UI without re-assessing them."""

    metadata = report.metadata_summary
    structure = report.structural_summary
    assessment = report.assessment_summary
    return {
        "assessment": {
            "metadata": assessment.metadata_completeness.value,
            "seo_score": {
                "total": report.assessment_summary.seo_score.total,
                "limiting_factors": _limiting_factor_views(
                    report.assessment_summary.seo_score, seo_dimension_text
                ),
                "entity_coverage": _score_dimension_view(
                    "entity_coverage", report.assessment_summary.seo_score.entity_coverage,
                    report.assessment_summary.seo_score.entity_coverage_detail,
                    seo_dimension_text("entity_coverage")["label"],
                ),
                "structured_data": _score_dimension_view(
                    "structured_data", report.assessment_summary.seo_score.structured_data,
                    report.assessment_summary.seo_score.structured_data_detail,
                    seo_dimension_text("structured_data")["label"],
                ),
                "semantic_quality": _score_dimension_view(
                    "semantic_quality", report.assessment_summary.seo_score.semantic_quality,
                    report.assessment_summary.seo_score.semantic_quality_detail,
                    seo_dimension_text("semantic_quality")["label"],
                ),
                "technical_access": _score_dimension_view(
                    "technical_access", report.assessment_summary.seo_score.technical_access,
                    report.assessment_summary.seo_score.technical_access_detail,
                    seo_dimension_text("technical_access")["label"],
                ),
            } if hasattr(report, 'assessment_summary') and hasattr(report.assessment_summary, 'seo_score') else None,
            "geo_score": {
                "total": report.assessment_summary.geo_score.total,
                "limiting_factors": _limiting_factor_views(
                    report.assessment_summary.geo_score, geo_dimension_text
                ),
                "semantic_completeness": _score_dimension_view(
                    "semantic_completeness",
                    report.assessment_summary.geo_score.semantic_completeness,
                    report.assessment_summary.geo_score.semantic_completeness_detail,
                    geo_dimension_text("semantic_completeness")["label"],
                ),
                "entity_authority": _score_dimension_view(
                    "entity_authority",
                    report.assessment_summary.geo_score.entity_authority,
                    report.assessment_summary.geo_score.entity_authority_detail,
                    geo_dimension_text("entity_authority")["label"],
                ),
                "structural_richness": _score_dimension_view(
                    "structural_richness",
                    report.assessment_summary.geo_score.structural_richness,
                    report.assessment_summary.geo_score.structural_richness_detail,
                    geo_dimension_text("structural_richness")["label"],
                ),
                "discoverability": _score_dimension_view(
                    "discoverability",
                    report.assessment_summary.geo_score.discoverability,
                    report.assessment_summary.geo_score.discoverability_detail,
                    geo_dimension_text("discoverability")["label"],
                ),
            } if hasattr(report, 'assessment_summary') and hasattr(report.assessment_summary, 'geo_score') else None,
        },
        "metadata": (
            {"label": "Publication date", "available": metadata.publication_date_available},
            {"label": "Last modified date", "available": metadata.last_modified_date_available},
            {"label": "Author", "available": metadata.author_available},
            {"label": "Description", "available": metadata.description_available},
        ),
        "structure": {
            "passage_count": structure.total_passage_count,
            "word_count": structure.total_word_count,
        },
        "passage_details": {
            "passage_count": structure.total_passage_count,
            "word_count": structure.total_word_count,
            "passages": [
                {
                    "position": profile.ordinal_position + 1,
                    "word_count": profile.word_count,
                    "text": profile.text,
                }
                for profile in report.passage_quality_summary.passage_profiles
            ],
        },
        "passage_extractability": {
            "passage_count": report.passage_quality_summary.passage_count,
            "bands": (
                {
                    "bound": 128,
                    "rate": report.passage_quality_summary.oversized_passage_rate_128,
                },
                {
                    "bound": 256,
                    "rate": report.passage_quality_summary.oversized_passage_rate_256,
                },
                {
                    "bound": 512,
                    "rate": report.passage_quality_summary.oversized_passage_rate_512,
                },
            ),
            "included_in_score": False,
        },
        "passage_balance": {
            "ratio": report.passage_balance_diagnostic.ratio,
            "included_in_score": report.passage_balance_diagnostic.included_in_score,
        },
        "direct_answer_coverage": {
            "ratio": report.direct_answer_coverage_diagnostic.ratio,
            "included_in_score": (
                report.direct_answer_coverage_diagnostic.included_in_score
            ),
        },
        "editor": (
            None
            if report.content_reuse_summary is None
            else {
                "subtitle": category_subtitle(RecommendationCategory.EDITOR),
                "compared_articles": compared_articles_phrase(
                    report.content_reuse_summary.compared_article_count
                ),
                "recommendations": _recommendation_views(
                    report, RecommendationCategory.EDITOR
                ),
            }
        ),
        "technical": (
            None
            if report.structured_data_summary is None
            else {
                "subtitle": category_subtitle(RecommendationCategory.TECHNICAL),
                "recommendations": _recommendation_views(
                    report, RecommendationCategory.TECHNICAL
                ),
            }
        ),
        # Named "identity", not "technical". It previously shared a key with
        # the technical recommendations above and, being second, silently
        # replaced them: the section rendered from a block that had no
        # recommendations in it at all.
        "identity": {
            "article_id": report.article_identity.article_id,
            "article_version_id": report.article_identity.article_version_id,
        },
    }


def _draft_view(review: Any) -> Dict[str, Any]:
    """Shape a draft review for display.

    Nothing here mentions metadata, structured data or article identity: a
    draft has none, and the review type does not carry them.
    """
    return {
        "headline": review.headline,
        "paragraph_count": review.paragraph_count,
        "word_count": review.word_count,
        "compared_article_count": review.compared_article_count,
        "checks_performed": [
            performed_check_text(check) for check in review.checks_performed
        ],
        "checks_unavailable": [
            unavailable_check_text(check) for check in review.checks_unavailable
        ],
        "localized_checks": {
            language: {
                "performed": [
                    performed_check_text(check, language)
                    for check in review.checks_performed
                ],
                "unavailable": [
                    unavailable_check_text(check, language)
                    for check in review.checks_unavailable
                ],
            }
            for language in ("tr", "en")
        },
        "seo_preview": _seo_score_view(review.seo_preview),
        "geo_preview": _geo_score_view(review.geo_preview),
        "recommendations": [
            _localized_draft_recommendation_view(r) for r in review.recommendations
        ],
    }


def _localized_draft_recommendation_view(recommendation: Any) -> Dict[str, Any]:
    english = recommendation_text(recommendation, "en")
    return {
        "headline": english.headline,
        "why_it_matters": english.why_it_matters,
        "what_to_do": english.what_to_do,
        "translations": {
            language: {
                "headline": recommendation_text(recommendation, language).headline,
                "why_it_matters": recommendation_text(
                    recommendation, language
                ).why_it_matters,
                "what_to_do": recommendation_text(
                    recommendation, language
                ).what_to_do,
            }
            for language in ("tr", "en")
        },
        "occurrences": [_occurrence_view(recommendation)],
    }


def _seo_score_view(score: Any) -> Optional[Dict[str, Any]]:
    if score is None:
        return None
    return {
        "total": score.total,
        "limiting_factors": _limiting_factor_views(score, seo_dimension_text),
        **{
            key: _score_dimension_view(
                key, getattr(score, key), getattr(score, f"{key}_detail"),
                seo_dimension_text(key)["label"],
            )
            for key in (
                "entity_coverage", "structured_data", "semantic_quality",
                "technical_access",
            )
        },
    }


def _geo_score_view(score: Any) -> Optional[Dict[str, Any]]:
    if score is None:
        return None
    return {
        "total": score.total,
        "limiting_factors": _limiting_factor_views(score, geo_dimension_text),
        **{
            key: _score_dimension_view(
                key, getattr(score, key), getattr(score, f"{key}_detail"),
                geo_dimension_text(key)["label"],
            )
            for key in (
                "semantic_completeness", "entity_authority",
                "structural_richness", "discoverability",
            )
        },
    }


def _occurrence_view(recommendation: Any) -> Dict[str, Any]:
    occurrence: Dict[str, Any] = {}
    if recommendation.excerpt:
        occurrence["excerpt"] = recommendation.excerpt
    if recommendation.other_article_count:
        occurrence["detail"] = repeated_in_phrase(recommendation.other_article_count)
    if recommendation.heading_count:
        occurrence["detail"] = heading_count_phrase(recommendation.heading_count)
    if recommendation.total_word_count:
        occurrence["detail"] = shared_words_phrase(
            recommendation.repeated_word_count, recommendation.total_word_count
        )
    return occurrence


def _analysis_response(result: Any) -> Dict[str, Any]:
    """Shape either a finished report or an explained non-article outcome.

    A page that could not be analysed is a result, not a failure. It returns
    with the same status as any other analysis and carries an explanation in
    place of a report.
    """
    outcome = outcome_view(result) if isinstance(result, PageAssessment) else None
    if outcome is not None:
        outcome["translations"] = {
            language: outcome_view(result, language) for language in ("tr", "en")
        }
        return {"report": None, "view": None, "outcome": outcome}
    return {
        "report": PlainTextAIReadinessReportRenderer().render(result),
        "view": _report_view(result),
        "outcome": None,
    }


def create_app(fetcher: Optional[HtmlFetcher] = None) -> FastAPI:
    """Create the standalone demonstration web application."""

    app = FastAPI(title="Aether AI Readiness", version="0.1.0")
    app.state.fetcher = fetcher or HttpHtmlFetcher()
    app.state.pipeline = AIReadinessPipeline()

    @app.get("/", response_class=FileResponse)
    def index() -> FileResponse:
        # The page shell and the analysis endpoints must never drift apart.
        # Without an explicit directive a browser may heuristically cache this
        # document and keep running script that reads fields the server has
        # since stopped sending.
        return FileResponse(
            _TEMPLATE_PATH,
            media_type="text/html",
            headers={"Cache-Control": "no-store"},
        )

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
            return _analysis_response(report)
        except (HtmlFetchError, DomainValidationError) as error:
            raise HTTPException(status_code=422, detail=_user_error_text(error)) from error

    @app.get("/publishers")
    def publishers() -> Dict[str, Any]:
        """Publishers already analysed, so a draft can be compared with them."""
        repository = app.state.pipeline.repository
        names = sorted(
            {
                article.publisher
                for article in repository.all_articles()
                if article.article_type != "draft"
            }
        )
        return {"publishers": names}

    @app.post("/analyze/draft")
    def analyze_draft(
        content: str = Form(""),
        headline: str = Form(""),
        language: str = Form("tr"),
        publisher: str = Form(""),
    ) -> Dict[str, Any]:
        try:
            review = app.state.pipeline.analyze_draft(
                content, headline, language, publisher
            )
        except (DraftContentRequired, DraftHeadlineRequired) as error:
            raise HTTPException(status_code=422, detail=_user_error_text(error)) from error
        except DomainValidationError as error:
            raise HTTPException(status_code=422, detail=_user_error_text(error)) from error
        return {"draft": _draft_view(review)}

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
            return _analysis_response(report)
        except UnicodeDecodeError as error:
            raise HTTPException(
                status_code=422, detail=_USER_ERROR_TEXT["HTML file must be UTF-8 encoded"]
            ) from error
        except DomainValidationError as error:
            raise HTTPException(status_code=422, detail=_user_error_text(error)) from error

    return app


app = create_app()
