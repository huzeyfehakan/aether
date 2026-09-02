"""Editor-facing wording for the outcome of an analysis attempt.

An editor is never shown why the parser stopped. They are told what was found,
what it most likely means, and what to do next, in the same voice as every
other recommendation.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from aether.application.ingestion.assess_page_content import (
    PageAssessment,
    PageOutcome,
)


@dataclass(frozen=True)
class OutcomeText:
    """One analysis outcome phrased for an editor."""

    headline: str
    what_happened: str
    what_to_do: str


_TEXT: Dict[PageOutcome, OutcomeText] = {
    PageOutcome.ARTICLE_TEXT_UNREADABLE: OutcomeText(
        headline="The page identifies itself as an article, but its text could not be read",
        what_happened=(
            "The page identifies itself to software as an article, but the served "
            "page contains no article text. A system reading outside a browser "
            "can see only the title."
        ),
        what_to_do=(
            "Share this with the technical team that manages the site. The article "
            "text is probably generated in the browser after the page loads; it "
            "needs to be present in the page sent by the server."
        ),
    ),
    PageOutcome.NO_ARTICLE_TEXT_FOUND: OutcomeText(
        headline="No article text was found on this page",
        what_happened=(
            "No article text could be read, and the page does not identify itself "
            "as an article. This is expected for video, listing, and program pages; "
            "Aether found no article to assess here."
        ),
        what_to_do=(
            "If this is not an article, there is no problem and no action is needed. "
            "If it is an article, share this with the technical team because the "
            "text may be generated later in the browser."
        ),
    ),
}

_TEXT_TR: Dict[PageOutcome, OutcomeText] = {
    PageOutcome.ARTICLE_TEXT_UNREADABLE: OutcomeText(
        headline="Sayfa kendisini makale olarak tanımlıyor ancak metni okunamadı",
        what_happened=(
            "Sayfa yazılımlara kendisini makale olarak tanımlıyor ancak sunulan "
            "sayfada makale metni bulunmuyor. Tarayıcı dışında okuyan bir sistem "
            "yalnızca başlığı görebiliyor."
        ),
        what_to_do=(
            "Bunu siteyi yöneten teknik ekiple paylaşın. Makale metni büyük "
            "olasılıkla sayfa yüklendikten sonra tarayıcıda oluşturuluyor; metnin "
            "sunucunun gönderdiği sayfada yer alması gerekir."
        ),
    ),
    PageOutcome.NO_ARTICLE_TEXT_FOUND: OutcomeText(
        headline="Bu sayfada makale metni bulunamadı",
        what_happened=(
            "Makale metni okunamadı ve sayfa kendisini makale olarak tanımlamıyor. "
            "Bu durum video, liste ve program sayfaları için normaldir; Aether "
            "burada değerlendirecek bir makale bulamadı."
        ),
        what_to_do=(
            "Bu bir makale değilse sorun yoktur ve işlem gerekmez. Makaleyse metin "
            "tarayıcıda sonradan oluşturuluyor olabileceğinden teknik ekiple paylaşın."
        ),
    ),
}


def outcome_text(outcome: PageOutcome, language: str = "en") -> OutcomeText:
    return (_TEXT_TR if language == "tr" else _TEXT)[outcome]


def declared_evidence(assessment: PageAssessment) -> Tuple[str, ...]:
    """What the page says about itself, shown so the reader can judge.

    The page's own declaration is reported and never used to classify. Across
    the TRT estate it is wrong in both directions, so presenting it as evidence
    is honest where trusting it would not be.
    """
    evidence = []
    if assessment.declared_page_type:
        evidence.append(
            f"The page identifies itself as “{assessment.declared_page_type}”."
        )
    if assessment.declared_types:
        evidence.append(
            "The structured data on the page declares these types: "
            + ", ".join(assessment.declared_types)
            + "."
        )
    else:
        evidence.append("The page does not publish structured data.")
    return tuple(evidence)


def declared_evidence_tr(assessment: PageAssessment) -> Tuple[str, ...]:
    evidence = []
    if assessment.declared_page_type:
        evidence.append(
            f'Sayfa kendisini “{assessment.declared_page_type}” olarak tanımlıyor.'
        )
    if assessment.declared_types:
        evidence.append(
            "Sayfadaki yapılandırılmış veri şu türleri bildiriyor: "
            + ", ".join(assessment.declared_types)
            + "."
        )
    else:
        evidence.append("Sayfa yapılandırılmış veri yayımlamıyor.")
    return tuple(evidence)


def outcome_view(
    assessment: PageAssessment, language: str = "en"
) -> Optional[Dict[str, object]]:
    """Shape a non-analysable outcome for display, or nothing if it analysed."""
    if assessment.is_analyzable:
        return None
    text = outcome_text(assessment.outcome, language)
    return {
        "outcome": assessment.outcome.value,
        "headline": text.headline,
        "what_happened": text.what_happened,
        "what_to_do": text.what_to_do,
        "evidence": list(
            declared_evidence_tr(assessment)
            if language == "tr"
            else declared_evidence(assessment)
        ),
    }
