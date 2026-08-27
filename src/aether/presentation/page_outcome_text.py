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
        headline="Sayfa kendisini makale olarak tanımlıyor ancak metni okunamadı",
        what_happened=(
            "Sayfa yazılımlara kendisini makale olarak tanıtıyor ancak sunduğu "
            "sayfada makale metni bulunmuyor. Tarayıcı dışında sayfayı okuyan "
            "bir sistem yalnızca başlığı görüyor."
        ),
        what_to_do=(
            "Bunu siteyi yöneten teknik ekiple paylaşın. Makale metni büyük "
            "olasılıkla sayfa yüklendikten sonra tarayıcıda oluşturuluyor; "
            "metnin sunucunun gönderdiği sayfada bulunması gerekir."
        ),
    ),
    PageOutcome.NO_ARTICLE_TEXT_FOUND: OutcomeText(
        headline="Bu sayfada makale metni bulunamadı",
        what_happened=(
            "Sayfadan makale metni okunamadı ve sayfa kendisini makale olarak "
            "tanımlamıyor. Video, liste ve program sayfalarında bu beklenen "
            "bir durumdur; Aether burada değerlendirecek bir makale bulamadı."
        ),
        what_to_do=(
            "Bu bir makale değilse sorun yoktur ve işlem gerekmez. Makaleyse, "
            "metin muhtemelen tarayıcıda sonradan oluşturulduğu için durumu "
            "siteyi yöneten teknik ekiple paylaşın."
        ),
    ),
}


def outcome_text(outcome: PageOutcome) -> OutcomeText:
    return _TEXT[outcome]


def declared_evidence(assessment: PageAssessment) -> Tuple[str, ...]:
    """What the page says about itself, shown so the reader can judge.

    The page's own declaration is reported and never used to classify. Across
    the TRT estate it is wrong in both directions, so presenting it as evidence
    is honest where trusting it would not be.
    """
    evidence = []
    if assessment.declared_page_type:
        evidence.append(
            f"Sayfa kendisini “{assessment.declared_page_type}” olarak tanımlıyor."
        )
    if assessment.declared_types:
        evidence.append(
            "Sayfadaki yapılandırılmış veri şu türleri tanımlıyor: "
            + ", ".join(assessment.declared_types)
            + "."
        )
    else:
        evidence.append("Sayfa yapılandırılmış veri yayınlamıyor.")
    return tuple(evidence)


def outcome_view(assessment: PageAssessment) -> Optional[Dict[str, object]]:
    """Shape a non-analysable outcome for display, or nothing if it analysed."""
    if assessment.is_analyzable:
        return None
    text = outcome_text(assessment.outcome)
    return {
        "outcome": assessment.outcome.value,
        "headline": text.headline,
        "what_happened": text.what_happened,
        "what_to_do": text.what_to_do,
        "evidence": list(declared_evidence(assessment)),
    }
