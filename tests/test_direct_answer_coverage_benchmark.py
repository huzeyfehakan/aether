"""Diagnostic characterization of Direct Answer Coverage.

The assertions freeze current deterministic behavior; they do not prescribe a
production accuracy target or alter the temporary Semantic Completeness weight.
"""

import sys
import unittest
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, "src")

from aether.application.analysis.analyze_article_metadata import MetadataAnalysis  # noqa: E402
from aether.application.analysis.analyze_article_structure import ArticleStructuralAnalysis  # noqa: E402
from aether.application.analysis.analyze_passage_quality import PassageProfile, PassageQualityAnalysis  # noqa: E402
from aether.application.analysis.assess_ai_readiness import AssessAIReadiness  # noqa: E402
from aether.application.analysis.build_article_analysis_report import ArticleAnalysisReport  # noqa: E402
from aether.application.ingestion.register_raw_html_article import _ArticleHtmlCollector  # noqa: E402


@dataclass(frozen=True)
class MetricResult:
    question_heading_count: int
    measurable_question_count: int
    answered_question_count: int
    direct_answer_coverage_ratio: Optional[float]
    heading_passage_overlap_ratio: Optional[float]


@dataclass(frozen=True)
class QuestionExample:
    language: str
    question_type: str
    classification: str
    heading: str
    passage: str
    current_result: Optional[float]


@dataclass(frozen=True)
class SensitivityResult:
    other_signal_score: float
    direct_answer_ratio: Optional[float]
    semantic_completeness: float
    geo_contribution: float
    geo_total: int


def _measure(headings_and_passages=(), *, title="Benchmark article") -> MetricResult:
    body = "".join(
        f"<h2>{heading}</h2><p>{passage}</p>"
        for heading, passage in headings_and_passages
    )
    collector = _ArticleHtmlCollector()
    collector.feed(
        f'<html lang="tr"><head><title>{title}</title></head>'
        f"<body><main>{body or '<p>Normal declarative article prose.</p>'}</main></body></html>"
    )
    collector.close()
    collector.calculate_geo_metrics()
    return MetricResult(
        question_heading_count=sum(
            heading.strip().endswith("?") for heading, _ in headings_and_passages
        ),
        measurable_question_count=len(collector.direct_answers),
        answered_question_count=int(sum(collector.direct_answers)),
        direct_answer_coverage_ratio=(
            sum(collector.direct_answers) / len(collector.direct_answers)
            if collector.direct_answers
            else None
        ),
        heading_passage_overlap_ratio=(
            sum(collector.heading_overlaps) / len(collector.heading_overlaps)
            if collector.heading_overlaps
            else None
        ),
    )


STRUCTURE_CASES = {
    "no_question_headings": (("Çocuk gelişimi", "Çocuk gelişimi düzenli desteklenir."),),
    "one_direct_answer": (("Ayılar neden saldırıyor?", "Ayılar açlık nedeniyle saldırabilir."),),
    "one_related_non_answer": (("Ayılar neden saldırıyor?", "Ayılar geniş ormanlarda yaşar."),),
    "several_all_answered": (
        ("Algoritma nedir?", "Algoritma, bir problemi çözen adımlar dizisidir."),
        ("Belgesel nasıl seçilir?", "Belgesel seçilirken önce yaş uygunluğu incelenmelidir."),
    ),
    "several_partly_answered": (
        ("Algoritma nedir?", "Algoritma, bir problemi çözen adımlar dizisidir."),
        ("Belgesel nasıl seçilir?", "Belgeseller birçok ülkede yayımlanır."),
    ),
    "question_title_only": (),
    "declarative_news": (("Yeni araştırmanın sonuçları", "Araştırma bugün yayımlandı."),),
}


QUESTION_EXAMPLES = (
    # Turkish causal forms.
    QuestionExample("tr", "neden", "true_positive", "Ayılar neden saldırıyor?", "Ayılar açlık nedeniyle saldırabilir.", 1.0),
    QuestionExample("tr", "neden", "related_negative", "Ayılar neden saldırıyor?", "Ayılar geniş ormanlarda yaşar.", 0.0),
    QuestionExample("tr", "neden", "cue_trap", "Ayılar neden saldırıyor?", "Ayılar nedeniyle bazı yollarda önlem alınmıştır.", 1.0),
    QuestionExample("tr", "niçin", "true_positive", "Ayılar niçin saldırıyor?", "Ayılar yavrularını koruduğu için değil, açlık nedeniyle saldırabilir.", 1.0),
    QuestionExample("tr", "niçin", "related_negative", "Ayılar niçin saldırıyor?", "Ayılar geniş ormanlarda yaşar.", 0.0),
    QuestionExample("tr", "niçin", "cue_trap", "Ayılar niçin saldırıyor?", "Ayılar nedeniyle bazı yollarda önlem alınmıştır.", 1.0),
    QuestionExample("tr", "niye", "true_positive", "Ayılar niye saldırıyor?", "Ayılar tehdit sonucunda saldırabilir.", 1.0),
    QuestionExample("tr", "niye", "related_negative", "Ayılar niye saldırıyor?", "Ayılar geniş ormanlarda yaşar.", 0.0),
    QuestionExample("tr", "niye", "cue_trap", "Ayılar niye saldırıyor?", "Ayılar nedeniyle bazı yollarda önlem alınmıştır.", 1.0),
    # Turkish definition, method, factors, and yes/no forms.
    QuestionExample("tr", "nedir", "true_positive", "Algoritma nedir?", "Algoritma, bir problemi çözmek için izlenen sonlu adımlar dizisidir.", 1.0),
    QuestionExample("tr", "nedir", "related_negative", "Algoritma nedir?", "Algoritma yarışmaları öğrenciler arasında popülerdir.", 0.0),
    QuestionExample("tr", "nedir", "cue_trap", "Algoritma nedir?", "Algoritma yarışması bir okul etkinliğidir.", 1.0),
    QuestionExample("tr", "nasıl", "true_positive", "Belgesel nasıl seçilir?", "Belgesel seçilirken önce yaş uygunluğu incelenmelidir.", 1.0),
    QuestionExample("tr", "nasıl", "related_negative", "Belgesel nasıl seçilir?", "Belgesel birçok ülkede yayımlanır.", 0.0),
    QuestionExample("tr", "nasıl", "cue_trap", "Belgesel nasıl seçilir?", "Belgesel önce televizyonda gösterildi.", 1.0),
    QuestionExample("tr", "nelere", "true_positive", "Belgesel seçerken nelere dikkat edilmeli?", "Belgesel seçiminde yaş, içerik dili ve süre değerlendirilir.", 1.0),
    QuestionExample("tr", "nelere", "related_negative", "Belgesel seçerken nelere dikkat edilmeli?", "Belgesel seçimi zamanla değişebilir.", 0.0),
    QuestionExample("tr", "nelere", "cue_trap", "Belgesel seçerken nelere dikkat edilmeli?", "Belgesel seçimi Türkiye, Fransa ve İtalya'da tartışıldı.", 1.0),
    QuestionExample("tr", "hangi", "true_positive", "Hangi belgesel ölçütleri önemlidir?", "Belgesel ölçütleri yaş, süre ve kaynak kalitesidir.", 1.0),
    QuestionExample("tr", "hangi", "related_negative", "Hangi belgesel ölçütleri önemlidir?", "Belgesel ölçütleri zamanla değişebilir.", 0.0),
    QuestionExample("tr", "hangi", "cue_trap", "Hangi belgesel ölçütleri önemlidir?", "Belgesel ölçütleri Türkiye, Fransa ve İtalya'da tartışıldı.", 1.0),
    QuestionExample("tr", "nelerdir", "true_positive", "Belgesel ölçütleri nelerdir?", "Belgesel ölçütleri yaş, süre ve kaynak kalitesidir.", 1.0),
    QuestionExample("tr", "nelerdir", "related_negative", "Belgesel ölçütleri nelerdir?", "Belgesel ölçütleri zamanla değişebilir.", 0.0),
    QuestionExample("tr", "nelerdir", "cue_trap", "Belgesel ölçütleri nelerdir?", "Belgesel ölçütleri Türkiye, Fransa ve İtalya'da tartışıldı.", 1.0),
    QuestionExample("tr", "mi_mu", "true_positive", "Bu yöntem güvenli mi?", "Evet, yöntem güvenlidir.", 1.0),
    QuestionExample("tr", "mi_mu", "related_negative", "Bu yöntem güvenli mi?", "Yöntem geçen yıl geliştirildi.", 0.0),
    QuestionExample("tr", "mi_mu", "cue_trap", "Bu yöntem güvenli mi?", "Evet, hava bugün güneşli.", 1.0),
    QuestionExample("tr", "mı", "true_positive", "Bu yaklaşım yararlı mı?", "Evet, yaklaşım yararlıdır.", 1.0),
    QuestionExample("tr", "mı", "related_negative", "Bu yaklaşım yararlı mı?", "Yaklaşım geçen yıl geliştirildi.", 0.0),
    QuestionExample("tr", "mı", "cue_trap", "Bu yaklaşım yararlı mı?", "Evet, hava bugün güneşli.", 1.0),
    QuestionExample("tr", "mu", "true_positive", "Bu sonuç doğru mu?", "Evet, sonuç doğrudur.", 1.0),
    QuestionExample("tr", "mu", "related_negative", "Bu sonuç doğru mu?", "Sonuç dün açıklandı.", 0.0),
    QuestionExample("tr", "mu", "cue_trap", "Bu sonuç doğru mu?", "Evet, hava bugün güneşli.", 1.0),
    QuestionExample("tr", "mü", "true_positive", "Bu çözüm mümkün mü?", "Evet, çözüm mümkündür.", 1.0),
    QuestionExample("tr", "mü", "related_negative", "Bu çözüm mümkün mü?", "Çözüm dün duyuruldu.", 0.0),
    QuestionExample("tr", "mü", "cue_trap", "Bu çözüm mümkün mü?", "Evet, hava bugün güneşli.", 1.0),
    # English bounded forms.
    QuestionExample("en", "why", "true_positive", "Why do bears attack?", "Bears attack because bears perceive a threat.", 1.0),
    QuestionExample("en", "why", "related_negative", "Why do bears attack?", "Bears live in many forests.", 0.0),
    QuestionExample("en", "why", "cue_trap", "Why do bears attack?", "Bears tourism declined because fuel prices rose.", 1.0),
    QuestionExample("en", "what_is_are", "true_positive", "What is an algorithm?", "An algorithm is a finite sequence of instructions.", 1.0),
    QuestionExample("en", "what_is_are", "related_negative", "What is an algorithm?", "Algorithm contests are popular.", 0.0),
    QuestionExample("en", "what_is_are", "cue_trap", "What is an algorithm?", "An algorithm contest is a school event.", 1.0),
    QuestionExample("en", "how", "true_positive", "How is a documentary selected?", "A documentary should first be checked for age suitability.", 1.0),
    QuestionExample("en", "how", "related_negative", "How is a documentary selected?", "A documentary aired yesterday.", 0.0),
    QuestionExample("en", "how", "cue_trap", "How is a documentary selected?", "A documentary first aired yesterday.", 1.0),
    QuestionExample("en", "which", "true_positive", "Which documentary factors matter?", "Documentary factors include age, duration, and source quality.", 1.0),
    QuestionExample("en", "which", "related_negative", "Which documentary factors matter?", "Documentary factors change over time.", 0.0),
    QuestionExample("en", "which", "cue_trap", "Which documentary factors matter?", "Documentary factors involve France, Italy, and Spain.", 1.0),
    QuestionExample("en", "yes_no", "true_positive", "Can this method work?", "Yes, it can work.", 1.0),
    QuestionExample("en", "yes_no", "related_negative", "Can this method work?", "This method was introduced last year.", 0.0),
    QuestionExample("en", "yes_no", "cue_trap", "Can this method work?", "Yes, the weather is clear.", 1.0),
    # ASCII uppercase I is currently mapped to Turkish dotless ı before
    # casefolding, so sentence-initial English "Is" is not classified.
    QuestionExample("en", "yes_no_is", "false_negative", "Is this method safe?", "Yes, it is safe.", None),
)


FALSE_NEGATIVE_CASES = (
    ("Ayılar neden saldırıyor?", "Açlık, yaralanma ve yavrularını koruma davranışı saldırganlığı artırabilir.", 0.0),
    ("Algoritma nedir?", "Algoritma, bir problemi çözmek için izlenen sonlu adımlar dizisidir.", 1.0),
    ("Çocuklar için belgesel nasıl seçilir?", "Yaş uygunluğu, içerik dili ve süre birlikte değerlendirilmelidir.", 0.0),
)


FALSE_POSITIVE_CASES = (
    ("Ayılar neden saldırıyor?", "Ayılar nedeniyle bazı bölgelerde güvenlik önlemleri artırılmıştır.", 1.0),
    ("Algoritma nedir?", "Algoritma yarışmaları öğrenciler arasında oldukça popülerdir.", 0.0),
    ("Belgesel nasıl seçilir?", "Belgeseller birçok ülkede yayınlanmaktadır.", 0.0),
)


def _score_sensitivity(other_score: float, direct_answer: Optional[float]) -> SensitivityResult:
    profiles = tuple(
        PassageProfile(
            passage_id=f"p-{index}",
            ordinal_position=index,
            word_count=10,
            character_count=50,
            contains_statistics=index < round(other_score / 20.0),
            contains_citation=False,
        )
        for index in range(5)
    )
    report = ArticleAnalysisReport(
        structural_analysis=ArticleStructuralAnalysis(
            article_id="benchmark",
            article_version_id="v1",
            total_passage_count=5,
            total_word_count=50,
            table_word_count=0,
            list_word_count=0,
            blockquote_word_count=0,
            answered_question_heading_count=0,
            unanswered_question_heading_count=0,
            heading_passage_overlap_ratio=other_score / 100.0,
            direct_answer_coverage_ratio=direct_answer,
        ),
        metadata_analysis=MetadataAnalysis(
            article_id="benchmark",
            article_version_id="v1",
            title_length=9,
            publication_date_available=False,
            last_modified_date_available=False,
            author_available=False,
            description_available=False,
        ),
        passage_quality_analysis=PassageQualityAnalysis(
            article_id="benchmark",
            article_version_id="v1",
            passage_profiles=profiles,
            passage_balance_ratio=1.0,
            keyword_stuffing_ratio=0.0,
        ),
    )
    geo = AssessAIReadiness().execute(report).geo_score
    return SensitivityResult(
        other_signal_score=other_score,
        direct_answer_ratio=direct_answer,
        semantic_completeness=geo.semantic_completeness.dimension_score,
        geo_contribution=geo.semantic_completeness.weighted_contribution,
        geo_total=geo.total,
    )


class DirectAnswerCoverageBenchmarkTests(unittest.TestCase):
    def test_article_structure_measurability_characterization(self):
        results = {
            name: _measure(
                pairs,
                title="Is the article title a question?" if name == "question_title_only" else name,
            )
            for name, pairs in STRUCTURE_CASES.items()
        }

        self.assertEqual(
            {name: result.direct_answer_coverage_ratio for name, result in results.items()},
            {
                "no_question_headings": None,
                "one_direct_answer": 1.0,
                "one_related_non_answer": 0.0,
                "several_all_answered": 1.0,
                "several_partly_answered": 0.5,
                "question_title_only": None,
                "declarative_news": None,
            },
        )
        self.assertEqual(sum(result.measurable_question_count > 0 for result in results.values()), 4)
        self.assertEqual(len(results), 7)
        self.assertEqual(
            tuple(
                (
                    result.question_heading_count,
                    result.measurable_question_count,
                    result.answered_question_count,
                )
                for result in results.values()
            ),
            ((0, 0, 0), (1, 1, 1), (1, 1, 0), (2, 2, 2), (2, 2, 1), (0, 0, 0), (0, 0, 0)),
        )

    def test_supported_question_types_freeze_true_negative_and_cue_trap_results(self):
        for example in QUESTION_EXAMPLES:
            with self.subTest(language=example.language, type=example.question_type, classification=example.classification):
                result = _measure(((example.heading, example.passage),))
                self.assertEqual(result.direct_answer_coverage_ratio, example.current_result)

    def test_realistic_turkish_false_negative_candidates(self):
        self.assertEqual(
            tuple(_measure(((heading, answer),)).direct_answer_coverage_ratio for heading, answer, _ in FALSE_NEGATIVE_CASES),
            tuple(expected for _, _, expected in FALSE_NEGATIVE_CASES),
        )

    def test_realistic_false_positive_candidates(self):
        self.assertEqual(
            tuple(_measure(((heading, answer),)).direct_answer_coverage_ratio for heading, answer, _ in FALSE_POSITIVE_CASES),
            tuple(expected for _, _, expected in FALSE_POSITIVE_CASES),
        )

    def test_overlap_and_answer_coverage_capture_distinct_cases(self):
        samples = {
            "high_overlap_low_answer": _measure((("Ayılar neden saldırıyor?", "Ayılar saldırıyor ama gözlemler sürüyor."),)),
            "low_overlap_high_answer": _measure((("Bu yöntem güvenli mi?", "Evet."),)),
            "both_high": _measure((("Ayılar neden saldırıyor?", "Ayılar açlık nedeniyle saldırıyor."),)),
            "both_low": _measure((("Ayılar neden saldırıyor?", "Kuşlar göç eder."),)),
        }

        self.assertGreater(samples["high_overlap_low_answer"].heading_passage_overlap_ratio, 0.5)
        self.assertEqual(samples["high_overlap_low_answer"].direct_answer_coverage_ratio, 0.0)
        self.assertEqual(samples["low_overlap_high_answer"].heading_passage_overlap_ratio, 0.0)
        self.assertEqual(samples["low_overlap_high_answer"].direct_answer_coverage_ratio, 1.0)
        self.assertGreater(samples["both_high"].heading_passage_overlap_ratio, 0.0)
        self.assertEqual(samples["both_high"].direct_answer_coverage_ratio, 1.0)
        self.assertEqual(samples["both_low"].heading_passage_overlap_ratio, 0.0)
        self.assertEqual(samples["both_low"].direct_answer_coverage_ratio, 0.0)

    def test_diagnostic_ratio_has_no_score_sensitivity(self):
        ratios = (None, 0.0, 0.25, 0.50, 0.75, 1.0)
        scenario_a = tuple(_score_sensitivity(100.0, ratio) for ratio in ratios)
        scenario_b = tuple(_score_sensitivity(60.0, ratio) for ratio in ratios)

        self.assertEqual(
            tuple(round(result.semantic_completeness, 1) for result in scenario_a),
            (100.0, 100.0, 100.0, 100.0, 100.0, 100.0),
        )
        self.assertEqual(
            tuple(round(result.semantic_completeness, 1) for result in scenario_b),
            (60.0, 60.0, 60.0, 60.0, 60.0, 60.0),
        )
        self.assertEqual(
            tuple(round(result.geo_contribution, 1) for result in scenario_a),
            (40.0, 40.0, 40.0, 40.0, 40.0, 40.0),
        )
        self.assertEqual(
            tuple(round(result.geo_contribution, 1) for result in scenario_b),
            (24.0, 24.0, 24.0, 24.0, 24.0, 24.0),
        )
        self.assertEqual(tuple(result.geo_total for result in scenario_a), (47,) * 6)
        self.assertEqual(tuple(result.geo_total for result in scenario_b), (28,) * 6)


if __name__ == "__main__":
    unittest.main()
