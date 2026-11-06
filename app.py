"""Vercel web entrypoint for the Chatterbox FAQ assistant."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.retrieval.retriever import answer_question

app = FastAPI(title="Chatterbox", description="Facts-only HDFC mutual fund FAQ assistant")


class ChatRequest(BaseModel):
    question: str


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Chatterbox — Mutual Fund FAQ</title>
    <style>
      body { font: 16px system-ui, sans-serif; max-width: 720px; margin: 3rem auto; padding: 0 1rem; color: #172033; }
      textarea { box-sizing: border-box; width: 100%; min-height: 100px; padding: .8rem; font: inherit; }
      button { margin-top: .75rem; padding: .65rem 1rem; font: inherit; cursor: pointer; }
      #result { white-space: pre-wrap; margin-top: 1.5rem; padding: 1rem; background: #f2f5f9; }
    </style>
  </head>
  <body>
    <h1>Chatterbox</h1>
    <p>Ask a factual question about HDFC mutual funds. Do not share personal or account information.</p>
    <p><strong>Facts-only. No investment advice.</strong></p>
    <form id="chat-form">
      <label for="question">Your question</label>
      <textarea id="question" required></textarea>
      <button type="submit">Ask</button>
    </form>
    <div id="result" role="status" aria-live="polite"></div>
    <script>
      const form = document.getElementById("chat-form");
      const question = document.getElementById("question");
      const result = document.getElementById("result");
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        result.textContent = "Looking up the available source material…";
        try {
          const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: question.value })
          });
          const data = await response.json();
          if (!response.ok) throw new Error(data.detail || "The request failed.");
          const citations = (data.citations || [])
            .map((citation) => `${citation.label}: ${citation.url}`)
            .join("\\n");
          result.textContent = `${data.status.toUpperCase()}\\n${data.answer}` +
            (citations ? `\\n\\nCitations:\\n${citations}` : "");
        } catch (error) {
          result.textContent = error.message || "Unable to answer right now.";
        }
      });
    </script>
  </body>
</html>"""


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    return answer_question(request.question)
