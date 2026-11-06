"""Vercel web entrypoint for the Chatterbox FAQ assistant."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.retrieval.retriever import answer_question
from src.ui.web_page import HOME_PAGE

app = FastAPI(title="Chatterbox", description="Facts-only HDFC mutual fund FAQ assistant")


class ChatRequest(BaseModel):
    question: str
    context: str = ""


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return HOME_PAGE


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    if request.context.strip():
        return answer_question(request.question, context=request.context)
    return answer_question(request.question)
