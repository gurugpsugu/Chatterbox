"""Retrieval, question screening, and evidence-backed answer generation."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

from src.embedding.embed_chunks import embed_query, load_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHUNKS_DIR = PROJECT_ROOT / "data" / "chunks"
DEFAULT_EMBEDDINGS_DIR = PROJECT_ROOT / "data" / "embeddings"
DEFAULT_SETTINGS = PROJECT_ROOT / "config" / "settings.json"
FALLBACK_CITATION = "https://www.sebi.gov.in/"


SENSITIVE_PATTERNS = [
    re.compile(r"\b(?:pan|permanent account number)\b[^\n]{0,30}\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE),
    re.compile(r"\b[A-Z]{4}[0-9]{4}[A-Z]\b"),
    re.compile(r"\b[0-9]{12}\b"),
    re.compile(r"\b[0-9]{6}\b"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b(?:\+?91[-\s]?)?(?:\d[ -]?){10}\b"),
    re.compile(r"\b(?:aadhaar|uidai|otp|one time password)\b", re.IGNORECASE),
]

ADVICE_PATTERNS = [
    re.compile(r"\bshould i\b.*\b(buy|sell|invest|switch|redeem)\b", re.IGNORECASE),
    re.compile(r"\bwhich\s+(fund|scheme)\s+should\s+i\b", re.IGNORECASE),
    re.compile(r"\b(?:buy|sell|invest|switch|redeem)\s+(this|that|the)\b", re.IGNORECASE),
    re.compile(r"\bcompare\s+(funds|schemes)\b", re.IGNORECASE),
    re.compile(r"\bperformance\b.*\b(?:compare|rank|return|returns)\b", re.IGNORECASE),
]


def normalize_question(question: str) -> str:
    return " ".join(str(question or "").strip().split())


def screen_question(question: str) -> dict[str, Any]:
    text = normalize_question(question)
    if not text:
        return {"allowed": False, "reason": "Question is empty or missing."}

    lowered = text.lower()
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            return {
                "allowed": False,
                "reason": "Please do not share personal identifiers or account related information.",
            }

    if any(token in lowered for token in ("pan", "aadhaar", "otp", "account number", "phone number", "email")):
        return {
            "allowed": False,
            "reason": "Please keep the question to public facts and avoid personal identifiers.",
        }

    return {"allowed": True, "normalized": text}


def is_advice_request(question: str) -> bool:
    text = normalize_question(question)
    return any(pattern.search(text) for pattern in ADVICE_PATTERNS)


def _iter_chunk_artifacts(chunks_dir: Path) -> Iterable[dict[str, Any]]:
    if not chunks_dir.exists():
        return []

    artifacts: list[dict[str, Any]] = []
    for path in sorted(chunks_dir.glob("*.json")):
        if path.name == "manifest.json":
            continue
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(artifact, dict) and isinstance(artifact.get("chunks"), list):
            artifacts.append(artifact)
    return artifacts


def _load_embedding_index(embeddings_dir: Path) -> dict[str, list[float]]:
    index: dict[str, list[float]] = {}
    if not embeddings_dir.exists():
        return index
    for path in sorted(embeddings_dir.glob("*.json")):
        if path.name == "manifest.json":
            continue
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(artifact, dict):
            continue
        for record in artifact.get("embeddings", []):
            if isinstance(record, dict) and isinstance(record.get("chunk_id"), str):
                vector = record.get("embedding")
                if isinstance(vector, list) and all(isinstance(x, (int, float)) for x in vector):
                    index[record["chunk_id"]] = [float(value) for value in vector]
    return index


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
    norm_a = math.sqrt(sum(value * value for value in vec_a))
    norm_b = math.sqrt(sum(value * value for value in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _token_overlap_score(query: str, text: str) -> float:
    query_tokens = {token.lower() for token in re.findall(r"[a-z0-9]+", query) if token}
    text_tokens = {token.lower() for token in re.findall(r"[a-z0-9]+", text) if token}
    if not query_tokens or not text_tokens:
        return 0.0
    overlap = query_tokens & text_tokens
    if not overlap:
        return 0.0
    return len(overlap) / max(len(query_tokens | text_tokens), 1)


def retrieve_chunks(
    question: str,
    *,
    chunks_dir: Path = DEFAULT_CHUNKS_DIR,
    embeddings_dir: Path = DEFAULT_EMBEDDINGS_DIR,
    top_k: int = 5,
    min_relevance: float | None = None,
) -> list[dict[str, Any]]:
    screen = screen_question(question)
    if not screen["allowed"]:
        raise ValueError(screen["reason"])

    query = screen["normalized"]
    candidates: list[dict[str, Any]] = []
    embedding_index = _load_embedding_index(embeddings_dir)
    vector_query: list[float] | None = None

    if embedding_index:
        try:
            vector_query = embed_query(query)
        except Exception:
            vector_query = None

    for artifact in _iter_chunk_artifacts(chunks_dir):
        for chunk in artifact.get("chunks", []):
            if not isinstance(chunk, dict):
                continue
            text = str(chunk.get("text", "")).strip()
            if not text:
                continue
            score = 0.0
            if vector_query is not None and chunk.get("chunk_id") in embedding_index:
                score = _cosine_similarity(vector_query, embedding_index[chunk["chunk_id"]])
            else:
                score = _token_overlap_score(query, text)

            candidates.append(
                {
                    "chunk_id": chunk.get("chunk_id"),
                    "source_id": chunk.get("source_id"),
                    "title": chunk.get("title") or artifact.get("title") or "Unknown source",
                    "url": chunk.get("url") or artifact.get("url") or FALLBACK_CITATION,
                    "text": text,
                    "retrieved_at": chunk.get("retrieved_at") or artifact.get("retrieved_at"),
                    "heading_path": chunk.get("heading_path") or [],
                    "score": float(score),
                }
            )

    if not candidates:
        return []

    scored = sorted(candidates, key=lambda item: item["score"], reverse=True)
    if min_relevance is not None:
        scored = [item for item in scored if item["score"] >= float(min_relevance)]
    return scored[: max(1, int(top_k))]


def _citations_for_evidence(evidence: list[dict[str, Any]]) -> list[dict[str, str]]:
    citations: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in evidence:
        url = str(item.get("url") or FALLBACK_CITATION).strip()
        if url and url not in seen:
            seen.add(url)
            citations.append({
                "url": url,
                "label": str(item.get("title") or "Source"),
            })
    if not citations:
        citations.append({"url": FALLBACK_CITATION, "label": "SEBI investor education"})
    return citations


def build_answer(question: str, evidence: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    screening = screen_question(question)
    if not screening["allowed"]:
        return {
            "status": "rejected",
            "answer": screening["reason"],
            "citations": [{"url": FALLBACK_CITATION, "label": "SEBI investor education"}],
            "last_updated_from_sources": None,
        }

    if is_advice_request(question):
        return {
            "status": "refused",
            "answer": "I can only answer factual questions. For investment decisions, please consult official fund materials or a licensed financial adviser.",
            "citations": [{"url": FALLBACK_CITATION, "label": "SEBI investor education"}],
            "last_updated_from_sources": None,
        }

    evidence_list = evidence if evidence is not None else retrieve_chunks(question)
    if not evidence_list:
        return {
            "status": "unverified",
            "answer": "I could not verify this fact from the available sources.",
            "citations": [{"url": FALLBACK_CITATION, "label": "SEBI investor education"}],
            "last_updated_from_sources": None,
        }

    text = evidence_list[0]["text"]
    cleaned = " ".join(text.split())
    if len(cleaned) > 220:
        cleaned = cleaned[:220].rstrip() + "..."

    answer = f"The available source material states: {cleaned}."
    times = [item.get("retrieved_at") for item in evidence_list if item.get("retrieved_at")]
    last_updated = max(times) if times else None
    citations = _citations_for_evidence(evidence_list)
    return {
        "status": "answered",
        "answer": answer,
        "citations": citations,
        "last_updated_from_sources": last_updated,
    }


def answer_question(
    question: str,
    *,
    chunks_dir: Path = DEFAULT_CHUNKS_DIR,
    embeddings_dir: Path = DEFAULT_EMBEDDINGS_DIR,
    top_k: int = 5,
    min_relevance: float | None = None,
) -> dict[str, Any]:
    if not isinstance(question, str):
        raise TypeError("Question must be a string")

    screen = screen_question(question)
    if not screen["allowed"]:
        return build_answer(question)

    evidence = retrieve_chunks(
        question,
        chunks_dir=chunks_dir,
        embeddings_dir=embeddings_dir,
        top_k=top_k,
        min_relevance=min_relevance,
    )
    return build_answer(question, evidence)


__all__ = [
    "answer_question",
    "build_answer",
    "is_advice_request",
    "retrieve_chunks",
    "screen_question",
]
