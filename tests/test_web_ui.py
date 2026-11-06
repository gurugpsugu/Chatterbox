import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as web_app
from src.loading.scrape_sources import PageTextExtractor
from src.retrieval.retriever import (
    _extract_historical_sip_performance,
    _live_source_evidence,
    _select_registry_sources,
    build_answer,
    get_fund_historical_performance,
    retrieve_chunks,
)
from src.ui.web_page import HOME_PAGE


class WebUiTests(unittest.TestCase):
    def test_home_includes_general_fund_filters_accessibility_and_disclaimer(self):
        page = web_app.home()

        self.assertEqual(page, HOME_PAGE)
        self.assertIn("Clear answers across mutual funds.", page)
        self.assertIn('id="category-filter"', page)
        self.assertIn('id="amc-filter"', page)
        self.assertIn('id="fund-cards"', page)
        self.assertIn("Facts-only. No investment advice.", page)
        self.assertIn('aria-live="polite"', page)
        self.assertIn("prefers-reduced-motion", page)
        self.assertIn('fetch("/api/funds")', page)

    def test_chat_endpoint_delegates_to_answer_logic(self):
        expected = {"status": "answered", "answer": "Verified from sources.", "citations": []}
        request = web_app.ChatRequest(question="What is the expense ratio?")

        with patch.object(web_app, "answer_question", return_value=expected) as answer_question:
            result = web_app.chat(request)

        self.assertEqual(result, expected)
        answer_question.assert_called_once_with("What is the expense ratio?")

    def test_chat_endpoint_passes_conversation_context_when_available(self):
        request = web_app.ChatRequest(
            question="What is the minimum SIP?",
            context="What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
        )

        with patch.object(web_app, "answer_question", return_value={"status": "answered"}) as answer_question:
            web_app.chat(request)

        answer_question.assert_called_once_with(
            "What is the minimum SIP?",
            context="What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
        )

    def test_fund_catalog_endpoint_exposes_categories_amcs_and_validated_sources(self):
        catalog = web_app.fund_catalog()

        self.assertEqual(len(catalog["funds"]), 12)
        self.assertEqual(len(catalog["categories"]), 8)
        self.assertEqual(len(catalog["amcs"]), 6)
        self.assertEqual(
            catalog["source_policy"],
            "official_first_with_labeled_third_party_fallback",
        )
        sbi_small = next(fund for fund in catalog["funds"] if fund["fund_id"] == "sbi-small-cap")
        self.assertIn("sbimf.com", sbi_small["official_url"])
        self.assertIn("groww.in", sbi_small["fallback_url"])

    def test_live_source_uses_official_source_then_falls_back_when_fact_is_missing(self):
        question = "What is the expense ratio of SBI Small Cap Fund Direct Growth?"
        selected = _select_registry_sources(question)

        self.assertEqual(
            [source["source_type"] for source in selected],
            ["official_amc", "third_party_fallback"],
        )
        with patch(
            "src.retrieval.retriever._fetch_source_text",
            side_effect=["Scheme details unavailable", "Expense ratio\n0.7%"],
        ) as fetch:
            evidence = _live_source_evidence(question)

        self.assertEqual(evidence[0]["source_id"], "sbi-small-cap-groww")
        self.assertEqual(evidence[0]["publisher"], "Groww")
        fetch.assert_any_call(selected[0]["url"])
        fetch.assert_any_call(selected[1]["url"])

    def test_indexed_retrieval_prioritizes_official_source_over_better_matching_fallback(self):
        question = "What is the expense ratio of SBI Small Cap Fund Direct Growth?"
        chunks = [{
            "chunks": [
                {
                    "chunk_id": "official-chunk",
                    "source_id": "sbi-small-cap-official",
                    "title": "SBI Small Cap Fund Direct Growth",
                    "url": "https://www.sbimf.com/sbimf-scheme-details/sbi-small-cap-fund-329",
                    "text": "Official scheme information.",
                },
                {
                    "chunk_id": "fallback-chunk",
                    "source_id": "sbi-small-cap-groww",
                    "title": "SBI Small Cap Fund Direct Growth",
                    "url": "https://groww.in/mutual-funds/sbi-small-midcap-fund-direct-growth",
                    "text": "Third-party scheme information.",
                },
            ],
        }]

        with patch("src.retrieval.retriever._load_embedding_index", return_value={
            "official-chunk": [1],
            "fallback-chunk": [2],
        }), patch("src.retrieval.retriever._iter_chunk_artifacts", return_value=chunks), patch(
            "src.retrieval.retriever.embed_query", return_value=[0],
        ), patch(
            "src.retrieval.retriever._cosine_similarity",
            side_effect=lambda _query, vector: 0.2 if vector == [1] else 0.9,
        ):
            evidence = retrieve_chunks(question)

        self.assertEqual([item["source_id"] for item in evidence], ["sbi-small-cap-official"])
        self.assertEqual(evidence[0]["publisher"], "SBI Mutual Fund")
        self.assertEqual(evidence[0]["source_type"], "official_amc")

    def test_ui_validates_citation_protocol_before_creating_links(self):
        self.assertIn("url.protocol === \"https:\" || url.protocol === \"http:\"", HOME_PAGE)
        self.assertIn('link.rel = "noopener noreferrer"', HOME_PAGE)
        self.assertIn("answer.textContent = data.answer", HOME_PAGE)

    def test_ui_supports_follow_ups_conversation_tabs_and_read_aloud(self):
        self.assertIn('role="tablist"', HOME_PAGE)
        self.assertIn('id="new-conversation"', HOME_PAGE)
        self.assertIn('role="tabpanel"', HOME_PAGE)
        self.assertIn('aria-label", "Suggested follow-up questions"', HOME_PAGE)
        self.assertIn("More facts from this scheme", HOME_PAGE)
        self.assertIn('id="read-aloud-dialog"', HOME_PAGE)
        self.assertIn("SpeechSynthesisUtterance", HOME_PAGE)
        self.assertIn("window.sessionStorage", HOME_PAGE)
        self.assertIn("body: JSON.stringify({ question, context })", HOME_PAGE)

    def test_suggestion_to_chat_transition_respects_reduced_motion(self):
        self.assertIn("document.startViewTransition(beginSubmission)", HOME_PAGE)
        self.assertIn("view-transition-name: conversation-panel", HOME_PAGE)
        self.assertIn("@keyframes panel-pan-in", HOME_PAGE)
        self.assertIn("@keyframes panel-pan-out", HOME_PAGE)
        self.assertIn("@keyframes chat-arrive", HOME_PAGE)
        self.assertIn('prefers-reduced-motion: reduce', HOME_PAGE)
        self.assertIn("chatShell.classList.toggle(\"is-active\", hasTurns)", HOME_PAGE)

    def test_fund_performance_endpoint_returns_source_backed_history(self):
        response = {
            "status": "available",
            "fund_id": "hdfc-large-cap",
            "periods": [],
            "citation": {"url": "https://groww.in/example"},
        }
        with patch.object(web_app, "get_fund_historical_performance", return_value=response):
            self.assertEqual(web_app.fund_performance("hdfc-large-cap"), response)

        with patch.object(
            web_app,
            "get_fund_historical_performance",
            side_effect=KeyError("unknown"),
        ), self.assertRaises(web_app.HTTPException) as error:
            web_app.fund_performance("not-a-fund")
        self.assertEqual(error.exception.status_code, 404)

    def test_historical_sip_parser_keeps_publisher_values_and_periods(self):
        extractor = PageTextExtractor()
        extractor.feed(
            "<main><p>NAV: 05 Nov '26</p><p>Monthly investment</p><p>₹5,000</p>"
            "<table><tr><th>Over the past</th><th>Total investment</th>"
            "<th>Would've become</th><th>Historic returns</th><th>Returns</th></tr>"
            "<tr><td>1 year</td><td>₹60,000</td><td>₹59,766</td><td>-0.39%</td></tr>"
            "<tr><td>3 years</td><td>₹1,80,000</td><td>₹1,83,780</td><td>+2.10%</td></tr>"
            "</table></main>"
        )

        result = _extract_historical_sip_performance(extractor.get_text().splitlines())

        self.assertEqual(result["monthly_investment"], 5000)
        self.assertEqual(result["as_of"], "05 Nov '26")
        self.assertEqual(result["periods"][0], {
            "period": "1 year",
            "months": 12,
            "total_investment": 60000,
            "would_become": 59766,
            "return_percent": -0.39,
            "display_return": "-0.39%",
        })
        self.assertEqual(result["periods"][1]["months"], 36)
        self.assertEqual(result["periods"][1]["display_return"], "+2.10%")

    def test_historical_performance_prefers_parsable_official_then_fallback(self):
        historical_page = (
            "Monthly investment\n₹5,000\nOver the past\nTotal investment\n"
            "Would've become\nHistoric returns\nReturns\n1 year\n₹60,000\n"
            "₹62,000\n+3.33%"
        )
        with patch(
            "src.retrieval.retriever._fetch_source_text",
            side_effect=["Scheme details only", historical_page],
        ):
            result = get_fund_historical_performance("sbi-small-cap")

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["citation"]["publisher"], "Groww")
        self.assertEqual(result["periods"][0]["return_percent"], 3.33)

    def test_historical_performance_reports_unavailable_without_inventing_rows(self):
        with patch(
            "src.retrieval.retriever._fetch_source_text",
            return_value="Scheme facts with no historical SIP table",
        ):
            result = get_fund_historical_performance("hdfc-large-cap")

        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("periods", result)

    def test_selected_fund_uses_source_backed_history_calculator(self):
        self.assertIn('id="return-calculator"', HOME_PAGE)
        self.assertIn('id="calculator-monthly"', HOME_PAGE)
        self.assertIn('id="calculator-period"', HOME_PAGE)
        self.assertIn('id="historical-chart"', HOME_PAGE)
        self.assertIn('fetch(`/api/funds/${encodeURIComponent(fundId)}/performance`)', HOME_PAGE)
        self.assertIn("published historical SIP illustration", HOME_PAGE)
        self.assertNotIn('id="calculator-rate"', HOME_PAGE)
        self.assertNotIn("annualRate", HOME_PAGE)
        self.assertIn("conversation.fundId = suggestionButton.dataset.fundId", HOME_PAGE)
        self.assertIn('calculatorMonthly.addEventListener("input", renderReturnCalculator)', HOME_PAGE)
        self.assertNotIn("fund.return", HOME_PAGE)

    def test_metric_visuals_are_animated_and_colors_do_not_signal_suitability(self):
        self.assertIn("animateMetricValue(value, metric, response)", HOME_PAGE)
        self.assertIn("if (animatedMetricResponses.has(response))", HOME_PAGE)
        self.assertIn("element.textContent = metric.display_value", HOME_PAGE)
        self.assertIn("requestAnimationFrame(() => { bar.style.width = targetWidth; })", HOME_PAGE)
        self.assertIn("Official AMC source", HOME_PAGE)
        self.assertIn("Third-party source", HOME_PAGE)
        self.assertIn("not a risk, performance, or suitability signal", HOME_PAGE)
        self.assertNotIn("favorable enough to invest", HOME_PAGE)

    def test_each_answer_has_non_advice_notice_and_visible_citations(self):
        self.assertIn("Not an investment recommendation", HOME_PAGE)
        self.assertIn("This response only reflects information available from the cited sources.", HOME_PAGE)
        self.assertIn("details.open = citations.length > 0", HOME_PAGE)
        self.assertIn('link.rel = "noopener noreferrer"', HOME_PAGE)

    def test_ui_only_renders_explicitly_verified_charts_with_citations(self):
        self.assertIn("chart.verified !== true", HOME_PAGE)
        self.assertIn("!Array.isArray(citations) || !citations.some((item) => safeHttpUrl(item.url))", HOME_PAGE)
        self.assertIn("Number.isFinite(item.value)", HOME_PAGE)
        self.assertIn("chart.data.length < 1", HOME_PAGE)
        self.assertIn("appendMetricCard(data.metric, citations, visuals, data)", HOME_PAGE)
        self.assertIn("appendChart(data.chart, citations, visuals)", HOME_PAGE)
        self.assertIn("button.textContent = text", HOME_PAGE)

    def test_answers_use_a_professional_and_considerate_tone(self):
        unverified = build_answer("What are the scheme details?", evidence=[])
        verified = build_answer(
            "What are the scheme details?",
            evidence=[{"text": "The fund invests in equities.", "url": "https://example.com/fund"}],
        )

        self.assertIn("I’m sorry", unverified["answer"])
        self.assertIn("I found this", verified["answer"])

    def test_numeric_answer_is_prominent_and_follow_ups_are_source_available_facts(self):
        evidence = [{
            "title": "HDFC Large Cap Fund Direct Growth",
            "url": "https://example.com/hdfc-large-cap",
            "retrieved_at": "2026-11-06T00:00:00+00:00",
            "text": (
                "HDFC Large Cap Fund Direct Growth\n"
                "Min. for SIP\n₹100\n"
                "Fund size (AUM)\n₹37,293.95 Cr\n"
                "Expense ratio\n1.01%"
            ),
        }]

        result = build_answer(
            "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
            evidence=evidence,
        )

        self.assertEqual(result["metric"]["display_value"], "1.01%")
        self.assertTrue(result["chart"]["verified"])
        self.assertEqual(result["chart"]["data"], [{
            "label": "Expense ratio",
            "value": 1.01,
            "display_value": "1.01%",
        }])
        self.assertEqual(result["chart"]["unit"], "%")
        self.assertTrue(any("minimum SIP" in question for question in result["follow_ups"]))
        self.assertTrue(any("fund size (AUM)" in question for question in result["follow_ups"]))
        self.assertFalse(any("What does SIP mean" in question for question in result["follow_ups"]))

        aum_result = build_answer(
            "What is the fund size (AUM) of HDFC Large Cap Fund Direct Growth?",
            evidence=evidence,
        )
        self.assertEqual(aum_result["metric"]["display_value"], "₹37,293.95 Cr")

        sip_result = build_answer(
            "What is the minimum SIP for HDFC Large Cap Fund Direct Growth?",
            evidence=evidence,
        )
        self.assertEqual(sip_result["metric"]["display_value"], "₹100")

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
                live_source_fallback=False,
            )

        self.assertEqual(results, [])

    def test_live_source_fallback_finds_and_cites_a_relevant_passage(self):
        source_text = (
            "HDFC Large Cap Fund Direct Growth\n"
            "Min. for SIP\n₹100\nFund size (AUM)\n₹37,293.95 Cr\n"
            "Expense ratio\n1.01%\nRating\n4"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chunks_dir = root / "chunks"
            embeddings_dir = root / "embeddings"
            chunks_dir.mkdir()
            embeddings_dir.mkdir()

            with patch(
                "src.retrieval.retriever._fetch_source_text",
                return_value=source_text,
            ) as fetch_source:
                results = retrieve_chunks(
                    "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
                    chunks_dir=chunks_dir,
                    embeddings_dir=embeddings_dir,
                    live_source_fallback=True,
                )

        self.assertEqual(len(results), 1)
        self.assertIn("Expense ratio 1.01%", results[0]["text"])
        self.assertEqual(
            results[0]["url"],
            "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        )
        fetch_source.assert_called_once_with(
            "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
        )

    def test_follow_up_without_scheme_name_uses_the_previous_question_context(self):
        source_text = (
            "HDFC Large Cap Fund Direct Growth\n"
            "Min. for SIP\n₹100\n"
            "Fund size (AUM)\n₹37,293.95 Cr\n"
            "Expense ratio\n1.01%"
        )
        with patch(
            "src.retrieval.retriever._fetch_source_text",
            return_value=source_text,
        ) as fetch_source:
            result = web_app.chat(web_app.ChatRequest(
                question="What is the minimum SIP?",
                context="What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
            ))

        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["metric"]["display_value"], "₹100")
        self.assertEqual(result["citations"][0]["label"], "HDFC Large Cap Fund Direct Growth")
        fetch_source.assert_called_once_with(
            "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
        )


if __name__ == "__main__":
    unittest.main()
