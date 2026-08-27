"""Turkish text definitions for score dimensions."""

from typing import Dict, TypedDict

class ScoreDimensionText(TypedDict):
    label: str

_SEO_SCORE_TEXTS = {
    "entity_coverage": {"label": "Entity Coverage"},
    "structured_data": {"label": "Structured Data"},
    "semantic_quality": {"label": "Anlamsal Kalite"},
    "technical_access": {"label": "Technical Access"},
}

_GEO_SCORE_TEXTS = {
    "semantic_completeness": {"label": "Semantic Completeness"},
    "entity_authority": {"label": "Entity Authority"},
    "structural_richness": {"label": "Structural Richness"},
    "discoverability": {"label": "Discoverability"},
}

def seo_dimension_text(key: str) -> ScoreDimensionText:
    """Return Turkish text for an SEO dimension."""
    return _SEO_SCORE_TEXTS.get(key, {"label": key})

def geo_dimension_text(key: str) -> ScoreDimensionText:
    """Return Turkish text for a GEO dimension."""
    return _GEO_SCORE_TEXTS.get(key, {"label": key})
