"""Deterministic plain-text, JSON, and Markdown renderers for AIReadinessReport."""

import json
from typing import Any, Dict

from aether.application.analysis.build_ai_readiness_report import AIReadinessReport
from aether.application.analysis.derive_editor_recommendations import (
    RecommendationCategory,
)
from aether.presentation.editor_recommendation_text import (
    category_subtitle,
    heading_count_phrase,
    shared_words_phrase,
    title_source_label,
    category_title,
    compared_articles_phrase,
    missing_properties_phrase,
    recommendation_text,
    repeated_in_phrase,
)


def _codes_in_order(recommendations) -> list:
    """Distinct recommendation codes, keeping first-seen order."""
    seen = []
    for recommendation in recommendations:
        if recommendation.code not in seen:
            seen.append(recommendation.code)
    return seen


def _score_mapping(score) -> dict:
    result = {"total": score.total}
    if hasattr(score, 'entity_coverage'):
        result["entity_coverage"] = {
            "weight_percentage": score.entity_coverage.weight_percentage,
            "dimension_score": score.entity_coverage.dimension_score,
            "weighted_contribution": score.entity_coverage.weighted_contribution,
        }
    if hasattr(score, 'structured_data'):
        result["structured_data"] = {
            "weight_percentage": score.structured_data.weight_percentage,
            "dimension_score": score.structured_data.dimension_score,
            "weighted_contribution": score.structured_data.weighted_contribution,
        }
    if hasattr(score, 'semantic_quality'):
        result["semantic_quality"] = {
            "weight_percentage": score.semantic_quality.weight_percentage,
            "dimension_score": score.semantic_quality.dimension_score,
            "weighted_contribution": score.semantic_quality.weighted_contribution,
        }
    if hasattr(score, 'technical_access'):
        result["technical_access"] = {
            "weight_percentage": score.technical_access.weight_percentage,
            "dimension_score": score.technical_access.dimension_score,
            "weighted_contribution": score.technical_access.weighted_contribution,
        }
    if hasattr(score, 'semantic_completeness'):
        result["semantic_completeness"] = {
            "weight_percentage": score.semantic_completeness.weight_percentage,
            "dimension_score": score.semantic_completeness.dimension_score,
            "weighted_contribution": score.semantic_completeness.weighted_contribution,
        }
    if hasattr(score, 'entity_authority'):
        result["entity_authority"] = {
            "weight_percentage": score.entity_authority.weight_percentage,
            "dimension_score": score.entity_authority.dimension_score,
            "weighted_contribution": score.entity_authority.weighted_contribution,
        }
    if hasattr(score, 'structural_richness'):
        result["structural_richness"] = {
            "weight_percentage": score.structural_richness.weight_percentage,
            "dimension_score": score.structural_richness.dimension_score,
            "weighted_contribution": score.structural_richness.weighted_contribution,
        }
    if hasattr(score, 'discoverability'):
        result["discoverability"] = {
            "weight_percentage": score.discoverability.weight_percentage,
            "dimension_score": score.discoverability.dimension_score,
            "weighted_contribution": score.discoverability.weighted_contribution,
        }
    return result

def _report_mapping(report: AIReadinessReport) -> Dict[str, Any]:
    """Map report fields directly without deriving any new business information."""
    seo_score = report.assessment_summary.seo_score
    geo_score = report.assessment_summary.geo_score
    return {
        "article_identity": {
            "article_id": report.article_identity.article_id,
            "article_version_id": report.article_identity.article_version_id,
        },
        "structural_summary": {
            "total_passage_count": report.structural_summary.total_passage_count,
            "total_word_count": report.structural_summary.total_word_count,
        },
        "metadata_summary": {
            "title_length": report.metadata_summary.title_length,
            "publication_date_available": report.metadata_summary.publication_date_available,
            "last_modified_date_available": report.metadata_summary.last_modified_date_available,
            "author_available": report.metadata_summary.author_available,
            "description_available": report.metadata_summary.description_available,
        },
        "passage_quality_summary": {
            "passage_profiles": [
                {
                    "passage_id": profile.passage_id,
                    "ordinal_position": profile.ordinal_position,
                    "word_count": profile.word_count,
                    "character_count": profile.character_count,
                }
                for profile in report.passage_quality_summary.passage_profiles
            ],
        },
        "content_reuse": (
            None
            if report.content_reuse_summary is None
            else {
                "compared_article_count": (
                    report.content_reuse_summary.compared_article_count
                ),
                "repeated_paragraph_count": len(
                    report.content_reuse_summary.repeated_passages
                ),
                "total_paragraph_count": (
                    report.content_reuse_summary.total_passage_count
                ),
            }
        ),
        "editor_recommendations": [
            {
                "category": recommendation.category.value,
                "code": recommendation.code.value,
                "excerpt": recommendation.excerpt,
                "other_article_count": recommendation.other_article_count,
                "declared_values": [
                    list(pair) for pair in recommendation.declared_values
                ],
            }
            for recommendation in report.editor_recommendations
        ],
        "assessment_summary": {
            "metadata_completeness": report.assessment_summary.metadata_completeness.value,
            "seo_score": _score_mapping(seo_score),
            "geo_score": _score_mapping(geo_score),
        },
    }


class JsonAIReadinessReportRenderer:
    """Serialize an existing report as deterministic JSON."""

    def render(self, report: AIReadinessReport) -> str:
        return json.dumps(_report_mapping(report), ensure_ascii=False, indent=2, sort_keys=True)


class PlainTextAIReadinessReportRenderer:
    """Render an existing report as readable plain text."""

    def render(self, report: AIReadinessReport) -> str:
        structural = report.structural_summary
        metadata = report.metadata_summary
        assessment = report.assessment_summary
        seo = assessment.seo_score
        geo = assessment.geo_score
        lines = (
            "AI Readiness Report",
            "",
            "Article Identity",
            f"Article ID: {report.article_identity.article_id}",
            f"Article Version ID: {report.article_identity.article_version_id}",
            "",
            "SEO Score",
            f" Total Score: {seo.total}",
            f" - Entity Coverage ({seo.entity_coverage.weight_percentage}%): {'N/A' if seo.entity_coverage.dimension_score is None else f'{seo.entity_coverage.dimension_score:.1f}'}",
            f" - Structured Data ({seo.structured_data.weight_percentage}%): {'N/A' if seo.structured_data.dimension_score is None else f'{seo.structured_data.dimension_score:.1f}'}",
            f" - Semantic Quality ({seo.semantic_quality.weight_percentage}%): {'N/A' if seo.semantic_quality.dimension_score is None else f'{seo.semantic_quality.dimension_score:.1f}'}",
            f" - Technical Access ({seo.technical_access.weight_percentage}%): {'N/A' if seo.technical_access.dimension_score is None else f'{seo.technical_access.dimension_score:.1f}'}",
            "",
            "GEO Score (Generative Engine Optimization)",
            f" Total Score: {geo.total}",
            f" - Semantic Completeness ({geo.semantic_completeness.weight_percentage}%): {'N/A' if geo.semantic_completeness.dimension_score is None else f'{geo.semantic_completeness.dimension_score:.1f}'}",
            f" - Entity Authority ({geo.entity_authority.weight_percentage}%): {'N/A' if geo.entity_authority.dimension_score is None else f'{geo.entity_authority.dimension_score:.1f}'}",
            f" - Structural Richness ({geo.structural_richness.weight_percentage}%): {'N/A' if geo.structural_richness.dimension_score is None else f'{geo.structural_richness.dimension_score:.1f}'}",
            f" - Discoverability ({geo.discoverability.weight_percentage}%): {'N/A' if geo.discoverability.dimension_score is None else f'{geo.discoverability.dimension_score:.1f}'}",
            "",
            "Structural Summary",
            f"Total Passages: {structural.total_passage_count}",
            f"Total Words: {structural.total_word_count}",
            "",
            "Extracted Metadata",
            "What Aether could read from this page, from any source on it.",
            f"Title Length: {metadata.title_length}",
            f"Publication Date Available: {metadata.publication_date_available}",
            f"Last Modified Date Available: {metadata.last_modified_date_available}",
            f"Author Available: {metadata.author_available}",
            f"Description Available: {metadata.description_available}",
            f"Metadata Completeness: {assessment.metadata_completeness.value}",
        ) + self._structured_data_lines(report)
        return "\n".join(list(lines) + list(self._recommendation_lines(report)))

    @staticmethod
    def _structured_data_lines(report: AIReadinessReport) -> tuple:
        summary = report.structured_data_summary
        if summary is None:
            return ()
        lines = [
            "",
            "Structured Data (Schema.org)",
            "What this page formally declares to machines.",
        ]
        if not summary.article_node_present:
            lines.append("Article markup: not present")
            return tuple(lines)
        lines.append("Article markup: present")
        lines.append(
            f"Declared: {len(summary.declared_article_properties)} properties"
        )
        if summary.missing_article_properties:
            lines.append(
                f"  {missing_properties_phrase(summary.missing_article_properties)}"
            )
        return tuple(lines)

    @staticmethod
    def _recommendation_lines(report: AIReadinessReport) -> tuple:
        lines = []
        for category in (
            RecommendationCategory.EDITOR,
            RecommendationCategory.TECHNICAL,
        ):
            in_category = [
                recommendation
                for recommendation in report.editor_recommendations
                if recommendation.category is category
            ]
            if category is RecommendationCategory.EDITOR:
                if report.content_reuse_summary is None:
                    continue
                lines.extend(
                    (
                        "",
                        category_title(category),
                        category_subtitle(category),
                        compared_articles_phrase(
                            report.content_reuse_summary.compared_article_count
                        ),
                    )
                )
                if not in_category:
                    if report.content_reuse_summary.compared_article_count:
                        lines.append("Nothing to change in this article.")
                    continue
            else:
                if report.structured_data_summary is None:
                    continue
                lines.extend(
                    ("", category_title(category), category_subtitle(category))
                )
                if not in_category:
                    lines.append(
                        "Nothing to change: this article declares itself completely."
                    )
                    continue
            for code in _codes_in_order(in_category):
                occurrences = [r for r in in_category if r.code is code]
                text = recommendation_text(occurrences[0])
                lines.extend(("", text.headline))
                for occurrence in occurrences:
                    detail = ""
                    if occurrence.other_article_count:
                        detail = repeated_in_phrase(occurrence.other_article_count)
                    if occurrence.heading_count:
                        lines.append(f"  {heading_count_phrase(occurrence.heading_count)}")
                    if occurrence.total_word_count:
                        lines.append(
                            "  "
                            + shared_words_phrase(
                                occurrence.repeated_word_count,
                                occurrence.total_word_count,
                            )
                        )
                    if occurrence.missing_properties:
                        detail = missing_properties_phrase(
                            occurrence.missing_properties
                        )
                    if detail:
                        lines.append(f"  {detail}")
                    for source, value in occurrence.declared_values:
                        lines.append(f"  {title_source_label(source)}: {value}")
                    if occurrence.excerpt:
                        lines.append(f'  "{occurrence.excerpt}"')
                lines.extend(
                    (
                        f"  Why it matters: {text.why_it_matters}",
                        f"  What to do: {text.what_to_do}",
                    )
                )
        return tuple(lines)


class MarkdownAIReadinessReportRenderer:
    """Render an existing report as deterministic Markdown."""

    def render(self, report: AIReadinessReport) -> str:
        structural = report.structural_summary
        metadata = report.metadata_summary
        passage_quality = report.passage_quality_summary
        assessment = report.assessment_summary
        seo = assessment.seo_score
        geo = assessment.geo_score
        lines = [
            "# AI Readiness Report",
            "",
            "## Article Identity",
            "",
            f"- Article ID: `{report.article_identity.article_id}`",
            f"- Article Version ID: `{report.article_identity.article_version_id}`",
            "",
            "## SEO Score",
            f"**Total Score: {seo.total} / 100**",
            "",
            f"- **Entity Coverage ({seo.entity_coverage.weight_percentage}%)**: {'N/A' if seo.entity_coverage.dimension_score is None else f'{seo.entity_coverage.dimension_score:.1f}'}",
            f"- **Structured Data ({seo.structured_data.weight_percentage}%)**: {'N/A' if seo.structured_data.dimension_score is None else f'{seo.structured_data.dimension_score:.1f}'}",
            f"- **Semantic Quality ({seo.semantic_quality.weight_percentage}%)**: {'N/A' if seo.semantic_quality.dimension_score is None else f'{seo.semantic_quality.dimension_score:.1f}'}",
            f"- **Technical Access ({seo.technical_access.weight_percentage}%)**: {'N/A' if seo.technical_access.dimension_score is None else f'{seo.technical_access.dimension_score:.1f}'}",
            "",
            "## GEO Score (Generative Engine Optimization)",
            f"**Total Score: {geo.total} / 100**",
            "",
            f"- **Semantic Completeness ({geo.semantic_completeness.weight_percentage}%)**: {'N/A' if geo.semantic_completeness.dimension_score is None else f'{geo.semantic_completeness.dimension_score:.1f}'}",
            f"- **Entity Authority ({geo.entity_authority.weight_percentage}%)**: {'N/A' if geo.entity_authority.dimension_score is None else f'{geo.entity_authority.dimension_score:.1f}'}",
            f"- **Structural Richness ({geo.structural_richness.weight_percentage}%)**: {'N/A' if geo.structural_richness.dimension_score is None else f'{geo.structural_richness.dimension_score:.1f}'}",
            f"- **Discoverability ({geo.discoverability.weight_percentage}%)**: {'N/A' if geo.discoverability.dimension_score is None else f'{geo.discoverability.dimension_score:.1f}'}",
            "",
            "## Structural Summary",
            "",
            f"- Total passages: {structural.total_passage_count}",
            f"- Total words: {structural.total_word_count}",
            "",
            "## Extracted Metadata",
            "",
            f"- Title length: {metadata.title_length}",
            f"- Publication date available: {metadata.publication_date_available}",
            f"- Last modified date available: {metadata.last_modified_date_available}",
            f"- Author available: {metadata.author_available}",
            f"- Description available: {metadata.description_available}",
            "",
            "",
            "### Passage Profiles",
            "",
            "| Passage ID | Ordinal | Words | Characters |",
            "| --- | ---: | ---: | ---: |",
        ]
        lines.extend(
            f"| `{profile.passage_id}` | {profile.ordinal_position} | {profile.word_count} | {profile.character_count} |"
            for profile in passage_quality.passage_profiles
        )
        lines.extend(
            (
                "",
                "## Assessment Summary",
                "",
                f"- Metadata completeness: {assessment.metadata_completeness.value}",
            )
        )
        return "\n".join(lines)