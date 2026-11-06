"""Validate scraped source artifacts and prepare them for chunking."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.loading.scrape_sources import DEFAULT_REGISTRY, load_registry


DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw"
DEFAULT_MANIFEST = DEFAULT_INPUT / "loading_manifest.json"
REQUIRED_ARTIFACT_FIELDS = (
    "source_id",
    "url",
    "publisher",
    "title",
    "source_type",
    "intended_use",
    "retrieved_at",
    "status",
    "text",
)
REGISTRY_MATCH_FIELDS = (
    "source_id",
    "url",
    "publisher",
    "title",
    "source_type",
    "intended_use",
)


def validate_artifact(
    artifact: Any,
    source: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(artifact, dict):
        return None, "Artifact root must be a JSON object"

    missing_fields = [
        field for field in REQUIRED_ARTIFACT_FIELDS
        if field not in artifact
    ]
    if missing_fields:
        return None, f"Missing required fields: {', '.join(missing_fields)}"

    for field in REGISTRY_MATCH_FIELDS:
        if artifact[field] != source[field]:
            return None, f"Artifact {field} does not match the source registry"

    if artifact["status"] != "success":
        return None, f"Fetch status is {artifact['status']!r}"

    text = artifact["text"]
    if not isinstance(text, str) or not text.strip():
        return None, "Extracted text is empty or invalid"

    retrieved_at = artifact["retrieved_at"]
    if not isinstance(retrieved_at, str):
        return None, "Retrieval timestamp is missing or invalid"
    try:
        datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
    except ValueError:
        return None, "Retrieval timestamp is not valid ISO 8601"

    content_hash = artifact.get("content_sha256")
    if content_hash is not None:
        if not isinstance(content_hash, str):
            return None, "Content hash is invalid"
        actual_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if content_hash != actual_hash:
            return None, "Content hash does not match extracted text"

    return artifact, None


def load_documents(
    sources: list[dict[str, Any]],
    input_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    started_at = datetime.now(timezone.utc).isoformat()
    documents: list[dict[str, Any]] = []
    results: list[dict[str, str]] = []

    for source in sources:
        source_id = source["source_id"]
        artifact_path = input_dir / f"{source_id}.json"
        result = {
            "source_id": source_id,
            "path": str(artifact_path),
        }

        if not artifact_path.is_file():
            result.update(status="skipped", reason="Raw artifact is missing")
            results.append(result)
            continue

        try:
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            result.update(status="failed", reason=f"Invalid JSON: {error}")
            results.append(result)
            continue
        except OSError as error:
            result.update(status="failed", reason=f"Unable to read artifact: {error}")
            results.append(result)
            continue

        document, validation_error = validate_artifact(artifact, source)
        if validation_error:
            result.update(status="skipped", reason=validation_error)
            results.append(result)
            continue

        documents.append(document)
        result["status"] = "loaded"
        results.append(result)

    loaded_ids = [item["source_id"] for item in results if item["status"] == "loaded"]
    skipped_ids = [item["source_id"] for item in results if item["status"] == "skipped"]
    failed_ids = [item["source_id"] for item in results if item["status"] == "failed"]
    if not loaded_ids:
        status = "failed"
    elif skipped_ids or failed_ids:
        status = "partial"
    else:
        status = "success"

    manifest = {
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "requested_source_count": len(sources),
        "loaded": len(loaded_ids),
        "skipped": len(skipped_ids),
        "failed": len(failed_ids),
        "loaded_document_ids": loaded_ids,
        "skipped_document_ids": skipped_ids,
        "failed_document_ids": failed_ids,
        "results": results,
        "status": status,
    }
    return documents, manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load and validate saved raw documents without network access."
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()

    try:
        sources = load_registry(args.registry)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2

    documents, manifest = load_documents(sources, args.input)
    try:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        print(f"Unable to write loading manifest {args.manifest}: {error}", file=sys.stderr)
        return 2

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "success" and documents else 1


if __name__ == "__main__":
    raise SystemExit(main())
