import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as web_app
from src.retrieval.retriever import build_answer, retrieve_chunks
from src.ui.web_page import HOME_PAGE


class WebUiTests(unittest.TestCase):
    def test_home_includes_starter_questions_accessibility_and_disclaimer(self):
        page = web_app.home()

        self.assertEqual(page, HOME_PAGE)
        self.assertEqual(page.count('class="suggestion"'), 3)
        self.assertIn("Facts-only. No investment advice.", page)
        self.assertIn('aria-live="polite"', page)
        self.assertIn("prefers-reduced-motion", page)
        self.assertIn('data-question="What is the ELSS lock-in period for HDFC ELSS Tax Saver Fund?"', page)

    def test_chat_endpoint_delegates_to_answer_logic(self):
        expected = {"status": "answered", "answer": "Verified from sources.", "citations": []}
        request = web_app.ChatRequest(question="What is the expense ratio?")

        with patch.object(web_app, "answer_question", return_value=expected) as answer_question:
            result = web_app.chat(request)

        self.assertEqual(result, expected)
        answer_question.assert_called_once_with("What is the expense ratio?")

    def test_ui_validates_citation_protocol_before_creating_links(self):
        self.assertIn("url.protocol === \"https:\" || url.protocol === \"http:\"", HOME_PAGE)
        self.assertIn('link.rel = "noopener noreferrer"', HOME_PAGE)
        self.assertIn("answer.textContent = data.answer", HOME_PAGE)

    def test_ui_supports_follow_ups_conversation_tabs_and_read_aloud(self):
        self.assertIn('role="tablist"', HOME_PAGE)
        self.assertIn('id="new-conversation"', HOME_PAGE)
        self.assertIn('role="tabpanel"', HOME_PAGE)
        self.assertIn("function followUpQuestions(question)", HOME_PAGE)
        self.assertIn('aria-label", "Suggested follow-up questions"', HOME_PAGE)
        self.assertIn('id="read-aloud-dialog"', HOME_PAGE)
        self.assertIn("SpeechSynthesisUtterance", HOME_PAGE)
        self.assertIn("window.sessionStorage", HOME_PAGE)

    def test_ui_only_renders_explicitly_verified_charts_with_citations(self):
        self.assertIn("chart.verified !== true", HOME_PAGE)
        self.assertIn("!Array.isArray(citations) || !citations.some((item) => safeHttpUrl(item.url))", HOME_PAGE)
        self.assertIn("Number.isFinite(item.value)", HOME_PAGE)
        self.assertIn("appendChart(data.chart, citations, turn)", HOME_PAGE)

    def test_answers_use_a_professional_and_considerate_tone(self):
        unverified = build_answer("What are the scheme details?", evidence=[])
        verified = build_answer(
            "What are the scheme details?",
            evidence=[{"text": "The fund invests in equities.", "url": "https://example.com/fund"}],
        )

        self.assertIn("I’m sorry", unverified["answer"])
        self.assertIn("I found this", verified["answer"])

    def test_retrieval_returns_no_evidence_without_corpus_embeddings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chunks_dir = root / "chunks"
            embeddings_dir = root / "embeddings"
            chunks_dir.mkdir()
            embeddings_dir.mkdir()
            chunk = {
                "chunk_id": "chunk-1",
                "source_id": "source-1",
                "url": "https://example.com/fund",
                "title": "Fund facts",
                "text": "HDFC fund minimum investment is 500 rupees.",
            }
            (chunks_dir / "source-1.json").write_text(
                json.dumps({"source_id": "source-1", "chunks": [chunk]}),
                encoding="utf-8",
            )

            results = retrieve_chunks(
                "What is the fund's lock-in period?",
                chunks_dir=chunks_dir,
                embeddings_dir=embeddings_dir,
            )

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
