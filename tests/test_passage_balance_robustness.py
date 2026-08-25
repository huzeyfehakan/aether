"""Diagnostic characterization of Passage Balance sensitivity.

These tests intentionally preserve the current formula and scoring behavior.
They do not define an editorially correct balance; they measure how HTML
paragraph boundaries and non-article paragraphs affect the existing result.
"""

import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean, median, pstdev

sys.path.insert(0, "src")

from aether.application.analysis.analyze_passage_quality import (  # noqa: E402
    AnalyzePassageQuality,
)
from aether.presentation.web.app import AIReadinessPipeline  # noqa: E402


TRT_FIXTURE = (
    Path(__file__).parent / "fixtures" / "trt_ebeveyn_akademisi_makale.html"
)


@dataclass(frozen=True)
class BenchmarkResult:
    passage_texts: tuple
    word_counts: tuple
    passage_balance_ratio: float
    semantic_completeness: float
    geo_score: int


@dataclass(frozen=True)
class CandidateMetrics:
    current_balance: float
    oversized_fitness_128: float
    oversized_fitness_256: float
    oversized_fitness_512: float
    robust_outlier_fitness: float
    iqr_outlier_fitness: float
    cv_dispersion: float
    size_window_fitness: float
    hybrid_fitness: float


def _current_balance(word_counts: tuple[int, ...]) -> float:
    return fmean(word_counts) / max(word_counts) if word_counts else 1.0


def _oversized_fitness(word_counts: tuple[int, ...], upper_bound: int) -> float:
    if not word_counts:
        return 1.0
    return 1.0 - sum(count > upper_bound for count in word_counts) / len(word_counts)


def _robust_outlier_fitness(word_counts: tuple[int, ...]) -> float:
    """Median-relative bounded deviation, averaged and converted to fitness."""
    if not word_counts:
        return 1.0
    center = median(word_counts)
    deviations = (
        abs(count - center) / max(count, center)
        for count in word_counts
        if max(count, center) > 0
    )
    values = tuple(deviations)
    return 1.0 - fmean(values) if values else 1.0


def _quartiles(word_counts: tuple[int, ...]) -> tuple[float, float] | None:
    """Tukey hinges; fewer than four passages are explicitly unsupported."""
    if len(word_counts) < 4:
        return None
    ordered = sorted(word_counts)
    midpoint = len(ordered) // 2
    lower = ordered[:midpoint]
    upper = ordered[-midpoint:]
    return median(lower), median(upper)


def _iqr_outlier_fitness(word_counts: tuple[int, ...]) -> float:
    quartiles = _quartiles(word_counts)
    if quartiles is None:
        return 1.0
    q1, q3 = quartiles
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    outliers = sum(
        count < lower_fence or count > upper_fence for count in word_counts
    )
    return 1.0 - outliers / len(word_counts)


def _cv_dispersion(word_counts: tuple[int, ...]) -> float:
    if not word_counts:
        return 0.0
    average = fmean(word_counts)
    return pstdev(word_counts) / average if average else 0.0


def _size_window_fitness(
    word_counts: tuple[int, ...], lower_bound: int = 40, upper_bound: int = 512
) -> float:
    """Experimental word-count proxy for a research-informed token window."""
    if not word_counts:
        return 1.0
    inside = sum(lower_bound <= count <= upper_bound for count in word_counts)
    return inside / len(word_counts)


def _candidate_metrics(word_counts: tuple[int, ...]) -> CandidateMetrics:
    oversized_128 = _oversized_fitness(word_counts, 128)
    oversized_256 = _oversized_fitness(word_counts, 256)
    oversized_512 = _oversized_fitness(word_counts, 512)
    robust = _robust_outlier_fitness(word_counts)
    return CandidateMetrics(
        current_balance=_current_balance(word_counts),
        oversized_fitness_128=oversized_128,
        oversized_fitness_256=oversized_256,
        oversized_fitness_512=oversized_512,
        robust_outlier_fitness=robust,
        iqr_outlier_fitness=_iqr_outlier_fitness(word_counts),
        cv_dispersion=_cv_dispersion(word_counts),
        size_window_fitness=_size_window_fitness(word_counts),
        # No fitted weights: the weaker of size-ceiling compliance and robust
        # distribution fitness determines this experimental composite.
        hybrid_fitness=min(oversized_256, robust),
    )


# Every unit carries a numeric marker, keeping statistics coverage measured at
# 100% under every segmentation. A-C contain exactly the same words in exactly
# the same order.
PROSE_UNITS = (
    "aileler 1 düzenli sohbetle çocukların günlük deneyimlerini dikkatle birlikte değerlendirir",
    "uzmanlar 2 güvenli rutinlerin duygusal gelişimi desteklediğini açıkça bugün belirtir",
    "çocuklar 3 oyun sırasında düşüncelerini paylaşarak yeni becerileri güvenle geliştirir",
    "ebeveynler 4 açık sorularla çocukların ihtiyaçlarını sabırla anlamaya özen gösterir",
    "öğretmenler 5 tutarlı geribildirimle öğrenme sürecini her gün dikkatle destekler",
    "dinlenme 6 çocukların öğrendiklerini işlemesine ve odaklanmasına düzenli biçimde yardım eder",
    "hareket 7 bedensel sağlıkla birlikte sosyal katılımı da doğal olarak güçlendirir",
    "işbirliği 8 aile ve okul arasındaki iletişimi uzun vadede belirgin güçlendirir",
)


def _paragraph(text: str) -> str:
    return f"<p>{text}</p>"


def _article_html(paragraphs: tuple) -> str:
    return (
        '<html lang="tr"><head><title>Çocuk gelişimi rehberi</title></head>'
        f"<body><main>{''.join(paragraphs)}</main></body></html>"
    )


NATURAL_HTML = _article_html(
    (
        _paragraph(" ".join(PROSE_UNITS[:2])),
        _paragraph(" ".join(PROSE_UNITS[2:5])),
        _paragraph(" ".join(PROSE_UNITS[5:])),
    )
)
SINGLE_PARAGRAPH_HTML = _article_html((_paragraph(" ".join(PROSE_UNITS)),))
OVER_SEGMENTED_HTML = _article_html(tuple(_paragraph(unit) for unit in PROSE_UNITS))
METADATA_CONTAMINATED_HTML = _article_html(
    (
        _paragraph("3 Ağustos 2026"),
        _paragraph("Yazar 1"),
        *tuple(
            _paragraph(" ".join(group))
            for group in (PROSE_UNITS[:2], PROSE_UNITS[2:5], PROSE_UNITS[5:])
        ),
        _paragraph("Şablon bildirimi sürüm 2"),
    )
)
LONG_OUTLIER_HTML = _article_html(
    (
        _paragraph(" ".join(PROSE_UNITS[:2])),
        _paragraph(" ".join(PROSE_UNITS[2:5])),
        _paragraph(" ".join(PROSE_UNITS[5:] + PROSE_UNITS[:7])),
    )
)


class PassageBalanceRobustnessBenchmarkTests(unittest.TestCase):
    def measure(self, name: str, html: str) -> BenchmarkResult:
        pipeline = AIReadinessPipeline()
        source_url = f"https://benchmark.example/{name}"
        report = pipeline.analyze_report(
            html=html,
            source_url=source_url,
            publisher="Benchmark",
            article_type="analysis_fixture",
        )
        article = pipeline.repository.all_articles()[0]
        passages = pipeline.repository.list_passages_for_version(
            article.current_version_id
        )
        passage_quality = AnalyzePassageQuality(pipeline.repository).execute(
            article,
            article.current_version_id,
        )
        return BenchmarkResult(
            passage_texts=tuple(passage.text for passage in passages),
            word_counts=tuple(
                profile.word_count
                for profile in passage_quality.passage_profiles
            ),
            passage_balance_ratio=passage_quality.passage_balance_ratio,
            semantic_completeness=(
                report.assessment_summary.geo_score.semantic_completeness.dimension_score
            ),
            geo_score=report.assessment_summary.geo_score.total,
        )

    def benchmark_results(self):
        return {
            "natural": self.measure("natural", NATURAL_HTML),
            "single_paragraph": self.measure(
                "single-paragraph", SINGLE_PARAGRAPH_HTML
            ),
            "over_segmented": self.measure("over-segmented", OVER_SEGMENTED_HTML),
            "metadata_contaminated": self.measure(
                "metadata-contaminated", METADATA_CONTAMINATED_HTML
            ),
            "long_outlier": self.measure("long-outlier", LONG_OUTLIER_HTML),
        }

    @staticmethod
    def baseline_deltas(results):
        natural = results["natural"]
        return {
            name: (
                result.passage_balance_ratio - natural.passage_balance_ratio,
                result.semantic_completeness - natural.semantic_completeness,
                result.geo_score - natural.geo_score,
            )
            for name, result in results.items()
        }

    def test_same_prose_changes_scores_when_only_paragraph_boundaries_change(self):
        results = self.benchmark_results()
        natural = results["natural"]
        single = results["single_paragraph"]
        over_segmented = results["over_segmented"]

        canonical_prose = " ".join(natural.passage_texts)
        self.assertEqual(" ".join(single.passage_texts), canonical_prose)
        self.assertEqual(" ".join(over_segmented.passage_texts), canonical_prose)
        self.assertNotEqual(single.passage_balance_ratio, natural.passage_balance_ratio)
        self.assertNotEqual(
            over_segmented.passage_balance_ratio,
            natural.passage_balance_ratio,
        )
        self.assertNotEqual(single.semantic_completeness, natural.semantic_completeness)
        self.assertNotEqual(single.geo_score, natural.geo_score)

    def test_benchmark_captures_counts_and_baseline_deltas_deterministically(self):
        first = self.benchmark_results()
        second = self.benchmark_results()
        self.assertEqual(first, second)

        deltas = self.baseline_deltas(first)
        self.assertEqual(deltas["natural"], (0.0, 0.0, 0))
        self.assertTrue(any(delta != (0.0, 0.0, 0) for delta in deltas.values()))
        self.assertEqual(
            tuple(len(result.word_counts) for result in first.values()),
            (3, 1, 8, 6, 3),
        )

    def test_trt_fixture_characterizes_passage_balance_population(self):
        result = self.measure("trt-ebeveyn", TRT_FIXTURE.read_text(encoding="utf-8"))

        self.assertEqual(
            result.passage_texts,
            (
                "3 Ağustos 2026",
                "Aşırı uyumlu çocuklar çoğu zaman çevre tarafından kolay çocuk olarak tanımlanır.",
                "Bu uyumun ardında çoğu zaman fark edilmeyen bir kaygı yatar.",
                "Prof. Dr. Funda Gümüştaş",
                "Bu içerik bilgilendirme amaçlı hazırlanmıştır.",
            ),
        )

    def test_candidate_metrics_characterize_shared_html_variants(self):
        results = self.benchmark_results()
        metrics = {
            name: _candidate_metrics(result.word_counts)
            for name, result in results.items()
        }

        self.assertEqual(
            metrics["natural"].current_balance,
            results["natural"].passage_balance_ratio,
        )
        self.assertEqual(metrics["single_paragraph"].oversized_fitness_128, 1.0)
        self.assertEqual(metrics["over_segmented"].oversized_fitness_128, 1.0)
        self.assertNotEqual(
            metrics["over_segmented"].robust_outlier_fitness,
            metrics["natural"].robust_outlier_fitness,
        )

    def test_candidate_metrics_characterize_synthetic_length_distributions(self):
        variants = {
            "uniform_normal": (100, 100, 100, 100),
            "uniform_huge": (500, 500, 500, 500),
            "uniform_tiny": (10, 10, 10, 10),
            "mostly_normal_one_huge": (100, 100, 100, 500),
            "mostly_normal_one_tiny": (10, 100, 100, 100, 100),
            "mixed_realistic": (40, 90, 120, 70),
            "single_passage": (200,),
            "very_few_passages": (100, 300),
        }
        metrics = {
            name: _candidate_metrics(word_counts)
            for name, word_counts in variants.items()
        }

        # Characterize known blind spots rather than asserting a normative
        # score: equality-only balance cannot distinguish huge or tiny chunks.
        self.assertEqual(metrics["uniform_huge"].current_balance, 1.0)
        self.assertEqual(metrics["uniform_tiny"].current_balance, 1.0)
        self.assertEqual(metrics["uniform_huge"].oversized_fitness_256, 0.0)
        self.assertEqual(metrics["uniform_tiny"].size_window_fitness, 0.0)

        # One large outlier is detected without collapsing every candidate to
        # zero; IQR deliberately declines to infer quartiles for n < 4.
        outlier = metrics["mostly_normal_one_huge"]
        self.assertGreater(outlier.robust_outlier_fitness, 0.0)
        self.assertLess(outlier.robust_outlier_fitness, 1.0)
        self.assertEqual(metrics["very_few_passages"].iqr_outlier_fitness, 1.0)

    def test_word_count_only_metric_cannot_solve_segmentation_and_tiny_windows(self):
        results = self.benchmark_results()
        over_segmented = results["over_segmented"].word_counts

        # This is the central trade-off exposed by the benchmark: a fixed
        # lower bound sees legitimate over-segmentation and uniformly tiny
        # chunks as the same length-distribution problem. Semantics are absent.
        self.assertEqual(_size_window_fitness(over_segmented), 0.0)
        self.assertEqual(_size_window_fitness((10,) * len(over_segmented)), 0.0)


if __name__ == "__main__":
    unittest.main()
