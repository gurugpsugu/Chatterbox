"""Embed persisted chunks with the shared configured sentence-transformers model."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_SETTINGS = PROJECT_ROOT / "config" / "settings.json"
DEFAULT_INPUT = PROJECT_ROOT / "data" / "chunks"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "embeddings"
DEFAULT_MANIFEST = DEFAULT_OUTPUT / "manifest.json"


class SentenceTransformerModel(Protocol):
    def get_sentence_embedding_dimension(self) -> int | None: ...

    def encode(
        self,
        sentences: list[str],
        *,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> Any: ...


def load_settings(path: Path = DEFAULT_SETTINGS) -> dict[str, Any]:
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Unable to read settings file {path}: {error}") from error

    embedding_settings = settings.get("embedding") if isinstance(settings, dict) else None
    model_name = embedding_settings.get("model") if isinstance(embedding_settings, dict) else None
    normalize = (
        embedding_settings.get("normalize_embeddings", True)
        if isinstance(embedding_settings, dict)
        else None
    )
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("Settings must define a non-empty embedding.model")
    if not isinstance(normalize, bool):
        raise ValueError("Settings embedding.normalize_embeddings must be a boolean")
    return {
        "model": model_name,
        "normalize_embeddings": normalize,
    }


def create_model(model_name: str) -> tuple[SentenceTransformerModel, str]:
    try:
        import sentence_transformers
    except ImportError as error:
        raise RuntimeError(
            "sentence-transformers is required; install dependencies with "
            "`python -m pip install -r requirements.txt`"
        ) from error

    try:
        model = sentence_transformers.SentenceTransformer(model_name)
    except Exception as error:
        raise RuntimeError(
            f"Unable to load embedding model {model_name!r}: {error}"
        ) from error
    return model, sentence_transformers.__version__


def load_chunks(input_dir: Path) -> list[dict[str, Any]]:
    if not input_dir.is_dir():
        raise ValueError(f"Chunk directory does not exist: {input_dir}")

    chunks: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    artifact_paths = sorted(
        path for path in input_dir.glob("*.json") if path.name != "manifest.json"
    )
    if not artifact_paths:
        raise ValueError(f"No per-source chunk artifacts found in {input_dir}")

    for path in artifact_paths:
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Unable to read chunk artifact {path}: {error}") from error

        if not isinstance(artifact, dict) or not isinstance(artifact.get("chunks"), list):
            raise ValueError(f"Chunk artifact must contain a chunks list: {path}")
        source_id = artifact.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            raise ValueError(f"Chunk artifact has no valid source_id: {path}")

        for chunk in artifact["chunks"]:
            if not isinstance(chunk, dict):
                raise ValueError(f"Chunk record must be an object: {path}")
            required_fields = ("chunk_id", "source_id", "url", "text", "content_hash")
            if any(not isinstance(chunk.get(field), str) or not chunk[field].strip() for field in required_fields):
                raise ValueError(f"Chunk in {path} is missing required metadata or text")
            if chunk["source_id"] != source_id:
                raise ValueError(f"Chunk source_id does not match artifact {path}")
            if chunk["chunk_id"] in seen_ids:
                raise ValueError(f"Duplicate chunk_id: {chunk['chunk_id']}")
            actual_hash = hashlib.sha256(chunk["text"].encode("utf-8")).hexdigest()
            if chunk["content_hash"] != actual_hash:
                raise ValueError(f"Chunk content hash mismatch: {chunk['chunk_id']}")
            seen_ids.add(chunk["chunk_id"])
            chunks.append(chunk)

    if not chunks:
        raise ValueError("Chunk artifacts contain no chunks")
    return chunks


def embed_texts(
    texts: list[str],
    model_name: str,
    normalize_embeddings: bool = True,
    model: SentenceTransformerModel | None = None,
) -> tuple[list[list[float]], int, SentenceTransformerModel, str | None]:
    if not texts:
        raise ValueError("Cannot embed an empty text list")
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("Embedding inputs must be non-empty strings")

    library_version: str | None = None
    if model is None:
        model, library_version = create_model(model_name)
    try:
        encoded = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=normalize_embeddings,
            show_progress_bar=False,
        )
    except Exception as error:
        raise RuntimeError(f"Embedding failed for model {model_name!r}: {error}") from error

    vectors = encoded.tolist() if hasattr(encoded, "tolist") else encoded
    if not isinstance(vectors, (list, tuple)) or len(vectors) != len(texts):
        raise RuntimeError("Embedding model returned an unexpected number of vectors")

    dimensions: int | None = None
    validated_vectors: list[list[float]] = []
    for vector in vectors:
        if not isinstance(vector, (list, tuple)) or not vector:
            raise RuntimeError("Embedding model returned an empty or invalid vector")
        converted: list[float] = []
        for value in vector:
            try:
                numeric_value = float(value)
            except (TypeError, ValueError) as error:
                raise RuntimeError("Embedding vector contains a non-numeric value") from error
            if not math.isfinite(numeric_value):
                raise RuntimeError("Embedding vector contains a non-finite value")
            converted.append(numeric_value)
        if dimensions is None:
            dimensions = len(converted)
        elif len(converted) != dimensions:
            raise RuntimeError("Embedding model returned vectors with inconsistent dimensions")
        validated_vectors.append(converted)

    model_dimension = model.get_sentence_embedding_dimension()
    if model_dimension is not None and model_dimension != dimensions:
        raise RuntimeError(
            "Embedding dimension mismatch: model reports "
            f"{model_dimension}, returned vectors have {dimensions}"
        )
    assert dimensions is not None
    return validated_vectors, dimensions, model, library_version


def embed_chunks(
    chunks: list[dict[str, Any]],
    output_dir: Path,
    model_name: str,
    normalize_embeddings: bool = True,
    model: SentenceTransformerModel | None = None,
    library_version: str | None = None,
) -> dict[str, Any]:
    if not chunks:
        raise ValueError("No chunks are available for embedding")
    texts = [chunk["text"] for chunk in chunks]
    vectors, dimensions, loaded_model, detected_version = embed_texts(
        texts,
        model_name,
        normalize_embeddings,
        model,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    by_source: dict[str, list[dict[str, Any]]] = {}
    for chunk, vector in zip(chunks, vectors, strict=True):
        by_source.setdefault(chunk["source_id"], []).append(
            {
                "chunk_id": chunk["chunk_id"],
                "source_id": chunk["source_id"],
                "content_hash": chunk["content_hash"],
                "embedding": vector,
            }
        )

    results: list[dict[str, Any]] = []
    for source_id, records in sorted(by_source.items()):
        artifact_path = output_dir / f"{source_id}.json"
        artifact = {
            "source_id": source_id,
            "model": model_name,
            "dimensions": dimensions,
            "normalized": normalize_embeddings,
            "embeddings": records,
        }
        artifact_path.write_text(
            json.dumps(artifact, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        results.append(
            {
                "source_id": source_id,
                "path": str(artifact_path),
                "embedding_count": len(records),
                "status": "success",
            }
        )

    try:
        model_revision = getattr(loaded_model, "model_card_data", None)
        revision = getattr(model_revision, "base_model", None)
    except Exception:
        revision = None
    manifest = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "library": "sentence-transformers",
        "library_version": library_version or detected_version,
        "dimensions": dimensions,
        "normalized": normalize_embeddings,
        "chunk_count": len(chunks),
        "results": results,
        "status": "success",
    }
    if revision:
        manifest["model_base_model"] = str(revision)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def embed_query(
    query: str,
    model: SentenceTransformerModel | None = None,
) -> list[float]:
    """Embed a screened query using the corpus model from shared settings."""
    settings = load_settings()
    vectors, _, _, _ = embed_texts(
        [query],
        settings["model"],
        settings["normalize_embeddings"],
        model,
    )
    return vectors[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Embed persisted chunks using the configured sentence-transformers model."
    )
    parser.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()

    try:
        settings = load_settings(args.settings)
        chunks = load_chunks(args.input)
        model, library_version = create_model(settings["model"])
        manifest = embed_chunks(
            chunks,
            args.output,
            settings["model"],
            settings["normalize_embeddings"],
            model,
            library_version,
        )
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Embedding phase failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
