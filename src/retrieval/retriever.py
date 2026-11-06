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


def _select_registry_sources(
    question: str,
    registry_path: Path = DEFAULT_REGISTRY,
    sources: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if sources is None:
        sources = load_registry(registry_path)
    query_terms = set(re.findall(r"[a-z0-9]+", question.lower())) - GENERIC_QUERY_TERMS
    if not query_terms:
        return []

    ranked_sources: list[tuple[int, int, dict[str, Any]]] = []
    for source in sources:
        title_terms = set(re.findall(r"[a-z0-9]+", source["title"].lower())) - GENERIC_QUERY_TERMS
        overlap = len(query_terms & title_terms)
        if overlap:
            ranked_sources.append((overlap, len(title_terms), source))
    if not ranked_sources:
        return []
    ranked_sources.sort(key=lambda result: (result[0], -result[1]), reverse=True)
    best_overlap, best_title_size, best_source = ranked_sources[0]
    if best_overlap < 2:
        return []

    best_fund_id = best_source.get("fund_id")
    selected_group = [
        source for overlap, title_size, source in ranked_sources
        if overlap == best_overlap
        and title_size == best_title_size
        and source.get("fund_id") == best_fund_id
    ]
    other_best_funds = {
        source.get("fund_id", source["source_id"])
        for overlap, title_size, source in ranked_sources
        if overlap == best_overlap and title_size == best_title_size
    }
    if len(other_best_funds) > 1:
        return []
    selected_group.sort(key=lambda source: (source.get("source_priority", 10), source["source_id"]))
    return selected_group


def _extract_numeric_facts(lines: list[str]) -> list[dict[str, Any]]:
    fact_fields = (
        (
            "minimum_sip",
            "Minimum SIP",
            re.compile(r"\bmin(?:imum)?\.?\s+(?:for\s+)?sip\b", re.IGNORECASE),
            "₹",
        ),
        (
            "aum",
            "Fund size (AUM)",
            re.compile(r"\b(?:fund\s+size|aum)\b", re.IGNORECASE),
            "₹ Cr",
        ),
        (
            "expense_ratio",
            "Expense ratio",
            re.compile(r"\bexpense\s+ratio\b", re.IGNORECASE),
            "%",
        ),
        (
            "nav",
            "NAV",
            re.compile(r"\bnav\b", re.IGNORECASE),
            "₹",
        ),
    )
    facts: list[dict[str, Any]] = []
    seen: set[str] = set()
    value_pattern = re.compile(
        r"₹\s*([\d,]+(?:\.\d+)?)|([\d,]+(?:\.\d+)?)\s*(%|Cr)(?![a-z])",
        re.IGNORECASE,
    )
    for index, line in enumerate(lines):
        for key, label, label_pattern, default_unit in fact_fields:
            if key in seen or not label_pattern.search(line):
                continue
            value_text = line
            if not value_pattern.search(value_text) and index + 1 < len(lines):
                value_text = lines[index + 1]
            match = value_pattern.search(value_text)
            if not match:
                continue
            numeric_text = match.group(1) or match.group(2)
            unit = match.group(3) or default_unit
            if default_unit == "₹ Cr":
                unit = "₹ Cr"
            elif match.group(1):
                unit = default_unit
            value = float(numeric_text.replace(",", ""))
            display_number = f"{value:,.2f}".rstrip("0").rstrip(".")
            if unit == "₹":
                display_value = f"₹{display_number}"
            elif unit == "₹ Cr":
                display_value = f"₹{display_number} Cr"
            elif unit == "%":
                display_value = f"{display_number}%"
            else:
                display_value = f"{display_number} {unit}".strip()
            facts.append({
                "key": key,
                "label": label,
                "value": value,
                "unit": unit,
                "display_value": display_value,
            })
            seen.add(key)
    return facts


def _extract_historical_sip_performance(lines: list[str]) -> dict[str, Any] | None:
    text = " ".join(" ".join(line.split()) for line in lines if line.strip())
    header_match = re.search(
        r"(?:over the past|period)\b.*?(?:would['’]ve become|would have become).*?\breturns?\b",
        text,
        re.IGNORECASE,
    )
    if header_match is None:
        return None

    monthly_match = re.search(
        r"\bmonthly investment\b[^₹\d]{0,24}(?:₹\s*|INR\s*)([\d,]+(?:\.\d+)?)",
        text[:header_match.start()],
        re.IGNORECASE,
    )
    if monthly_match is None:
        return None
    monthly_investment = float(monthly_match.group(1).replace(",", ""))
    if monthly_investment <= 0:
        return None

    row_pattern = re.compile(
        r"\b(\d+(?:\.\d+)?)\s+(months?|years?)\s+"
        r"(?:₹\s*|INR\s*)([\d,]+(?:\.\d+)?)\s+"
        r"(?:₹\s*|INR\s*)([\d,]+(?:\.\d+)?)\s+"
        r"([+-]?\d+(?:\.\d+)?)\s*%",
        re.IGNORECASE,
    )
    remaining_text = text[header_match.end():]
    section_end = re.search(
        r"\b(?:holdings|fund manager|riskometer|exit load|expense ratio)\b",
        remaining_text,
        re.IGNORECASE,
    )
    if section_end:
        remaining_text = remaining_text[:section_end.start()]
    periods: list[dict[str, Any]] = []
    for row_match in row_pattern.finditer(remaining_text):
        duration = float(row_match.group(1))
        unit = row_match.group(2).lower()
        months = round(duration * (12 if unit.startswith("year") else 1))
        if months <= 0:
            continue
        total_investment = float(row_match.group(3).replace(",", ""))
        would_become = float(row_match.group(4).replace(",", ""))
        expected_investment = monthly_investment * months
        if abs(total_investment - expected_investment) > max(1, expected_investment * 0.02):
            continue

        return_value = float(row_match.group(5))
        value_return = (would_become / total_investment - 1) * 100
        if abs(value_return - return_value) > 0.1:
            continue
        periods.append({
            "period": f"{row_match.group(1)} {row_match.group(2)}",
            "months": months,
            "total_investment": total_investment,
            "would_become": would_become,
            "return_percent": return_value,
            "display_return": row_match.group(5) + "%",
        })

    if not periods:
        return None

    date_pattern = r"(\d{1,2}\s+[A-Za-z]{3,9}\s+['’]?\d{2,4})"
    as_of_match = re.search(rf"\b(?:as on|as of)\s*:?\s*{date_pattern}", text, re.IGNORECASE)
    if as_of_match is None:
        as_of_match = re.search(rf"\bNAV\s*:?\s*{date_pattern}", text, re.IGNORECASE)
    as_of = as_of_match.group(1) if as_of_match else None

    return {
        "monthly_investment": monthly_investment,
        "as_of": as_of,
        "periods": periods,
    }


def get_fund_historical_performance(
    fund_id: str,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    sources = [
        source for source in load_registry(registry_path)
        if source.get("fund_id") == fund_id
    ]
    if not sources:
        raise KeyError(f"No approved sources are configured for fund {fund_id!r}")
    sources.sort(key=lambda source: (source.get("source_priority", 10), source["source_id"]))

    fetch_errors: list[str] = []
    for source in sources:
        try:
            text = _fetch_source_text(source["url"])
        except RuntimeError as error:
            fetch_errors.append(f"{source['publisher']}: {error}")
            continue
        history = _extract_historical_sip_performance(text.splitlines())
        if history is None:
            continue
        return {
            "status": "available",
            "fund_id": fund_id,
            **history,
            "citation": {
                "url": source["url"],
                "label": source["title"],
                "publisher": source["publisher"],
                "source_type": source["source_type"],
            },
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

    if fetch_errors:
        raise RuntimeError("Unable to retrieve historical return data: " + "; ".join(fetch_errors))
    return {
        "status": "unavailable",
        "fund_id": fund_id,
        "message": "Historical SIP return data was not present in the approved source pages.",
    }


def _requested_fact_key(question: str) -> str | None:
    lowered = question.lower()
    if "expense ratio" in lowered or "total expense ratio" in lowered:
        return "expense_ratio"
    if "sip" in lowered and any(term in lowered for term in ("minimum", "min.", "min ")):
        return "minimum_sip"
    if "aum" in lowered or "fund size" in lowered:
        return "aum"
    if re.search(r"\bnav\b", lowered):
        return "nav"
    return None


def _suggest_numeric_follow_ups(
    source_title: str,
    facts: list[dict[str, Any]],
    current_fact_key: str | None,
) -> list[str]:
    questions = {
        "minimum_sip": f"What is the minimum SIP for {source_title}?",
        "aum": f"What is the fund size (AUM) of {source_title}?",
        "expense_ratio": f"What is the expense ratio of {source_title}?",
        "nav": f"What is the latest NAV for {source_title}?",
    }
    return [
        questions[fact["key"]]
        for fact in facts
        if fact["key"] != current_fact_key and fact["key"] in questions
    ][:2]


def _chart_for_fact(fact: dict[str, Any], source_title: str) -> dict[str, Any]:
    value = float(fact["value"])
    magnitude = 10 ** math.floor(math.log10(value)) if value > 0 else 1
    scale_max = next(
        multiplier * magnitude
        for multiplier in (1, 1.25, 1.5, 2, 2.5, 5, 10)
        if multiplier * magnitude >= value * 1.2
    )
    return {
        "verified": True,
        "title": f"{fact['label']} — {source_title}",
        "unit": fact["unit"],
        "scale_max": scale_max,
        "source_label": source_title,
        "data": [{
            "label": fact["label"],
            "value": value,
            "display_value": fact["display_value"],
        }],
    }


def _live_source_evidence(
    question: str,
    registry_path: Path = DEFAULT_REGISTRY,
    context: str = "",
) -> list[dict[str, Any]]:
    source_query = " ".join(part for part in (question, context) if part)
    sources = _select_registry_sources(source_query, registry_path)
    if not sources:
        return []

    requested_fact_key = _requested_fact_key(question)
    query_terms = set(re.findall(r"[a-z0-9]+", source_query.lower())) - GENERIC_QUERY_TERMS
    if not query_terms:
        return []

    important_terms = query_terms & {
        "aum", "charge", "expense", "exit", "fee", "load",
        "lock", "minimum", "nav", "ratio", "risk", "sip", "tax",
    }
    if not important_terms:
        important_terms = query_terms

    fetch_errors: list[str] = []
    for source in sources:
        try:
            text = _fetch_source_text(source["url"])
        except RuntimeError as error:
            fetch_errors.append(f"{source['publisher']}: {error}")
            continue
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            continue

        facts = _extract_numeric_facts(lines)
        requested_fact = next(
            (fact for fact in facts if fact["key"] == requested_fact_key),
            None,
        )
        best_window: list[str] = []
        best_score = 0
        if requested_fact is not None:
            best_window = [requested_fact["label"], requested_fact["display_value"]]
            best_score = 4
        elif requested_fact_key is not None:
            continue

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
            continue

        evidence = {
            "chunk_id": f"live-{source['source_id']}",
            "source_id": source["source_id"],
            "title": source["title"],
            "url": source["url"],
            "publisher": source["publisher"],
            "source_type": source["source_type"],
            "text": " ".join(best_window),
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "heading_path": [],
            "score": float(best_score),
            "facts": facts,
        }
        if requested_fact is not None:
            evidence["metric"] = requested_fact
        return [evidence]

    if fetch_errors:
        raise RuntimeError(
            "No matching evidence was available; source fetch failures: "
            + "; ".join(fetch_errors)
        )
    return []


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
    context: str = "",
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

    context_screen = screen_question(context) if context else {"allowed": True, "normalized": ""}
    if not context_screen["allowed"]:
        raise ValueError(context_screen["reason"])
    query = " ".join(part for part in (screen["normalized"], context_screen["normalized"]) if part)
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
            return _live_source_evidence(
                screen["normalized"],
                registry_path,
                context_screen["normalized"],
            )
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

    registry_sources = load_registry(registry_path)
    source_by_id = {source["source_id"]: source for source in registry_sources}
    for candidate in candidates:
        source_id = candidate.get("source_id")
        source = source_by_id.get(source_id) if isinstance(source_id, str) else None
        if source:
            candidate["publisher"] = source["publisher"]
            candidate["source_type"] = source["source_type"]

    preferred_sources = _select_registry_sources(query, registry_path, registry_sources)
    if preferred_sources:
        preferred_by_id = {source["source_id"]: source for source in preferred_sources}
        candidates = [
            candidate for candidate in candidates
            if isinstance(candidate.get("source_id"), str)
            and candidate["source_id"] in preferred_by_id
        ]
        if not candidates:
            return []
        for candidate in candidates:
            source = preferred_by_id[candidate["source_id"]]
            candidate["source_priority"] = source.get("source_priority", 10)
        best_priority = min(candidate["source_priority"] for candidate in candidates)
        candidates = [
            candidate for candidate in candidates
            if candidate["source_priority"] == best_priority
        ]

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
            citation = {
                "url": url,
                "label": str(item.get("title") or "Source"),
            }
            if item.get("publisher"):
                citation["publisher"] = str(item["publisher"])
            if item.get("source_type"):
                citation["source_type"] = str(item["source_type"])
            citations.append(citation)
    if not citations:
        citations.append({
            "url": FALLBACK_CITATION,
            "label": "SEBI investor education",
            "publisher": "SEBI",
            "source_type": "official_regulator",
        })
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
    source_title = str(evidence_list[0].get("title") or "the available source")
    facts: list[dict[str, Any]] = []
    for evidence_item in evidence_list:
        evidence_facts = evidence_item.get("facts")
        if isinstance(evidence_facts, list):
            facts.extend(
                fact for fact in evidence_facts
                if isinstance(fact, dict) and isinstance(fact.get("key"), str)
            )
        else:
            facts.extend(_extract_numeric_facts(
                [line.strip() for line in str(evidence_item.get("text", "")).splitlines() if line.strip()]
            ))
    deduplicated_facts = {fact["key"]: fact for fact in facts}
    current_fact_key = _requested_fact_key(question)
    metric = deduplicated_facts.get(current_fact_key) if current_fact_key else None
    if metric is None and current_fact_key:
        for evidence_item in evidence_list:
            extracted = _extract_numeric_facts(
                [line.strip() for line in str(evidence_item.get("text", "")).splitlines() if line.strip()]
            )
            metric = next((fact for fact in extracted if fact["key"] == current_fact_key), None)
            if metric:
                source_title = str(evidence_item.get("title") or source_title)
                break

    cleaned = " ".join(text.split())
    if metric:
        answer = f"The {metric['label'].lower()} shown for {source_title} is {metric['display_value']}."
    else:
        if len(cleaned) > 220:
            cleaned = cleaned[:220].rstrip() + "..."
        answer = f"I found this in the available source material: {cleaned}."

    times = [item.get("retrieved_at") for item in evidence_list if item.get("retrieved_at")]
    last_updated = max(times) if times else None
    citations = _citations_for_evidence(evidence_list)
    response: dict[str, Any] = {
        "status": "answered",
        "answer": answer,
        "citations": citations,
        "last_updated_from_sources": last_updated,
    }
    if metric:
        response["metric"] = metric
        response["chart"] = _chart_for_fact(metric, source_title)
    follow_ups = _suggest_numeric_follow_ups(
        source_title,
        list(deduplicated_facts.values()),
        current_fact_key,
    )
    if follow_ups:
        response["follow_ups"] = follow_ups
    return response


def answer_question(
    question: str,
    *,
    context: str = "",
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
    if context and not screen_question(context)["allowed"]:
        return build_answer(context)

    evidence = retrieve_chunks(
        question,
        context=context,
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
