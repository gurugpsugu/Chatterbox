"""Create deterministic, provenance-preserving chunks from loaded documents."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.loading.load_documents import DEFAULT_INPUT, load_documents
from src.loading.scrape_sources import DEFAULT_REGISTRY, load_registry


DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "chunks"
DEFAULT_MANIFEST = DEFAULT_OUTPUT / "manifest.json"
DEFAULT_MAX_CHARS = 1200
CHUNKER_VERSION = "1.0"
SECTION_HEADINGS = {
    "asset allocation",
    "education",
    "exit load",
    "exit load, stamp duty and tax",
    "facts",
    "fund management",
    "fund overview",
    "holdings",
    "minimum investments",
    "overview",
    "portfolio",
    "returns and rankings",
    "scheme details",
    "tax implication",
}
FACT_LABELS = {
    "expense ratio",
    "fund size (aum)",
    "min. for 1st investment",
    "min. for 2nd investment",
    "min. for sip",
    "minimum investment",
    "minimum sip",
    "rating",
}
HOLDINGS_HEADER = ("name", "sector", "instruments", "assets")
WHITESPACE = re.compile(r"\s+")


def _normalize_line(line: str) -> str:
    return WHITESPACE.sub(" ", line).strip()


def _is_section_heading(line: str) -> bool:
    normalized = line.casefold().rstrip(":")
    return normalized in SECTION_HEADINGS or normalized.startswith("holdings (")


def _is_fact_label(line: str) -> bool:
    normalized = line.casefold().rstrip(":")
    return normalized in FACT_LABELS or normalized.startswith("nav:")


def _split_long_line(text: str, max_chars: int) -> list[str]:
    words = text.split()
    parts: list[str] = []
    current: list[str] = []
    current_length = 0
    for word in words:
        added_length = len(word) + (1 if current else 0)
        if current and current_length + added_length > max_chars:
            parts.append(" ".join(current))
            current = []
            current_length = 0
        current.append(word)
        current_length += added_length
    if current:
        parts.append(" ".join(current))
    return parts


def _build_units(
    document: dict[str, Any],
    max_chars: int,
) -> list[dict[str, Any]]:
    lines = [_normalize_line(line) for line in document["text"].splitlines()]
    lines = [line for line in lines if line]
    title = document["title"]
    heading_path = [title]
    units: list[dict[str, Any]] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        if _is_section_heading(line):
            if line.casefold().startswith("holdings ("):
                heading = line.rstrip(":")
                if index + 2 < len(lines) and lines[index + 2] == ")":
                    heading = f"Holdings ({lines[index + 1]})"
                    index += 2
                heading_path = [title, heading]
            else:
                heading_path = [title, line.rstrip(":")]
            index += 1
            continue

        if index == 0 and line == title:
            index += 1
            continue

        if tuple(item.casefold() for item in lines[index:index + 4]) == HOLDINGS_HEADER:
            table_header = " | ".join(lines[index:index + 4])
            index += 4
            while index < len(lines):
                if lines[index].casefold() == "see all":
                    index += 1
                    break
                if index + 3 >= len(lines):
                    break
                row = lines[index:index + 4]
                if _is_section_heading(row[0]):
                    break
                units.append(
                    {
                        "text": " | ".join(row),
                        "heading_path": list(heading_path),
                        "table_header": table_header,
                    }
                )
                index += 4
            continue

        if _is_fact_label(line) and index + 1 < len(lines):
            units.append(
                {
                    "text": f"{line}: {lines[index + 1]}",
                    "heading_path": list(heading_path),
                    "table_header": None,
                }
            )
            index += 2
            continue

        for part in _split_long_line(line, max_chars):
            units.append(
                {
                    "text": part,
                    "heading_path": list(heading_path),
                    "table_header": None,
                }
            )
        index += 1

    return units


def chunk_document(
    document: dict[str, Any],
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[dict[str, Any]]:
    """Split a validated loaded document while keeping facts and table rows intact."""
    if max_chars < 1:
        raise ValueError("max_chars must be a positive integer")
    required = ("source_id", "url", "title", "retrieved_at", "text")
    if any(not isinstance(document.get(field), str) or not document[field].strip() for field in required):
        raise ValueError("Document is missing required non-empty source metadata or text")

    units = _build_units(document, max_chars)
    if not units:
        return []

    chunks: list[dict[str, Any]] = []
    current_units: list[dict[str, Any]] = []
    current_heading: list[str] | None = None
    current_table_header: str | None = None

    def emit() -> None:
        nonlocal current_units
        if not current_units or current_heading is None:
            return
        context_lines = list(current_heading)
        if current_table_header:
            context_lines.append(current_table_header)
        body = "\n".join(unit["text"] for unit in current_units)
        text = "\n".join([*context_lines, body])
        chunk_index = len(chunks)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        identity = "\0".join(
            (document["source_id"], str(chunk_index), content_hash, CHUNKER_VERSION)
        )
        chunk_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
        chunks.append(
            {
                "chunk_id": f"{document['source_id']}-{chunk_id}",
                "source_id": document["source_id"],
                "url": document["url"],
                "title": document["title"],
                "heading_path": list(current_heading),
                "text": text,
                "content_hash": content_hash,
                "retrieved_at": document["retrieved_at"],
                "chunker_version": CHUNKER_VERSION,
            }
        )
        current_units = []

    for unit in units:
        unit_heading = unit["heading_path"]
        unit_table_header = unit["table_header"]
        same_context = (
            current_heading == unit_heading
            and current_table_header == unit_table_header
        )
        unit_length = len(unit["text"])
        current_length = sum(len(item["text"]) + 1 for item in current_units)
        if current_units and (
            not same_context
            or current_length + unit_length > max_chars
        ):
            emit()
        if not current_units:
            current_heading = unit_heading
            current_table_header = unit_table_header
        current_units.append(unit)

    emit()
    return chunks


def chunk_documents(
    documents: list[dict[str, Any]],
    output_dir: Path,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> dict[str, Any]:
    if max_chars < 1:
        raise ValueError("max_chars must be a positive integer")
    output_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []
    total_chunks = 0

    for document in documents:
        chunks = chunk_document(document, max_chars)
        source_id = document["source_id"]
        artifact_path = output_dir / f"{source_id}.json"
        artifact = {
            "source_id": source_id,
            "url": document["url"],
            "title": document["title"],
            "retrieved_at": document["retrieved_at"],
            "source_content_hash": document.get("content_sha256")
            or hashlib.sha256(document["text"].encode("utf-8")).hexdigest(),
            "chunker_version": CHUNKER_VERSION,
            "max_chars": max_chars,
            "chunk_count": len(chunks),
            "chunks": chunks,
        }
        artifact_path.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        total_chunks += len(chunks)
        results.append(
            {
                "source_id": source_id,
                "path": str(artifact_path),
                "chunk_count": len(chunks),
                "status": "success" if chunks else "empty",
            }
        )

    manifest = {
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(documents),
        "chunk_count": total_chunks,
        "max_chars": max_chars,
        "chunker_version": CHUNKER_VERSION,
        "results": results,
        "status": "success" if documents and all(
            result["status"] == "success" for result in results
        ) else "failed",
    }
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Chunk validated saved documents without network access."
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    args = parser.parse_args()
    if args.max_chars < 1:
        parser.error("--max-chars must be positive")

    try:
        sources = load_registry(args.registry)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2

    documents, loading_manifest = load_documents(sources, args.input)
    if not documents:
        print(
            "No valid documents are available for chunking; "
            f"loading status: {loading_manifest['status']}",
            file=sys.stderr,
        )
        return 1

    try:
        manifest = chunk_documents(documents, args.output, args.max_chars)
        if loading_manifest["status"] != "success":
            manifest["status"] = "partial"
            manifest["loading_manifest"] = {
                "status": loading_manifest["status"],
                "loaded": loading_manifest["loaded"],
                "skipped": loading_manifest["skipped"],
                "failed": loading_manifest["failed"],
            }
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        print(f"Unable to write chunk artifacts: {error}", file=sys.stderr)
        return 2

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
