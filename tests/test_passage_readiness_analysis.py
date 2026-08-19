import sys
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

sys.path.insert(0, "src")

from aether.adapters.outbound.in_memory_content_repository import (  # noqa: E402
    InMemoryContentRepository,
)
from aether.application.analysis.analyze_heading_structure import (  # noqa: E402
    AnalyzeHeadingStructure,
)
from aether.application.analysis.analyze_passage_quality import (  # noqa: E402
    AnalyzePassageQuality,
)
from aether.application.analysis.analyze_passage_readiness import (  # noqa: E402
    AnalyzePassageReadiness,
)
from aether.application.ingestion.register_raw_html_article import (  # noqa: E402
    RawHtmlArticle,
    RegisterRawHtmlArticle,
)
from aether.application.ingestion.register_source_snapshot import (  # noqa: E402
    RegisterSourceSnapshot,
    SourceArticleSnapshot,
)
from aether.domain.common import DomainValidationError  # noqa: E402
from aether.domain.source_data import DeclaredHeading  # noqa: E402


NOW = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)


def _page(body_html, language="tr"):
    return (
        '<html lang="%s"><head><title>Sayfa</title></head><body><article>%s'
        "</article></body></html>" % (language, body_html)
    )


class PassageReadinessAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryContentRepository()
        self.ingest = RegisterRawHtmlArticle(self.repository)
        self.analyze = AnalyzePassageReadiness(
            self.repository,
            AnalyzeHeadingStructure(self.repository),
            AnalyzePassageQuality(self.repository),
        )

    def analyze_page(self, body_html, language="tr", source_url="https://example.org/a"):
        registered = self.ingest.execute(
            RawHtmlArticle(
                html=_page(body_html, language),
                source_url=source_url,
                publisher="TRT",
                article_type="news_report",
                observed_at=NOW,
            )
        )
        return self.analyze.execute(
            registered.article, registered.article_version.article_version_id
        )

    # -- sectioning --------------------------------------------------------

    def test_each_heading_owns_the_passages_that_follow_it(self):
        analysis = self.analyze_page(
            "<h1>Giriş</h1><p>Birinci paragraf burada.</p>"
            "<p>İkinci paragraf burada.</p>"
            "<h2>Ayrıntı</h2><p>Üçüncü paragraf burada.</p>"
        )

        self.assertEqual(
            [(section.heading_text, section.passage_ordinals) for section in analysis.sections],
            [("Giriş", (0, 1)), ("Ayrıntı", (2,))],
        )
        self.assertEqual(analysis.section_count, 2)

    def test_passages_before_the_first_heading_form_a_section_with_no_heading(self):
        analysis = self.analyze_page(
            "<p>Başlıktan önceki paragraf.</p><h2>Bölüm</h2><p>Bölüm paragrafı.</p>"
        )

        leading = analysis.sections[0]
        self.assertIsNone(leading.heading_text)
        self.assertIsNone(leading.heading_level)
        self.assertFalse(leading.has_heading)
        self.assertEqual(leading.passage_ordinals, (0,))
        self.assertEqual(analysis.passages_before_first_heading, 1)

    def test_an_article_without_headings_is_one_section_holding_every_passage(self):
        analysis = self.analyze_page("<p>Tek paragraf.</p><p>İkinci paragraf.</p>")

        self.assertEqual(analysis.section_count, 1)
        self.assertFalse(analysis.sections[0].has_heading)
        self.assertEqual(analysis.sections[0].passage_ordinals, (0, 1))
        self.assertEqual(analysis.passages_before_first_heading, 2)

    def test_consecutive_headings_leave_the_earlier_section_empty(self):
        analysis = self.analyze_page(
            "<h2>Yöntem</h2><h3>Kaynaklar</h3><p>Veriler kurumdan alındı.</p>"
        )

        self.assertEqual(
            [(section.heading_text, section.is_empty) for section in analysis.sections],
            [("Yöntem", True), ("Kaynaklar", False)],
        )
        self.assertEqual(
            [section.heading_text for section in analysis.empty_sections], ["Yöntem"]
        )

    def test_section_word_count_sums_the_passages_it_holds(self):
        analysis = self.analyze_page(
            "<h2>Bölüm</h2><p>Bir iki üç.</p><p>Dört beş.</p>"
        )

        self.assertEqual(analysis.sections[0].word_count, 5)
        self.assertEqual(analysis.sections[0].passage_count, 2)

    def test_every_passage_resolves_to_exactly_one_section(self):
        analysis = self.analyze_page(
            "<p>Önsöz.</p><h2>Bir</h2><p>Bir bölümü.</p><h2>İki</h2><p>İki bölümü.</p>"
        )

        assigned = [profile.section_ordinal for profile in analysis.passage_profiles]
        self.assertEqual(assigned, [0, 1, 2])
        held = [
            ordinal
            for section in analysis.sections
            for ordinal in section.passage_ordinals
        ]
        self.assertEqual(sorted(held), [0, 1, 2])

    # -- definition signals ------------------------------------------------

    def test_reports_a_definition_opening_with_the_sentence_it_came_from(self):
        analysis = self.analyze_page(
            "<p>Enflasyon, fiyatlar genel düzeyinin sürekli artışıdır.</p>"
            "<p>Bakan dün Ankara'da bir toplantıya katıldı.</p>"
        )

        first, second = analysis.passage_profiles
        self.assertTrue(first.opens_with_definition)
        self.assertEqual(first.definition_opening.construction, "copular_predicate")
        self.assertEqual(
            first.definition_opening.sentence,
            "Enflasyon, fiyatlar genel düzeyinin sürekli artışıdır.",
        )
        self.assertFalse(second.opens_with_definition)
        self.assertEqual(
            [profile.ordinal_position for profile in analysis.definition_opening_profiles],
            [0],
        )

    def test_a_definition_after_the_first_sentence_is_not_an_opening(self):
        """The signal asked for is a passage that *begins* by defining."""
        analysis = self.analyze_page(
            "<p>Kurul dün toplandı. Enflasyon, fiyat artışıdır.</p>"
        )

        self.assertFalse(analysis.passage_profiles[0].opens_with_definition)

    # -- anchor and context signals ----------------------------------------

    def test_separates_a_self_naming_sentence_from_one_that_points_outside_it(self):
        analysis = self.analyze_page(
            "<p>Türkiye'nin ihracatı 2026 yılında %12 arttı. "
            "Bu oran geçen yıla göre iki puan yüksek.</p>"
        )

        profile = analysis.passage_profiles[0]
        self.assertEqual(profile.sentence_count, 2)
        self.assertEqual(
            [sentence.text for sentence in profile.anchor_candidate_sentences],
            ["Türkiye'nin ihracatı 2026 yılında %12 arttı."],
        )
        dependent = profile.context_dependent_sentences
        self.assertEqual(len(dependent), 1)
        self.assertEqual(dependent[0].context_markers, ("bu",))

    def test_every_sentence_carries_its_position_and_its_source_text(self):
        analysis = self.analyze_page("<p>Birinci cümle. İkinci cümle.</p>")

        profile = analysis.passage_profiles[0]
        self.assertEqual(
            [(sentence.ordinal, sentence.text) for sentence in profile.sentences],
            [(0, "Birinci cümle."), (1, "İkinci cümle.")],
        )
        self.assertEqual(profile.text, "Birinci cümle. İkinci cümle.")

    def test_sentence_rules_follow_the_passage_language(self):
        analysis = self.analyze_page(
            "<p>Exports rose by 12 percent in 2026. This figure is a record.</p>",
            language="en-GB",
            source_url="https://example.org/en",
        )

        profile = analysis.passage_profiles[0]
        self.assertEqual(len(profile.anchor_candidate_sentences), 1)
        self.assertEqual(
            profile.context_dependent_sentences[0].context_markers, ("this",)
        )

    # -- reuse and contracts -----------------------------------------------

    def test_word_counts_agree_with_the_passage_quality_analysis(self):
        registered = self.ingest.execute(
            RawHtmlArticle(
                html=_page("<h2>Bölüm</h2><p>Bir iki üç dört.</p><p>Beş altı.</p>"),
                source_url="https://example.org/reuse",
                publisher="TRT",
                article_type="news_report",
                observed_at=NOW,
            )
        )
        version_id = registered.article_version.article_version_id

        quality = AnalyzePassageQuality(self.repository).execute(
            registered.article, version_id
        )
        readiness = self.analyze.execute(registered.article, version_id)

        self.assertEqual(
            [profile.word_count for profile in quality.passage_profiles],
            [profile.word_count for profile in readiness.passage_profiles],
        )

    def test_rejects_a_version_belonging_to_another_article(self):
        first = self.ingest.execute(
            RawHtmlArticle(
                html=_page("<p>Birinci makale paragrafı.</p>"),
                source_url="https://example.org/first",
                publisher="TRT",
                article_type="news_report",
                observed_at=NOW,
            )
        )
        second = self.ingest.execute(
            RawHtmlArticle(
                html=_page("<p>İkinci makale paragrafı.</p>"),
                source_url="https://example.org/second",
                publisher="TRT",
                article_type="news_report",
                observed_at=NOW,
            )
        )

        with self.assertRaises(DomainValidationError):
            self.analyze.execute(
                first.article, second.article_version.article_version_id
            )

    def test_analysis_is_deterministic_and_immutable(self):
        registered = self.ingest.execute(
            RawHtmlArticle(
                html=_page("<h2>Bölüm</h2><p>Bir cümle. Bu ikinci cümle.</p>"),
                source_url="https://example.org/stable",
                publisher="TRT",
                article_type="news_report",
                observed_at=NOW,
            )
        )
        version_id = registered.article_version.article_version_id

        first = self.analyze.execute(registered.article, version_id)
        second = self.analyze.execute(registered.article, version_id)

        self.assertEqual(first, second)
        with self.assertRaises(FrozenInstanceError):
            first.sections[0].ordinal = 5
        with self.assertRaises(FrozenInstanceError):
            first.passage_profiles[0].word_count = 99

    def test_a_snapshot_without_heading_positions_still_analyses(self):
        """Headings declared with no position all sit at the article's start.

        Callers that predate ``body_position`` supply no positions, so every
        heading reports zero. The sections that produces are reported as they
        are rather than guessed at: the earlier headings hold nothing.
        """
        registered = RegisterSourceSnapshot(self.repository).execute(
            SourceArticleSnapshot(
                publisher="TRT",
                canonical_source="https://example.org/legacy",
                original_language="tr",
                article_type="news_report",
                title="Eski kayıt",
                body="Birinci paragraf.\n\nİkinci paragraf.",
                observed_at=NOW,
                source_published_at=NOW,
                declared_headings=(
                    DeclaredHeading(level=1, text="Başlık"),
                    DeclaredHeading(level=2, text="Alt başlık"),
                ),
            )
        )

        analysis = self.analyze.execute(
            registered.article, registered.article_version.article_version_id
        )

        self.assertEqual(analysis.section_count, 2)
        self.assertEqual(analysis.sections[0].passage_ordinals, ())
        self.assertEqual(analysis.sections[1].passage_ordinals, (0, 1))


if __name__ == "__main__":
    unittest.main()
