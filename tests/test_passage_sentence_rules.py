import sys
import unittest

sys.path.insert(0, "src")

from aether.application.analysis.passage_sentence_rules import (  # noqa: E402
    context_markers_in,
    definition_opening,
    primary_language_subtag,
    split_sentences,
)


class SentenceSplittingTests(unittest.TestCase):
    def test_splits_on_terminal_punctuation_followed_by_space(self):
        self.assertEqual(
            split_sentences("Bir cümle. İkinci cümle! Üçüncü mü?"),
            ("Bir cümle.", "İkinci cümle!", "Üçüncü mü?"),
        )

    def test_keeps_dotted_numbers_and_dates_inside_one_sentence(self):
        """A period between digits carries no whitespace, so it never splits."""
        self.assertEqual(
            split_sentences("Oran 12.05.2026 tarihinde %3.7 olarak ölçüldü."),
            ("Oran 12.05.2026 tarihinde %3.7 olarak ölçüldü.",),
        )

    def test_normalizes_whitespace_before_splitting(self):
        self.assertEqual(
            split_sentences("  İlk   cümle.\n\n  İkinci cümle.  "),
            ("İlk cümle.", "İkinci cümle."),
        )

    def test_empty_text_yields_no_sentences(self):
        self.assertEqual(split_sentences("   "), ())

    def test_text_without_terminal_punctuation_is_one_sentence(self):
        self.assertEqual(split_sentences("Başlık gibi bir satır"), ("Başlık gibi bir satır",))


class LanguageSubtagTests(unittest.TestCase):
    def test_reduces_a_tag_to_its_primary_subtag(self):
        for tag in ("tr", "tr-TR", "TR_tr", "  tr-Latn-TR  "):
            self.assertEqual(primary_language_subtag(tag), "tr")

    def test_unknown_tag_resolves_to_itself_and_matches_no_rule(self):
        self.assertEqual(primary_language_subtag("de-DE"), "de")
        self.assertEqual(context_markers_in("Dies ist ein Satz.", "de-DE"), ())
        self.assertIsNone(definition_opening("Was ist Inflation?", "de-DE"))


class ContextMarkerTests(unittest.TestCase):
    def test_reports_the_marker_that_opens_a_dependent_sentence(self):
        self.assertEqual(
            context_markers_in("Bu oran geçen yıla göre %12 arttı.", "tr"),
            ("bu",),
        )

    def test_reports_nothing_for_a_sentence_that_names_its_own_subject(self):
        self.assertEqual(
            context_markers_in("Türkiye'nin ihracatı 2026 yılında %12 arttı.", "tr"),
            (),
        )

    def test_prefers_the_longest_marker_over_its_own_prefix(self):
        self.assertEqual(
            context_markers_in("Bu nedenle üretim durduruldu.", "tr"),
            ("bu nedenle",),
        )

    def test_a_marker_is_matched_as_a_whole_word_only(self):
        """``Bursa`` opens with the letters of ``bu`` and is not a marker."""
        self.assertEqual(context_markers_in("Bursa'da üretim arttı.", "tr"), ())
        self.assertEqual(context_markers_in("Bunalım derinleşti.", "tr"), ())

    def test_a_marker_inside_a_sentence_is_not_reported(self):
        """A pronoun mid-sentence usually refers to a subject that sentence set."""
        self.assertEqual(
            context_markers_in("Kurul raporu inceledi ve bu sonuca vardı.", "tr"),
            (),
        )

    def test_leading_quotation_marks_do_not_hide_a_marker(self):
        self.assertEqual(
            context_markers_in("\u201cBu karar bağlayıcıdır\u201d dedi.", "tr"),
            ("bu",),
        )

    def test_english_markers_are_matched_in_english_passages(self):
        self.assertEqual(
            context_markers_in("This figure rose by 12 percent.", "en-GB"),
            ("this",),
        )
        self.assertEqual(
            context_markers_in("Exports rose by 12 percent in 2026.", "en-GB"),
            (),
        )


class DefinitionOpeningTests(unittest.TestCase):
    def test_detects_a_question_form_definition(self):
        opening = definition_opening("Enflasyon nedir?", "tr")
        self.assertIsNotNone(opening)
        self.assertEqual(opening.construction, "question_form")
        self.assertEqual(opening.sentence, "Enflasyon nedir?")

    def test_detects_a_copular_predicate_definition(self):
        opening = definition_opening(
            "Enflasyon, fiyatlar genel düzeyinin sürekli artışıdır.", "tr"
        )
        self.assertIsNotNone(opening)
        self.assertEqual(opening.construction, "copular_predicate")

    def test_detects_an_explicit_definition(self):
        opening = definition_opening(
            "Sepet, tüketicinin bir ayda aldığı mallar olarak tanımlanır.", "tr"
        )
        self.assertIsNotNone(opening)
        self.assertEqual(opening.construction, "explicit_definition")

    def test_a_narrative_sentence_is_not_a_definition(self):
        self.assertIsNone(
            definition_opening("Bakan dün Ankara'da bir toplantıya katıldı.", "tr")
        )

    def test_a_copular_sentence_without_a_subject_comma_is_not_a_definition(self):
        """``-dir`` alone ends many Turkish declaratives that define nothing."""
        self.assertIsNone(
            definition_opening("Toplantı salonu bu sabah kapalıdır.", "tr")
        )

    def test_the_reported_construction_is_stable_for_the_same_sentence(self):
        sentence = "Enflasyon nedir? Enflasyon, fiyat artışıdır."
        first = definition_opening(sentence, "tr")
        second = definition_opening(sentence, "tr")
        self.assertEqual(first, second)

    def test_english_definitions_are_detected(self):
        self.assertEqual(
            definition_opening("What is inflation?", "en").construction,
            "question_form",
        )
        self.assertEqual(
            definition_opening(
                "Inflation is defined as a sustained rise in prices.", "en"
            ).construction,
            "explicit_definition",
        )
        self.assertEqual(
            definition_opening("Inflation is a sustained rise in prices.", "en").construction,
            "copular_predicate",
        )


if __name__ == "__main__":
    unittest.main()
