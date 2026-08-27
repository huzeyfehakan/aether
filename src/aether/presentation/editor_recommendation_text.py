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
    RecommendationCategory.EDITOR: "Content Recommendations",
    RecommendationCategory.TECHNICAL: "Technical / Site Recommendations",
}

CATEGORY_SUBTITLES: Dict[RecommendationCategory, str] = {
    RecommendationCategory.EDITOR: "Improvements you can make to this article now.",
    RecommendationCategory.TECHNICAL: (
        "These recommendations require changes to the page template or CMS. "
        "They usually affect other articles on the site as well. Share them "
        "with the technical team or site administrator."
    ),
}

# Turkish is the default interface language. Detection continues to emit only
# codes and evidence; this table owns how every code is presented to an editor.
_TEXT_TR: Dict[RecommendationCode, RecommendationText] = {
    RecommendationCode.NO_ARTICLE_STRUCTURED_DATA: RecommendationText(
        "Bu sayfa kendisini makale olarak tanımlamıyor",
        "Schema.org Article yapılandırılmış verisi, yazılımların sayfanın türünü, yazarını ve yayın tarihini doğrudan okumasını sağlar.",
        "Sayfaya headline, datePublished, author ve publisher alanlarını içeren Schema.org Article işaretlemesi ekleyin.",
    ),
    RecommendationCode.INCOMPLETE_ARTICLE_STRUCTURED_DATA: RecommendationText(
        "Makale yapılandırılmış verilerinde eksik alanlar var",
        "Sayfa kendisini makale olarak tanımlıyor ancak Schema.org Article için beklenen bazı bilgileri bildirmiyor.",
        "Eksik alanları Article yapılandırılmış verisine ekleyin.",
    ),
    RecommendationCode.MISSING_PUBLICATION_DATE: RecommendationText(
        "Makalenin yayın tarihi belirtilmemiş", "Yayın tarihi, içeriğin güncelliğini ve haber akışındaki yerini anlamayı sağlar. Bu bilgi olmadan yeni bir haber eski bir içerikten güvenilir biçimde ayrılamaz.",
        "CMS'deki yayın tarihi alanını doldurun; doluysa tarihin yayınlanan sayfaya ulaştığını kontrol edin.",
    ),
    RecommendationCode.MISSING_AUTHOR: RecommendationText(
        "Makalenin yazarı belirtilmemiş", "Yazar bilgisi içeriğin kime veya hangi editoryal birime ait olduğunu açıklar. Bu alan boş olduğunda çalışmanın arkasındaki kişinin veya yayın biriminin uzmanlığı görünmez kalır.",
        "CMS'deki yazar alanını kişi veya sorumlu yayın biriminin adıyla doldurun.",
    ),
    RecommendationCode.MISSING_SUMMARY: RecommendationText(
        "Makalenin özeti yok", "Özet, içeriğin konusunu arama sonuçları ve paylaşılan bağlantılar için kısa biçimde açıklar.",
        "CMS'deki özet veya açıklama alanına, başlığı tekrarlamayan bir ya da iki cümle yazın.",
    ),
    RecommendationCode.MISSING_LAST_MODIFIED_DATE: RecommendationText(
        "Makalenin son güncellenme tarihi belirtilmemiş", "Son güncellenme tarihi düzeltme veya genişletmelerin daha yeni sürümde olduğunu gösterir.",
        "Makale düzenlendiğinde article:modified_time veya Schema.org dateModified alanını yayınlayın.",
    ),
    RecommendationCode.NO_TOP_LEVEL_HEADING: RecommendationText(
        "Makalenin ana başlığı yok", "Ana başlık, içeriğin tamamının konusunu sayfa içinde açıkça belirtir.",
        "Makale gövdesinin başına, kalın metin yerine CMS'nin sunduğu ana başlık biçimini kullanarak bir H1 ekleyin.",
    ),
    RecommendationCode.MULTIPLE_TOP_LEVEL_HEADINGS: RecommendationText(
        "Makalede birden fazla ana başlık var", "Birden fazla H1, hangi başlığın makaleyi tanımladığını belirsizleştirir.",
        "Makale için tek bir H1 bırakın; diğerlerini bölüm başlığı düzeyine indirin.",
    ),
    RecommendationCode.WEAK_ARTICLE_OPENING: RecommendationText(
        "Makalenin girişi çok kısa", "Kısa bir giriş, devamındaki kapsamlı içerik için yeterli bağlam sağlamayabilir.",
        "Başlangıca makalenin konusunu açıkça özetleyen bir veya iki cümle ekleyin.",
    ),
    RecommendationCode.WEAK_TOPIC_INTRODUCTION: RecommendationText(
        "Makalenin konusu girişte açıkça kurulmuyor", "İlk paragraf, başlıktaki ana kavramların çok azını içeriyor.",
        "Makalenin ana konusunu ilk paragrafta açıkça tanıtın.",
    ),
    RecommendationCode.TITLE_SOURCES_DISAGREE: RecommendationText(
        "Sayfadaki başlıklar birbiriyle uyuşmuyor", "Tarayıcı başlığı, sosyal paylaşım başlığı ve yapılandırılmış veri farklı metinler bildiriyor.",
        "Doğru başlığı belirleyip CMS'deki diğer başlık kaynaklarını onunla eşleştirin.",
    ),
    RecommendationCode.DESCRIPTION_SOURCES_DISAGREE: RecommendationText(
        "Sayfadaki özetler birbiriyle uyuşmuyor", "Arama, sosyal paylaşım ve yapılandırılmış veri alanları aynı makale için farklı özetler bildiriyor.",
        "Doğru özeti belirleyip CMS'deki diğer açıklama kaynaklarını onunla eşleştirin.",
    ),
    RecommendationCode.BODY_MOSTLY_REPEATED_TEXT: RecommendationText(
        "Makalenin büyük bölümü diğer makalelerde de bulunan metinlerden oluşuyor", "Tekrarlanan metin makaleye özgü bilgiyi geri plana iter.",
        "Makalenin kendi metninin eksiksiz yayınlandığını kontrol edin; standart uyarıları mümkünse makale gövdesinin dışına taşıyın.",
    ),
    RecommendationCode.REPEATED_TEXT_IN_ARTICLE_BODY: RecommendationText(
        "Bu paragraf diğer makalelerinizde de yer alıyor", "Tekrarlanan paragraf bu makaleyi diğerlerinden ayıran bilgiye katkı sağlamaz.",
        "Metni kaldırın veya yeniden yazın; otomatik ekleniyorsa site ekibinden makale gövdesinin dışında yayınlamasını isteyin.",
    ),
    RecommendationCode.NO_OUTBOUND_LINKS: RecommendationText(
        "Makalede dış kaynak bağlantısı yok", "Dış kaynaklar önemli iddiaların dayanağını ve araştırmanın kapsamını görünür kılar.",
        "İddiaları destekleyen güvenilir ve ilgili dış kaynaklara bağlantı ekleyin.",
    ),
    RecommendationCode.NO_CITATIONS: RecommendationText(
        headline="This article contains no citations",
        why_it_matters="Citations show which evidence supports verifiable claims.",
        what_to_do="Add reliable source links or explicit citations for important claims.",
    ),
    RecommendationCode.NO_CITATIONS: RecommendationText(
        "Makalede kaynak gösterimi yok", "Kaynak gösterimi, doğrulanabilir iddiaların hangi kanıta dayandığını açıklar.",
        "Önemli iddialara güvenilir kaynak bağlantıları veya açık atıflar ekleyin.",
    ),
    RecommendationCode.NO_STATISTICS: RecommendationText(
        "Makalede istatistik veya sayısal veri yok", "Sayısal veriler iddiaları somutlaştırır ve kapsamı daha açık hale getirir.",
        "Uygun olan iddiaları güvenilir istatistikler, yüzdeler veya sayısal verilerle destekleyin.",
    ),
    RecommendationCode.ORPHAN_PAGE: RecommendationText(
        "Makaleye site içinden bağlantı verilmiyor", "Site içi bağlantılar ilgili içerikler arasındaki ilişkiyi ve erişim yolunu gösterir.",
        "İlgili kategori veya makalelerden bu sayfaya anlamlı bir iç bağlantı ekleyin.",
    ),
    RecommendationCode.NO_INTERNAL_BODY_LINKS: RecommendationText(
        "Makale gövdesinde iç bağlantı yok", "İç bağlantılar okuyucuyu ilgili içeriklere yönlendirir ve konu bağlamını güçlendirir.",
        "Ana metne sitenizdeki ilgili makalelere yönlendiren bağlantılar ekleyin.",
    ),
    RecommendationCode.ORPHAN_PAGE: RecommendationText(
        headline="No analyzed page links to this article",
        why_it_matters="Internal links make the path to related content visible.",
        what_to_do="Add a meaningful internal link from a relevant category or article.",
    ),
    RecommendationCode.CONTENT_BLOAT: RecommendationText(
        "Konuyla zayıf ilişkili paragrafları sadeleştirin", "Başlığıyla ortak kavram taşımayan paragraflar makalenin düzenini belirsizleştirebilir.",
        "Ana konuyla ilişkisi zayıf paragrafları kaldırın, yeniden yazın veya uygun bölüm altında konumlandırın.",
    ),
    RecommendationCode.SKIPPED_HEADING_LEVEL: RecommendationText(
        "Başlık hiyerarşisinde seviye atlanmış", "H1, H2 ve H3 sırası makalenin mantıksal bölüm yapısını gösterir.",
        "Başlık seviyelerini numara atlamadan sıralı biçimde düzenleyin.",
    ),
    RecommendationCode.CONFLICTING_PUBLISHED_DATES: RecommendationText(
        "Yayın tarihleri birbiriyle uyuşmuyor", "Meta, JSON-LD ve time alanlarındaki farklı tarihler güncellik bilgisini belirsizleştirir.",
        "CMS'nin JSON-LD, article:published_time ve HTML time alanlarında aynı yayın tarihini kullandığını doğrulayın.",
    ),
    RecommendationCode.UNSUPPORTED_ENTITIES: RecommendationText(
        "Kurum ve ürün adlarını kaynaklarla destekleyin", "Özel isimlerin geçtiği bazı paragraflarda onları destekleyen bağımsız kanıt bulunmuyor.",
        "İlgili paragraflara güvenilir istatistikler veya bağımsız dış kaynaklar ekleyin.",
    ),
    RecommendationCode.LOW_TRUST_INDEX: RecommendationText(
        headline="Strengthen source reliability",
        why_it_matters="The article has limited source variety and independent support.",
        what_to_do="Support important claims with reliable primary and independent sources.",
    ),
    RecommendationCode.LOW_TRUST_INDEX: RecommendationText(
        "Kaynak güvenilirliğini güçlendirin", "İçerikteki kaynak çeşitliliği ve bağımsız dayanaklar sınırlı görünüyor.",
        "Önemli iddiaları birincil ve bağımsız güvenilir kaynaklarla destekleyin.",
    ),
    RecommendationCode.MISSING_SAME_AS_SCHEMA: RecommendationText(
        "Yapılandırılmış veride sameAs eksik", "sameAs, yazar ve kurum gibi varlıkların doğrulanmış profillerle eşleştirilmesini sağlar.",
        "Schema.org JSON-LD içinde uygun Wikipedia veya Wikidata profillerini sameAs alanıyla belirtin.",
    ),
}


_TEXT_EN: Dict[RecommendationCode, RecommendationText] = {
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
    RecommendationCode.WEAK_ARTICLE_OPENING: RecommendationText(
        headline="The article opening is very short",
        why_it_matters=(
            "The article contains substantial content, but its opening paragraph "
            "provides very little context before the rest of the story."
        ),
        what_to_do=(
            "Add one or two sentences near the beginning that clearly summarize "
            "what the article is about."
        ),
    ),
    RecommendationCode.WEAK_TOPIC_INTRODUCTION: RecommendationText(
    headline="The article topic is not clearly established in the opening",
    why_it_matters=(
        "The opening paragraph contains few of the main terms used "
        "in the article title, which can make the subject less explicit."
    ),
    what_to_do=(
        "Introduce the article's main topic explicitly in the opening paragraph."
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
        headline="Simplify isolated and bloated content",
        why_it_matters=(
            "Paragraphs that do not share vocabulary with their heading can make "
            "the article's organization less explicit."
        ),
        what_to_do=(
            "Remove filler paragraphs that have weak ties to the main heading or associate them with the main theme."
        ),
    ),
    RecommendationCode.SKIPPED_HEADING_LEVEL: RecommendationText(
        headline="Heading hierarchy skips a level",
        why_it_matters=(
            "AI crawlers parse heading structures (H1, H2, H3, H4) as a logical outline. "
            "Skipping heading levels (like jumping directly from H2 to H4) breaks the document's semantic structure."
        ),
        what_to_do=(
            "Fix your heading hierarchy so that every heading level steps down linearly without skipping numbers."
        ),
    ),
    RecommendationCode.CONFLICTING_PUBLISHED_DATES: RecommendationText(
        headline="Published dates conflict",
        why_it_matters=(
            "Conflicting dates in metadata, JSON-LD, and time elements make the "
            "article's publication timeline unclear."
        ),
        what_to_do=(
            "Make sure the CMS publishes the same date in JSON-LD, "
            "article:published_time, and the HTML time element."
        ),
    ),
    RecommendationCode.UNSUPPORTED_ENTITIES: RecommendationText(
        headline="Support named organizations and products with evidence",
        why_it_matters=(
            "Some passages name organizations or specific products without "
            "supporting evidence."
        ),
        what_to_do=(
            "Add relevant statistics or independent external sources that support "
            "the claims in those passages."
        ),
    ),
    RecommendationCode.MISSING_SAME_AS_SCHEMA: RecommendationText(
        headline="Structured data does not declare sameAs",
        why_it_matters=(
            "The sameAs property connects authors and organizations to their "
            "verified profiles."
        ),
        what_to_do=(
            "Declare the author's and organization's relevant Wikipedia or "
            "Wikidata profiles with sameAs in the page's Schema.org JSON-LD."
        ),
    ),
}

_TEXT_EN.update({
    RecommendationCode.NO_CITATIONS: RecommendationText(
        "This article contains no citations",
        "Citations show which evidence supports verifiable claims.",
        "Add reliable source links or explicit citations for important claims.",
    ),
    RecommendationCode.ORPHAN_PAGE: RecommendationText(
        "No analyzed page links to this article",
        "Internal links make the path to related content visible.",
        "Add a meaningful internal link from a relevant category or article.",
    ),
    RecommendationCode.LOW_TRUST_INDEX: RecommendationText(
        "Strengthen source reliability",
        "The article has limited source variety and independent support.",
        "Support important claims with reliable primary and independent sources.",
    ),
})


def recommendation_text(recommendation: EditorRecommendation) -> RecommendationText:
    """Return the editor-facing wording for one recommendation."""
    return _TEXT_EN[recommendation.code]


def category_title(category: RecommendationCategory) -> str:
    return CATEGORY_TITLES[category]


def category_subtitle(category: RecommendationCategory) -> str:
    return CATEGORY_SUBTITLES[category]


#: Editor-facing names for the Schema.org properties this report checks.
_PROPERTY_LABELS = {
    "headline": "headline",
    "description": "description",
    "datePublished": "datePublished",
    "dateModified": "dateModified",
    "author": "author",
    "publisher": "publisher",
    "image": "image",
    "inLanguage": "inLanguage",
}


def missing_properties_phrase(missing_properties) -> str:
    """Name the undeclared details in words an editor recognises."""
    labels = [_PROPERTY_LABELS.get(name, name) for name in missing_properties]
    if len(labels) == 1:
        return f"Missing field: {labels[0]}"
    return "Missing fields: " + ", ".join(labels)


#: Editor-facing names for the places a page can state its title.
_TITLE_SOURCE_LABELS = {
    "document_title": "Browser tab title",
    "open_graph": "Social sharing title",
    "structured_data": "Structured data title",
    "meta_description": "Search result description",
    "og_description": "Social sharing description",
    "twitter_description": "Twitter card description",
    "structured_data_description": "Structured data description",
}


def title_source_label(source: str) -> str:
    return _TITLE_SOURCE_LABELS.get(source, source)


def shared_words_phrase(repeated_word_count: int, total_word_count: int) -> str:
    """State the share as the two counts, so the reader judges rather than a rule."""
    return (
        f"{repeated_word_count} of {total_word_count} words in this article also "
        "appear in your other articles"
    )


def heading_count_phrase(heading_count: int) -> str:
    """State how many top-level headings were found, in its own words.

    This has its own fact rather than borrowing the repetition count, which
    the report words as "also appears in N other articles" and which described
    a heading count as though it were duplication.
    """
    return f"{heading_count} headings are used as main headings"


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
            "Repeated text could not be checked because no articles from this "
            "publisher have been analyzed yet."
        )
    return (
        "Compared with previously analyzed articles from this publisher "
        f"({compared_article_count} {'article' if compared_article_count == 1 else 'articles'})."
    )


_IMPACT_LABELS = {}


def impact_label(value: str) -> str:
    """Return the English display label without changing internal keys."""
    return _IMPACT_LABELS.get(value, value)
