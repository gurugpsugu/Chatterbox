"""Minimal console UI for the Chatterbox demo."""

from __future__ import annotations

from typing import Any

from src.retrieval.retriever import answer_question, screen_question

EXAMPLE_QUESTIONS = [
    "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
    "What is the minimum SIP for HDFC Mid Cap Fund Direct Growth?",
    "What is the ELSS lock-in period for HDFC ELSS Tax Saver Fund?",
]


def render_welcome() -> str:
    lines = [
        "Welcome to Chatterbox.",
        "Ask a factual question about HDFC mutual funds.",
        "Example questions:",
        *[f"- {question}" for question in EXAMPLE_QUESTIONS],
    ]
    return "\n".join(lines)


def render_disclaimer() -> str:
    return "Facts-only. No investment advice."


def render_answer_card(result: dict[str, Any]) -> str:
    status = result.get("status", "answered")
    answer = str(result.get("answer", "No answer available."))
    citations = result.get("citations") or []
    citations_text = "; ".join(f"{entry.get('label', 'Source')}: {entry.get('url', '')}" for entry in citations)
    last_updated = result.get("last_updated_from_sources")
    heading = f"Status: {status.upper()}"
    parts = [heading, answer]
    if citations_text:
        parts.append(f"Citations: {citations_text}")
    if last_updated:
        parts.append(f"Last updated from sources: {last_updated}")
    return "\n".join(parts)


def main() -> int:
    print(render_welcome())
    print(render_disclaimer())
    while True:
        try:
            question = input("\nQuestion: ")
        except EOFError:
            print()
            return 0
        if not question.strip():
            continue
        if question.strip().lower() in {"exit", "quit"}:
            return 0
        screening = screen_question(question)
        if not screening["allowed"]:
            print(render_answer_card({
                "status": "rejected",
                "answer": screening["reason"],
                "citations": [{"url": "https://www.sebi.gov.in/", "label": "SEBI investor education"}],
            }))
            continue
        result = answer_question(question)
        print(render_answer_card(result))


if __name__ == "__main__":
    raise SystemExit(main())
