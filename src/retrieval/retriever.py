"""Retrieval, question screening, and evidence-backed answer generation."""

from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from src.embedding.embed_chunks import embed_query, load_settings
from src.loading.scrape_sources import PageTextExtractor, load_registry

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHUNKS_DIR = PROJECT_ROOT / "data" / "chunks"
DEFAULT_EMBEDDINGS_DIR = PROJECT_ROOT / "data" / "embeddings"
DEFAULT_SETTINGS = PROJECT_ROOT / "config" / "settings.json"
DEFAULT_REGISTRY = PROJECT_ROOT / "config" / "sources.json"
FALLBACK_CITATION = "https://www.sebi.gov.in/"
LIVE_SOURCE_TIMEOUT_SECONDS = 8
MAX_SOURCE_BYTES = 4 * 1024 * 1024
GENERIC_QUERY_TERMS = {
    "a", "an", "and", "about", "can", "does", "do", "find", "for", "fund",
    "growth", "hdfc", "i", "in", "is", "latest", "me", "mutual", "of",
    "plan", "please", "scheme", "tell", "the", "what", "which",
}


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def _fetch_source_text(url: str, timeout: int = LIVE_SOURCE_TIMEOUT_SECONDS) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ChatterboxPublicPageFetcher/1.0"},
    )
    opener = urllib.request.build_opener(_NoRedirectHandler)
    try:
        with opener.open(request, timeout=timeout) as response:
            final_url = response.geturl()
            if final_url != url:
                raise RuntimeError("The approved source redirected to a different URL.")
            if not response.headers.get("Content-Type", "").lower().startswith("text/html"):
                raise RuntimeError("The approved source did not return an HTML page.")
            content = response.read(MAX_SOURCE_BYTES + 1)
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"The approved source returned HTTP {error.code}."
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(
            f"The approved source could not be reached: {error.reason}"
        ) from error
    except TimeoutError as error:
        raise RuntimeError("The approved source request timed out.") from error
    if len(content) > MAX_SOURCE_BYTES:
        raise RuntimeError("The approved source page exceeded the maximum supported size.")
    charset = response.headers.get_content_charset() or "utf-8"
    try:
        html = content.decode(charset)
    except (LookupError, UnicodeDecodeError) as error:
        raise RuntimeError("The approved source page could not be decoded.") from error

    extractor = PageTextExtractor()
    extractor.feed(html)
    return extractor.get_text()


def _select_registry_source(
    question: str,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict[str, Any] | None:
    sources = load_registry(registry_path)
    query_terms = set(re.findall(r"[a-z0-9]+", question.lower())) - GENERIC_QUERY_TERMS
    if not query_terms:
        return None

    ranked_sources: list[tuple[int, int, dict[str, Any]]] = []
    for source in sources:
        title_terms = set(
            re.findall(r"[a-z0-9]+", f"{source['title']} {source['source_id']}".lower())
        ) - GENERIC_QUERY_TERMS
        overlap = len(query_terms & title_terms)
        if overlap:
            ranked_sources.append((overlap, len(title_terms), source))
    if not ranked_sources:
        return None
    ranked_sources.sort(key=lambda result: (result[0], -result[1]), reverse=True)
    best_overlap, _, best_source = ranked_sources[0]
    if best_overlap < 2:
        return None
    if len(ranked_sources) > 1 and ranked_sources[1][0] == best_overlap:
        return None
    return best_source


def _live_source_evidence(question: str, registry_path: Path = DEFAULT_REGISTRY) -> list[dict[str, Any]]:
    source = _select_registry_source(question, registry_path)
    if source is None:
        return []

    text = _fetch_source_text(source["url"])
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    query_terms = set(re.findall(r"[a-z0-9]+", question.lower())) - GENERIC_QUERY_TERMS
    if not lines or not query_terms:
        return []

    important_terms = query_terms & {
        "aum", "charge", "expense", "exit", "fee", "load",
        "lock", "minimum", "nav", "ratio", "risk", "sip", "tax",
    }
    if not important_terms:
        important_terms = query_terms

    requested_field = None
    if {"expense", "ratio"} <= query_terms:
        requested_field = re.compile(r"\bexpense\s+ratio\b", re.IGNORECASE)
    elif "sip" in query_terms and "minimum" in query_terms:
        requested_field = re.compile(r"\bmin(?:imum)?\.?\s+(?:for\s+)?sip\b", re.IGNORECASE)
    value_pattern = re.compile(r"(?:₹\s*[\d,]+(?:\.\d+)?|\b\d+(?:\.\d+)?\s*%)")

    best_window: list[str] = []
    best_score = 0
    if requested_field is not None:
        for index, line in enumerate(lines[:-1]):
            if requested_field.search(line) and value_pattern.search(lines[index + 1]):
                best_window = [line, lines[index + 1]]
                best_score = 4
                break

    if not best_window:
        for index in range(len(lines)):
            start = max(0, index - 2)
            end = min(len(lines), index + 6)
            window = lines[start:end]
            window_terms = set(re.findall(r"[a-z0-9]+", " ".join(window).lower()))
            matched_terms = important_terms & window_terms
            score = len(matched_terms) * 4 + len(query_terms & window_terms)
            if score >= best_score and score > 0:
                best_score = score
                best_window = window

    if not best_window or best_score < 4:
        return []

    return [{
        "chunk_id": f"live-{source['source_id']}",
        "source_id": source["source_id"],
        "title": source["title"],
        "url": source["url"],
        "text": " ".join(best_window),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "heading_path": [],
        "score": float(best_score),
    }]


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


def retrieve_chunks(
    question: str,
    *,
    chunks_dir: Path = DEFAULT_CHUNKS_DIR,
    embeddings_dir: Path = DEFAULT_EMBEDDINGS_DIR,
    top_k: int = 5,
    min_relevance: float | None = None,
    live_source_fallback: bool | None = None,
    registry_path: Path = DEFAULT_REGISTRY,
    settings_path: Path = DEFAULT_SETTINGS,
) -> list[dict[str, Any]]:
    screen = screen_question(question)
    if not screen["allowed"]:
        raise ValueError(screen["reason"])

    query = screen["normalized"]
    candidates: list[dict[str, Any]] = []
    embedding_index = _load_embedding_index(embeddings_dir)
    if not embedding_index:
        if live_source_fallback is None:
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise ValueError(f"Unable to read retrieval settings {settings_path}: {error}") from error
            retrieval_settings = settings.get("retrieval") if isinstance(settings, dict) else None
            live_source_fallback = (
                retrieval_settings.get("live_source_fallback", False)
                if isinstance(retrieval_settings, dict)
                else False
            )
            if not isinstance(live_source_fallback, bool):
                raise ValueError("retrieval.live_source_fallback must be a boolean")
        if live_source_fallback:
            return _live_source_evidence(query, registry_path)
        return []

    try:
        vector_query = embed_query(query)
    except Exception as error:
        raise RuntimeError(f"Unable to embed question for retrieval: {error}") from error

    for artifact in _iter_chunk_artifacts(chunks_dir):
        for chunk in artifact.get("chunks", []):
            if not isinstance(chunk, dict):
                continue
            text = str(chunk.get("text", "")).strip()
            chunk_id = chunk.get("chunk_id")
            vector = embedding_index.get(chunk_id) if isinstance(chunk_id, str) else None
            if not text or vector is None:
                continue
            score = _cosine_similarity(vector_query, vector)

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
            "answer": "I’m happy to help with factual fund information. For investment decisions, please refer to official fund materials or a licensed financial adviser.",
            "citations": [{"url": FALLBACK_CITATION, "label": "SEBI investor education"}],
            "last_updated_from_sources": None,
        }

    evidence_list = evidence if evidence is not None else retrieve_chunks(question)
    if not evidence_list:
        return {
            "status": "unverified",
            "answer": "I’m sorry, I couldn’t verify this fact in the sources currently available.",
            "citations": [{"url": FALLBACK_CITATION, "label": "SEBI investor education"}],
            "last_updated_from_sources": None,
        }

    text = evidence_list[0]["text"]
    cleaned = " ".join(text.split())
    if len(cleaned) > 220:
        cleaned = cleaned[:220].rstrip() + "..."

    answer = f"I found this in the available source material: {cleaned}."
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
