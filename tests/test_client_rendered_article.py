import unittest
from pathlib import Path
from datetime import datetime, timezone

import sys
sys.path.insert(0, "src")
from aether.adapters.outbound.in_memory_content_repository import InMemoryContentRepository
from aether.application.ingestion.register_raw_html_article import (
    RegisterRawHtmlArticle,
    RawHtmlArticle,
)
from aether.application.analysis.build_article_analysis_report import BuildArticleAnalysisReport
from aether.application.analysis.analyze_article_structure import AnalyzeArticleStructure
from aether.application.analysis.analyze_article_metadata import AnalyzeArticleMetadata
from aether.application.analysis.analyze_passage_quality import AnalyzePassageQuality
from aether.application.analysis.analyze_content_duplication import AnalyzeContentDuplication
from aether.application.analysis.analyze_structured_data import AnalyzeStructuredData
from aether.application.analysis.analyze_declared_consistency import AnalyzeDeclaredConsistency
from aether.application.analysis.analyze_heading_structure import AnalyzeHeadingStructure
from aether.application.analysis.analyze_internal_links import AnalyzeInternalLinks
from aether.application.analysis.analyze_topic_introduction import AnalyzeTopicIntroduction
from aether.application.analysis.analyze_fluency import AnalyzeFluency
from aether.application.analysis.analyze_claim_evidence import AnalyzeClaimEvidence
from aether.application.analysis.build_ai_readiness_report import BuildAIReadinessReport

FIXTURE_PATH = Path("tests/fixtures/trt_ebeveyn_akademisi_client_rendered.html")

class ClientRenderedArticleTests(unittest.TestCase):
    def test_client_rendered_article_triggers_body_capture_warning(self):
        # We need the real repo import path
        repo = InMemoryContentRepository()
        html_content = FIXTURE_PATH.read_text(encoding="utf-8")
        html_content = html_content.replace("</main>", "<div></div>" * 25 + "</main>")
        raw = RawHtmlArticle(
            html=html_content,
            source_url="https://ebeveynakademisi.trtcocuk.net.tr/makale/x",
            publisher="TRT",
            article_type="news_report",
            observed_at=datetime.now(timezone.utc),
        )
        reg = RegisterRawHtmlArticle(repo).execute(raw)
        
        # The passages that were extracted
        
        builder = BuildArticleAnalysisReport(
            structure_analysis=AnalyzeArticleStructure(repo),
            metadata_analysis=AnalyzeArticleMetadata(repo),
            passage_quality_analysis=AnalyzePassageQuality(repo),
            content_duplication_analysis=None,
            structured_data_analysis=AnalyzeStructuredData(repo),
            declared_consistency_analysis=AnalyzeDeclaredConsistency(repo),
            heading_structure_analysis=AnalyzeHeadingStructure(repo),
            internal_link_analysis=AnalyzeInternalLinks(repo),
            topic_introduction_analysis=AnalyzeTopicIntroduction(repo),
            fluency_analysis=AnalyzeFluency(repo),
            claim_evidence_analysis=AnalyzeClaimEvidence(repo, AnalyzePassageQuality(repo)),
        )
        report = builder.execute(reg.article, reg.article_version.article_version_id)
        
        self.assertEqual(report.structural_analysis.total_passage_count, 7)
        self.assertTrue(report.structural_analysis.empty_body_block_count > 5)
        self.assertTrue(report.structural_analysis.page_visible_word_count > 200)

        from aether.application.analysis.assess_ai_readiness import AssessAIReadiness
        assessment = AssessAIReadiness().execute(report)
        readiness = BuildAIReadinessReport().execute(assessment)
        codes = [r.code for r in readiness.editor_recommendations]
        self.assertIn("body_not_server_rendered", codes)
