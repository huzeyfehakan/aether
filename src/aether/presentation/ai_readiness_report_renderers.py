"""Deterministic plain-text, JSON, and Markdown renderers for AIReadinessReport."""

import json
from typing import Any, Dict

from aether.application.analysis.build_ai_readiness_report import AIReadinessReport


def _display_optional(value: Any) -> str:
    return "unavailable" if value is None else str(value)


def _report_mapping(report: AIReadinessReport) -> Dict[str, Any]:
    """Map report fields directly without deriving any new business information."""
    return {
        "article_identity": {
            "article_id": report.article_identity.article_id,
            "article_version_id": report.article_identity.article_version_id,
        },
        "structural_summary": {
            "total_passage_count": report.structural_summary.total_passage_count,
            "total_word_count": report.structural_summary.total_word_count,
            "average_passage_length": report.structural_summary.average_passage_length,
            "heading_count": report.structural_summary.heading_count,
            "paragraph_count": report.structural_summary.paragraph_count,
        },
        "metadata_summary": {
            "title_available": report.metadata_summary.title_available,
            "title_length": report.metadata_summary.title_length,
            "canonical_url_available": report.metadata_summary.canonical_url_available,
            "publication_date_available": report.metadata_summary.publication_date_available,
            "last_modified_date_available": report.metadata_summary.last_modified_date_available,
            "language_available": report.metadata_summary.language_available,
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
            "minimum_passage_word_count": (
                report.passage_quality_summary.minimum_passage_word_count
            ),
            "maximum_passage_word_count": (
                report.passage_quality_summary.maximum_passage_word_count
            ),
            "median_passage_word_count": (
                report.passage_quality_summary.median_passage_word_count
            ),
        },
        "assessment_summary": {
            "metadata_completeness": (
                report.assessment_summary.metadata_completeness.value
            ),
            "structural_completeness": (
                report.assessment_summary.structural_completeness.value
            ),
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
        passage_quality = report.passage_quality_summary
        assessment = report.assessment_summary
        lines = (
            "AI Readiness Report",
            "",
            "Article Identity",
            f"Article ID: {report.article_identity.article_id}",
            f"Article Version ID: {report.article_identity.article_version_id}",
            "",
            "Structural Summary",
            f"Total Passages: {structural.total_passage_count}",
            f"Total Words: {structural.total_word_count}",
            f"Average Passage Length: {structural.average_passage_length}",
            f"Heading Count: {_display_optional(structural.heading_count)}",
            f"Paragraph Count: {structural.paragraph_count}",
            "",
            "Metadata Summary",
            f"Title Available: {metadata.title_available}",
            f"Title Length: {metadata.title_length}",
            f"Canonical URL Available: {metadata.canonical_url_available}",
            f"Publication Date Available: {metadata.publication_date_available}",
            f"Last Modified Date Available: {metadata.last_modified_date_available}",
            f"Language Available: {metadata.language_available}",
            f"Author Available: {metadata.author_available}",
            f"Description Available: {metadata.description_available}",
            "",
            "Passage Quality Summary",
            f"Minimum Passage Word Count: {_display_optional(passage_quality.minimum_passage_word_count)}",
            f"Maximum Passage Word Count: {_display_optional(passage_quality.maximum_passage_word_count)}",
            f"Median Passage Word Count: {_display_optional(passage_quality.median_passage_word_count)}",
            "",
            "Assessment Summary",
            f"Metadata Completeness: {assessment.metadata_completeness.value}",
            f"Structural Completeness: {assessment.structural_completeness.value}",
        )
        return "\n".join(lines)


class MarkdownAIReadinessReportRenderer:
    """Render an existing report as deterministic Markdown."""

    def render(self, report: AIReadinessReport) -> str:
        structural = report.structural_summary
        metadata = report.metadata_summary
        passage_quality = report.passage_quality_summary
        assessment = report.assessment_summary
        lines = [
            "# AI Readiness Report",
            "",
            "## Article Identity",
            "",
            f"- Article ID: `{report.article_identity.article_id}`",
            f"- Article Version ID: `{report.article_identity.article_version_id}`",
            "",
            "## Structural Summary",
            "",
            f"- Total passages: {structural.total_passage_count}",
            f"- Total words: {structural.total_word_count}",
            f"- Average passage length: {structural.average_passage_length}",
            f"- Heading count: {_display_optional(structural.heading_count)}",
            f"- Paragraph count: {structural.paragraph_count}",
            "",
            "## Metadata Summary",
            "",
            f"- Title available: {metadata.title_available}",
            f"- Title length: {metadata.title_length}",
            f"- Canonical URL available: {metadata.canonical_url_available}",
            f"- Publication date available: {metadata.publication_date_available}",
            f"- Last modified date available: {metadata.last_modified_date_available}",
            f"- Language available: {metadata.language_available}",
            f"- Author available: {metadata.author_available}",
            f"- Description available: {metadata.description_available}",
            "",
            "## Passage Quality Summary",
            "",
            f"- Minimum passage word count: {_display_optional(passage_quality.minimum_passage_word_count)}",
            f"- Maximum passage word count: {_display_optional(passage_quality.maximum_passage_word_count)}",
            f"- Median passage word count: {_display_optional(passage_quality.median_passage_word_count)}",
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
                f"- Structural completeness: {assessment.structural_completeness.value}",
            )
        )
        return "\n".join(lines)
