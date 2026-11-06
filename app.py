"""Vercel web entrypoint for the Chatterbox FAQ assistant."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.loading.scrape_sources import DEFAULT_REGISTRY, load_registry
from src.retrieval.retriever import answer_question, get_fund_historical_performance
from src.ui.web_page import HOME_PAGE

PROJECT_ROOT = Path(__file__).resolve().parent
FUND_CATALOG_PATH = PROJECT_ROOT / "config" / "funds.json"

app = FastAPI(title="Chatterbox", description="Facts-only mutual fund enquiry assistant")


class ChatRequest(BaseModel):
    question: str
    context: str = ""


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return HOME_PAGE


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/funds")
def fund_catalog() -> dict[str, Any]:
    try:
        catalog = json.loads(FUND_CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Unable to read fund catalog {FUND_CATALOG_PATH}: {error}") from error
    if not isinstance(catalog, dict) or not isinstance(catalog.get("categories"), list) \
            or not isinstance(catalog.get("funds"), list) or not catalog["funds"]:
        raise ValueError("Fund catalog must contain category and fund lists")
    categories = catalog["categories"]
    if not categories or not all(isinstance(item, str) and item.strip() for item in categories):
        raise ValueError("Fund catalog categories must be non-empty strings")
    if len(set(categories)) != len(categories):
        raise ValueError("Fund catalog categories must be unique")

    sources = {
        source["source_id"]: source
        for source in load_registry(DEFAULT_REGISTRY)
    }
    funds = []
    seen_fund_ids: set[str] = set()
    for fund in catalog["funds"]:
        if not isinstance(fund, dict):
            raise ValueError("Every fund catalog entry must be an object")
        for field in ("fund_id", "name", "amc", "category"):
            if not isinstance(fund.get(field), str) or not fund[field].strip():
                raise ValueError(f"Fund catalog entry is missing {field}")
        fund_id = fund["fund_id"]
        if fund_id in seen_fund_ids:
            raise ValueError(f"Duplicate fund ID in catalog: {fund_id}")
        seen_fund_ids.add(fund_id)
        if fund["category"] not in categories:
            raise ValueError(f"Fund {fund_id} uses an unknown category")
        source_ids = fund.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids \
                or not all(isinstance(item, str) and item for item in source_ids):
            raise ValueError(f"Fund {fund_id} must reference at least one source")
        if len(set(source_ids)) != len(source_ids):
            raise ValueError(f"Fund {fund_id} contains duplicate source IDs")
        try:
            fund_sources = [sources[source_id] for source_id in source_ids]
        except KeyError as error:
            raise ValueError(f"Fund {fund_id} references an unknown source") from error
        if any(source.get("fund_id") != fund_id for source in fund_sources):
            raise ValueError(f"Fund {fund_id} references a source assigned to another fund")
        if any(
            source.get("amc") != fund["amc"] or source.get("category") != fund["category"]
            for source in fund_sources
        ):
            raise ValueError(f"Fund {fund_id} does not match its source metadata")
        official = next(
            (source for source in fund_sources if source["source_type"] == "official_amc"),
            None,
        )
        fallback = next(
            (source for source in fund_sources if source["publisher"] == "Groww"),
            None,
        )
        funds.append({
            "fund_id": fund["fund_id"],
            "name": fund["name"],
            "amc": fund["amc"],
            "category": fund["category"],
            "official_url": official["url"] if official else None,
            "official_publisher": official["publisher"] if official else None,
            "fallback_url": fallback["url"] if fallback else None,
        })
    return {
        "categories": categories,
        "amcs": sorted({fund["amc"] for fund in funds}),
        "funds": funds,
        "source_policy": "official_first_with_labeled_third_party_fallback",
    }


@app.get("/api/funds/{fund_id}/performance")
def fund_performance(fund_id: str) -> dict[str, Any]:
    try:
        return get_fund_historical_performance(fund_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Unknown fund ID.") from error


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    try:
        if request.context.strip():
            return answer_question(request.question, context=request.context)
        return answer_question(request.question)
    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail="The approved source lookup failed or timed out. Please try again.",
        ) from error
