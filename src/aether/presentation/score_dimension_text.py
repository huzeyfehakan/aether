"""Turkish text definitions for score dimensions."""

from typing import Dict, TypedDict

class ScoreDimensionText(TypedDict):
    label: str

_SEO_SCORE_TEXTS = {
    "entity_coverage": {"label": "Varlık Kapsamı"},
    "structured_data": {"label": "Yapısal Veri"},
    "semantic_quality": {"label": "Anlamsal Kalite"},
    "technical_access": {"label": "Teknik Erişim"},
}

_GEO_SCORE_TEXTS = {
    "semantic_completeness": {"label": "Anlamsal Bütünlük"},
    "entity_authority": {"label": "Varlık Otoritesi"},
    "structural_richness": {"label": "Yapısal Zenginlik"},
    "discoverability": {"label": "Keşfedilebilirlik"},
}

def seo_dimension_text(key: str) -> ScoreDimensionText:
    """Return Turkish text for an SEO dimension."""
    return _SEO_SCORE_TEXTS.get(key, {"label": key})

def geo_dimension_text(key: str) -> ScoreDimensionText:
    """Return Turkish text for a GEO dimension."""
    return _GEO_SCORE_TEXTS.get(key, {"label": key})
