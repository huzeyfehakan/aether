"""Editor-facing wording for recommendations.

Wording lives in presentation, not in the use case that decides which
recommendation applies. That keeps copy out of the application layer and leaves
room for a Turkish edition of the same recommendation codes.

Two rules govern the language. Say what was observed, never what a model will
do: the product does not predict how any AI system ranks or quotes an article,
so no wording may imply it. Use the words an editor uses -- paragraph, article,
notice -- rather than the vocabulary of the parser.

Content quality wording describes the article itself and makes no claim about
machines. AI visibility wording may describe what a specification asks a
publisher to declare, because that is checkable.
"""

from dataclasses import dataclass
from typing import Dict

from aether.application.analysis.derive_editor_recommendations import (
    EditorRecommendation,
    RecommendationCategory,
    RecommendationCode,
)


@dataclass(frozen=True)
class RecommendationText:
    """One recommendation phrased for an editor."""

    headline: str
    why_it_matters: str
    what_to_do: str


CATEGORY_TITLES: Dict[RecommendationCategory, str] = {
    RecommendationCategory.EDITOR: "Editor Recommendations",
    RecommendationCategory.TECHNICAL: "Technical AI Readiness",
}

CATEGORY_SUBTITLES: Dict[RecommendationCategory, str] = {
    RecommendationCategory.EDITOR: "Things you can change in this article now.",
    RecommendationCategory.TECHNICAL: (
        "Things that need a change to the page template or the CMS. These "
        "usually apply to every article on the site, not just this one. Share "
        "them with whoever maintains it."
    ),
}


_TEXT: Dict[RecommendationCode, RecommendationText] = {
    RecommendationCode.NO_ARTICLE_STRUCTURED_DATA: RecommendationText(
        headline="This page does not identify itself as an article",
        why_it_matters=(
            "Schema.org is the shared vocabulary publishers use to tell "
            "software what a page is. Without it, anything reading this page "
            "has to infer from the layout that it is an article, who wrote it "
            "and when it was published."
        ),
        what_to_do=(
            "Add Schema.org Article markup to the page, declaring at least the "
            "headline, publication date, author and publisher."
        ),
    ),
    RecommendationCode.INCOMPLETE_ARTICLE_STRUCTURED_DATA: RecommendationText(
        headline="Your article markup leaves some details undeclared",
        why_it_matters=(
            "The page identifies itself as an article, but does not declare "
            "everything Schema.org provides for. Each undeclared detail is one "
            "an AI system has to guess at from the page text instead of "
            "reading it directly."
        ),
        what_to_do="Add the missing properties to the Article markup.",
    ),
    RecommendationCode.MISSING_PUBLICATION_DATE: RecommendationText(
        headline="This article does not say when it was published",
        why_it_matters=(
            "A publication date is how anything reading the page tells a piece "
            "written today from one written three years ago. Without it this "
            "article cannot be placed in the sequence of coverage on its "
            "subject, and cannot be shown as current when it is."
        ),
        what_to_do=(
            "Set the publish date on the article in your CMS. If that field is "
            "already filled, the date is not reaching the published page and "
            "whoever maintains the site needs to add it to the page markup."
        ),
    ),
    RecommendationCode.MISSING_AUTHOR: RecommendationText(
        headline="This article does not name who wrote it",
        why_it_matters=(
            "The byline is how a reader, and anything reading the page, knows "
            "who stands behind the article. Without it the work can only be "
            "attributed to the site as a whole, so the expertise of the person "
            "or desk that produced it is invisible."
        ),
        what_to_do=(
            "Fill in the author field for this article in your CMS. If the "
            "piece is published by a desk rather than a person, name the desk "
            "explicitly rather than leaving the field empty."
        ),
    ),
    RecommendationCode.MISSING_SUMMARY: RecommendationText(
        headline="This article has no summary",
        why_it_matters=(
            "The summary is the shortest statement of what the article is "
            "about, and it is what appears beneath the headline in search "
            "results and on shared links. Without one, other software writes "
            "its own from whatever the article happens to open with."
        ),
        what_to_do=(
            "Write one or two sentences in the summary or description field of "
            "your CMS, saying what the article establishes rather than "
            "repeating the headline."
        ),
    ),
    RecommendationCode.MISSING_LAST_MODIFIED_DATE: RecommendationText(
        headline="This article does not say when it was last updated",
        why_it_matters=(
            "An article that has been corrected or expanded looks identical to "
            "one that has never changed. Anything reading the page has no way "
            "to know a newer version exists, so a correction may never be "
            "picked up."
        ),
        what_to_do=(
            "Have the page publish a last-modified date whenever an article is "
            "edited, through article:modified_time or the Schema.org "
            "dateModified property."
        ),
    ),
    RecommendationCode.NO_TOP_LEVEL_HEADING: RecommendationText(
        headline="This article has no main heading",
        why_it_matters=(
            "The main heading is what states, inside the article itself, what "
            "the whole piece is about. Without one a reader skimming the page "
            "has nothing to anchor on, and software reading it has to fall "
            "back on the browser tab title, which often carries the site name "
            "rather than the story."
        ),
        what_to_do=(
            "Give the article a main heading at the top of the body, styled as "
            "the largest heading level your CMS offers, rather than as bold "
            "text."
        ),
    ),
    RecommendationCode.MULTIPLE_TOP_LEVEL_HEADINGS: RecommendationText(
        headline="This article has more than one main heading",
        why_it_matters=(
            "When several headings claim to be the top of the article, nothing "
            "reading the page can tell which one names the piece. The others "
            "look like separate articles rather than sections of this one."
        ),
        what_to_do=(
            "Keep one main heading for the article and demote the rest to "
            "section headings."
        ),
    ),
    RecommendationCode.TITLE_SOURCES_DISAGREE: RecommendationText(
        headline="This article gives more than one headline",
        why_it_matters=(
            "The page states its title in several places, and they do not all "
            "say the same thing. Readers see one headline, while software "
            "reading the page may take another. Formatting differences such as "
            "the site name or punctuation are ignored here, so this is a "
            "genuine difference in wording."
        ),
        what_to_do=(
            "Decide which headline is correct and make the others match it in "
            "your CMS."
        ),
    ),
    RecommendationCode.DESCRIPTION_SOURCES_DISAGREE: RecommendationText(
        headline="This article gives more than one summary",
        why_it_matters=(
            "The page states its summary in several places, and they do not "
            "all say the same thing. Search results, social cards and software "
            "reading the page may each show a different summary of the same "
            "article. Formatting differences such as an added tagline or "
            "punctuation are ignored here, so this is a genuine difference in "
            "wording."
        ),
        what_to_do=(
            "Decide which summary is correct and make the others match it in "
            "your CMS."
        ),
    ),
    RecommendationCode.BODY_MOSTLY_REPEATED_TEXT: RecommendationText(
        headline="Most of this article is text that appears in your other articles",
        why_it_matters=(
            "More of this article's words are shared with your other articles "
            "than are its own. Anything reading the page to learn what this "
            "piece says finds mostly text it has already seen elsewhere, with "
            "little that belongs to this story."
        ),
        what_to_do=(
            "Check that the article's own text is reaching the published page. "
            "If standing notices such as a disclaimer or a byline make up most "
            "of the body, they belong outside it."
        ),
    ),
    RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY: RecommendationText(
        headline="This paragraph also appears in your other articles",
        why_it_matters=(
            "Repeated text is not part of what makes this article distinct. It "
            "adds length to the article body without adding anything specific "
            "to this story."
        ),
        what_to_do=(
            "If you added this text, consider removing or rewriting it. If it "
            "appears automatically on every article, ask whoever maintains the "
            "site to publish it outside the article body."
        ),
    ),
    RecommendationCode.NO_OUTBOUND_LINKS: RecommendationText(
        headline="This article contains no outbound links",
        why_it_matters=(
            "Generative AI engines measure Entity Authority by checking if an article "
            "links to external references. Providing citations to other domains signals "
            "trustworthiness and deep research."
        ),
        what_to_do=(
            "Add relevant outbound links to authoritative external sources to back up your claims."
        ),
    ),
    RecommendationCode.NO_CITATIONS: RecommendationText(
        headline="This article lacks formal citations",
        why_it_matters=(
            "AI engines trust factual content supported by explicit references. "
            "Formal citation marks like [1] or (Source: Example) are strong signals of "
            "Entity Authority."
        ),
        what_to_do=(
            "Add explicit citation markers like [1] or [2] next to your claims to prove their source."
        ),
    ),
    RecommendationCode.NO_STATISTICS: RecommendationText(
        headline="This article contains no statistics or data points",
        why_it_matters=(
            "Quantitative data significantly boosts an article's Semantic Completeness. "
            "AI engines prioritize content that can support its claims with hard numbers."
        ),
        what_to_do=(
            "Include concrete statistics, percentages, and numerical data points to support your arguments."
        ),
    ),
    RecommendationCode.ORPHAN_PAGE: RecommendationText(
        headline="This article is an orphan page (No incoming links)",
        why_it_matters=(
            "Without any other articles on your site linking to it, AI crawlers will "
            "struggle to discover and index this page. It severely hurts your Discoverability score."
        ),
        what_to_do=(
            "Link to this article from relevant, older articles on your website to establish a content cluster."
        ),
    ),
    RecommendationCode.NO_INTERNAL_BODY_LINKS: RecommendationText(
        headline="This article contains no internal links in its body",
        why_it_matters=(
            "Articles that don't link to other related content create dead ends for "
            "readers and AI crawlers. Internal linking distributes authority and context."
        ),
        what_to_do=(
            "Add internal links within the main body text to other relevant articles on your site."
        ),
    ),
    RecommendationCode.CONTENT_BLOAT: RecommendationText(
        headline="İzole ve Şişirme İçeriği Sadeleştirin",
        why_it_matters=(
            "AI engines penalize 'content bloat'. Paragraphs that don't share vocabulary "
            "with their heading and lack a definitive stance dilute your Semantic Completeness."
        ),
        what_to_do=(
            "Remove filler paragraphs that have weak ties to the main heading or associate them with the main theme."
        ),
    ),
    RecommendationCode.SKIPPED_HEADING_LEVEL: RecommendationText(
        headline="Anlamsal Kopukluk: Başlık Hiyerarşisi Atlanmış",
        why_it_matters=(
            "AI crawlers parse heading structures (H1, H2, H3, H4) as a logical outline. "
            "Skipping heading levels (like jumping directly from H2 to H4) breaks the document's semantic structure."
        ),
        what_to_do=(
            "Fix your heading hierarchy so that every heading level steps down linearly without skipping numbers."
        ),
    ),
    RecommendationCode.CONFLICTING_PUBLISHED_DATES: RecommendationText(
        headline="Çelişkili Tarih Verileri (Sanity Check Başarısız)",
        why_it_matters=(
            "Yapay zeka arama motorları, tazeliği doğrulamak için Meta, JSON-LD ve <time> etiketlerindeki tarihleri çapraz kontrol eder. "
            "Eğer bu tarihler uyuşmuyorsa kaynağın güvenilirliği sarsılır."
        ),
        what_to_do=(
            "CMS'nizin JSON-LD, meta property='article:published_time' ve HTML <time> etiketlerine aynı (veya uyumlu) tarih damgasını bastığından emin olun."
        ),
    ),
    RecommendationCode.UNSUPPORTED_ENTITIES: RecommendationText(
        headline="Kanıtsız Varlıkları (Kurum/Ürün) Destekleyin",
        why_it_matters=(
            "Özel isimlerin, kurum veya spesifik ürünlerin geçtiği paragraflarda birincil kanıt eksikliği bulunuyor."
        ),
        what_to_do=(
            "Yapay zeka motorlarının bu varlıkları (entity) güvenilir bir kaynak olarak referans alabilmesi için, ilgili paragraflara iddialarınızı kanıtlayan istatistiksel veriler veya bağımsız dış atıflar ekleyin."
        ),
    ),
    RecommendationCode.LOW_TRUST_INDEX: RecommendationText(
        headline="Otoriter Kaynak Referanslarını Güçlendirin",
        why_it_matters=(
            "Wikipedia ve .gov gibi otoriter domainlere atıf yapmak, yapay zeka modelleri nezdinde makalenin güvenilirliğini artırır."
        ),
        what_to_do=(
            "İddialarınızı ve kurumları desteklemek için Wikipedia veya resmî kurumlara (.gov, .edu) dış bağlantılar ekleyin."
        ),
    ),
    RecommendationCode.MISSING_SAME_AS_SCHEMA: RecommendationText(
        headline="Yapısal Veri (sameAs) Kullanımı Eksik",
        why_it_matters=(
            "Yapay zeka motorlarının varlıkları Knowledge Graph ile eşleştirebilmesi için sameAs özelliğine ihtiyacı vardır."
        ),
        what_to_do=(
            "Sayfanın Schema.org JSON-LD bloğunda, yazarın ve kurumun Wikipedia/Wikidata profillerini sameAs özelliğiyle belirtin."
        ),
    ),
}


def recommendation_text(recommendation: EditorRecommendation) -> RecommendationText:
    """Return the editor-facing wording for one recommendation."""
    return _TEXT[recommendation.code]


def category_title(category: RecommendationCategory) -> str:
    return CATEGORY_TITLES[category]


def category_subtitle(category: RecommendationCategory) -> str:
    return CATEGORY_SUBTITLES[category]


#: Editor-facing names for the Schema.org properties this report checks.
_PROPERTY_LABELS = {
    "headline": "headline",
    "description": "summary",
    "datePublished": "publication date",
    "dateModified": "last updated date",
    "author": "author",
    "publisher": "publisher",
    "image": "image",
    "inLanguage": "language",
}


def missing_properties_phrase(missing_properties) -> str:
    """Name the undeclared details in words an editor recognises."""
    labels = [_PROPERTY_LABELS.get(name, name) for name in missing_properties]
    if len(labels) == 1:
        return f"Not declared: {labels[0]}"
    return "Not declared: " + ", ".join(labels[:-1]) + f" and {labels[-1]}"


#: Editor-facing names for the places a page can state its title.
_TITLE_SOURCE_LABELS = {
    "document_title": "Browser tab title",
    "open_graph": "Social sharing title",
    "structured_data": "Structured data headline",
    "meta_description": "Search result summary",
    "og_description": "Social sharing summary",
    "twitter_description": "Twitter card summary",
    "structured_data_description": "Structured data summary",
}


def title_source_label(source: str) -> str:
    return _TITLE_SOURCE_LABELS.get(source, source)


def shared_words_phrase(repeated_word_count: int, total_word_count: int) -> str:
    """State the share as the two counts, so the reader judges rather than a rule."""
    return (
        f"{repeated_word_count} of {total_word_count} words in this article "
        "also appear in your other articles"
    )


def heading_count_phrase(heading_count: int) -> str:
    """State how many top-level headings were found, in its own words.

    This has its own fact rather than borrowing the repetition count, which
    the report words as "also appears in N other articles" and which described
    a heading count as though it were duplication.
    """
    return f"{heading_count} headings claim to be the main heading"


def repeated_in_phrase(other_article_count: int) -> str:
    """Describe how widely a paragraph is repeated, in plain language."""
    if other_article_count == 1:
        return "Also appears in 1 other article"
    return f"Also appears in {other_article_count} other articles"


def compared_articles_phrase(compared_article_count: int) -> str:
    """State the evidence a reuse finding rests on, always.

    The wording names the limit plainly: the comparison covers articles that
    have been analyzed before, not everything the publisher has ever
    published. An editor who reads a small number here should read the finding
    as narrow rather than as a statement about their whole site.
    """
    if compared_article_count == 0:
        return (
            "No previously analyzed articles from this publisher, so repeated "
            "text could not be checked."
        )
    article_word = "article" if compared_article_count == 1 else "articles"
    return (
        "Compared against previously analyzed articles from this publisher "
        f"({compared_article_count} {article_word})."
    )
