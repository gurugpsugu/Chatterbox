"""Build a deployable snapshot of verified facts and performance data."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.loading.load_documents import validate_artifact
from src.loading.scrape_sources import DEFAULT_REGISTRY, load_registry
from src.retrieval.retriever import (
    _extract_annualized_returns,
    _extract_historical_sip_performance,
    _extract_numeric_facts,
    _extract_riskometer,
)

DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "fund_facts.json"


def build_fact_cache(
    sources: list[dict[str, Any]],
    input_dir: Path,
) -> dict[str, Any]:
    funds: dict[str, list[dict[str, Any]]] = {}
    skipped: list[dict[str, str]] = []
    for source in sources:
        fund_id = source.get("fund_id")
        if not isinstance(fund_id, str):
            continue
        artifact_path = input_dir / f"{source['source_id']}.json"
        if not artifact_path.is_file():
            skipped.append({"source_id": source["source_id"], "reason": "Raw artifact is missing"})
            continue
        try:
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            skipped.append({"source_id": source["source_id"], "reason": f"Unable to read artifact: {error}"})
            continue
        document, validation_error = validate_artifact(artifact, source)
        if validation_error or document is None:
            skipped.append({
                "source_id": source["source_id"],
                "reason": validation_error or "Artifact validation failed",
            })
            continue

        lines = document["text"].splitlines()
        facts = _extract_numeric_facts(lines)
        sip_history = _extract_historical_sip_performance(lines)
        annualized_returns = _extract_annualized_returns(lines)
        riskometer = _extract_riskometer(document["text"])
        if not facts and not sip_history and not annualized_returns and not riskometer:
            skipped.append({"source_id": source["source_id"], "reason": "No supported numeric facts found"})
            continue
        source_cache = {
            "source_id": source["source_id"],
            "retrieved_at": document["retrieved_at"],
            "facts": facts,
            "periods": sip_history["periods"] if sip_history else [],
            "annualized_returns": annualized_returns,
            "as_of": sip_history["as_of"] if sip_history else None,
            "riskometer": riskometer,
        }
        funds.setdefault(fund_id, []).append(source_cache)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "funds": [
            {"fund_id": fund_id, "sources": source_records}
            for fund_id, source_records in sorted(funds.items())
        ],
        "skipped_sources": skipped,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a deployable facts and performance cache from validated scraped pages."
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    try:
        sources = load_registry(args.registry)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2

    cache = build_fact_cache(sources, args.input)
    if not cache["funds"]:
        print("No verified fund facts were found in the scraped source artifacts.", file=sys.stderr)
        return 1
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        print(f"Unable to write fact cache {args.output}: {error}", file=sys.stderr)
        return 2

    print(json.dumps({
        "funds": len(cache["funds"]),
        "sources_with_data": sum(len(fund["sources"]) for fund in cache["funds"]),
        "skipped_sources": len(cache["skipped_sources"]),
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
