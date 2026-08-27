"""Editor-facing wording for what a draft review did and did not check.

These sentences were built in the use case that decides which checks apply,
which fixed the report to one language and put copywriting inside application
logic. They live here for the same reason recommendation wording does.

Two rules govern the language. A check that could not run is stated with its
reason and never as something missing: an editor reads "not yet", not "you
forgot". And the reason is the real one -- waiting for the page to exist,
having no formatting to read, or having nothing chosen to compare against are
three different situations and are never worded alike.
"""

from typing import Dict

from aether.application.analysis.build_draft_review import (
    DraftCheck,
    UnavailableCheck,
)

PERFORMED_TEXT: Dict[DraftCheck, str] = {
    DraftCheck.PARAGRAPH_STRUCTURE: "Paragraf yapısı",
    DraftCheck.HEADING_STRUCTURE: "Başlık yapısı",
    DraftCheck.REPEATED_TEXT: "Diğer makalelerinizde tekrarlanan metin",
}

UNAVAILABLE_TEXT: Dict[UnavailableCheck, str] = {
    UnavailableCheck.PUBLISHED_METADATA: (
        "Makale yayınlandığında belirlenen yayın tarihi, yazar ve özet"
    ),
    UnavailableCheck.DECLARED_CONSISTENCY: (
        "Sayfanın tek bir başlık ve özet bildirip bildirmediği; bunun için "
        "yayınlanmış sayfa gerekir"
    ),
    UnavailableCheck.STRUCTURED_DATA: (
        "Site şablonunun ürettiği Schema.org yapılandırılmış verisi"
    ),
    UnavailableCheck.HEADING_STRUCTURE_WITHOUT_MARKUP: (
        "Yapıştırılan taslak biçimlendirme içermediği için başlık yapısı"
    ),
    UnavailableCheck.REPEATED_TEXT_NO_PUBLISHER: (
        "Taslağın karşılaştırılacağı yayıncı seçilmediği için diğer "
        "makalelerde tekrarlanan metin"
    ),
    UnavailableCheck.REPEATED_TEXT_NO_ARTICLES: (
        "Bu yayıncıdan henüz makale analiz edilmediği için diğer makalelerde "
        "tekrarlanan metin"
    ),
}


def performed_check_text(check: DraftCheck) -> str:
    return PERFORMED_TEXT[check]


def unavailable_check_text(check: UnavailableCheck) -> str:
    return UNAVAILABLE_TEXT[check]
