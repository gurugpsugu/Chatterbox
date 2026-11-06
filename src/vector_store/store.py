"""Persist and query chunk embeddings in the configured vector store."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Protocol

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_SETTINGS = PROJECT_ROOT / "config" / "settings.json"
DEFAULT_EMBEDDINGS_DIR = PROJECT_ROOT / "data" / "embeddings"
DEFAULT_CHUNKS_DIR = PROJECT_ROOT / "data" / "chunks"
DEFAULT_PERSIST_DIR = PROJECT_ROOT / "data" / "chroma"


class VectorStore(Protocol):
    provider: str
    collection_name: str

    def upsert(self, records: list[dict[str, Any]]) -> list[str]: ...

    def query(self, query_vector: list[float], top_k: int = 5) -> list[dict[str, Any]]: ...


class LocalJSONVectorStore:
    """Simple fallback that persists vectors and metadata as local JSON."""

    provider = "json"

    def __init__(self, persist_directory: str | Path, collection_name: str):
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.index_path = self.persist_directory / f"{collection_name}.json"
        self._index = self._read_index()

    def _read_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {"collection": self.collection_name, "records": []}
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"collection": self.collection_name, "records": []}
        if not isinstance(data, dict):
            return {"collection": self.collection_name, "records": []}
        records = data.get("records", [])
        if isinstance(records, list):
            return {"collection": self.collection_name, "records": records}
        return {"collection": self.collection_name, "records": []}

    def _write_index(self, index: dict[str, Any]) -> None:
        self.index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _normalise_vector(self, vector: Any) -> list[float]:
        if not isinstance(vector, list) or not vector:
            raise ValueError("Embedding vector must be a non-empty list of floats")
        values: list[float] = []
        for value in vector:
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError("Embedding vector contains a non-finite value")
            values.append(numeric)
        return values

    def _cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
        norm_a = math.sqrt(sum(value * value for value in vec_a))
        norm_b = math.sqrt(sum(value * value for value in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def upsert(self, records: list[dict[str, Any]]) -> list[str]:
        if not records:
            return []

        index = self._read_index()
        records_by_id: dict[str, dict[str, Any]] = {
            str(item.get("chunk_id")): item for item in index.get("records", []) if item.get("chunk_id")
        }

        for record in records:
            if not isinstance(record, dict):
                continue
            chunk_id = str(record.get("chunk_id") or "").strip()
            if not chunk_id:
                continue
            payload = dict(record)
            payload["chunk_id"] = chunk_id
            if isinstance(payload.get("embedding"), list):
                payload["embedding"] = self._normalise_vector(payload["embedding"])
            records_by_id[chunk_id] = payload

        index["collection"] = self.collection_name
        index["records"] = sorted(records_by_id.values(), key=lambda item: str(item.get("chunk_id")))
        self._write_index(index)
        self._index = index
        return [str(item.get("chunk_id")) for item in index["records"] if item.get("chunk_id")]

    def query(self, query_vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        if not query_vector:
            return []

        if not self._index.get("records"):
            return []

        normalized_query = self._normalise_vector(query_vector)
        scored: list[tuple[float, dict[str, Any]]] = []
        for record in self._index["records"]:
            embedding = record.get("embedding")
            if not isinstance(embedding, list):
                continue
            score = self._cosine_similarity(normalized_query, self._normalise_vector(embedding))
            scored.append((score, record))

        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[dict[str, Any]] = []
        for score, record in scored[: max(1, int(top_k))]:
            result = dict(record)
            result["score"] = float(score)
            result["distance"] = 1.0 - float(score)
            results.append(result)
        return results


class ChromaVectorStore:
    provider = "chromadb"

    def __init__(self, persist_directory: str | Path, collection_name: str):
        try:
            import chromadb  # type: ignore
        except ImportError as error:
            raise RuntimeError(
                "chromadb is required to use the configured vector store; "
                "install dependencies with `python -m pip install -r requirements.txt`"
            ) from error

        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, records: list[dict[str, Any]]) -> list[str]:
        if not records:
            return []

        ids: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, Any]] = []
        documents: list[str] = []

        for record in records:
            chunk_id = str(record.get("chunk_id") or "").strip()
            if not chunk_id:
                continue
            vector = record.get("embedding")
            if not isinstance(vector, list) or not vector:
                raise ValueError(f"Embedding for chunk {chunk_id!r} is missing or empty")
            ids.append(chunk_id)
            embeddings.append([float(value) for value in vector])
            documents.append(str(record.get("text") or ""))
            metadata = {
                "chunk_id": chunk_id,
                "source_id": str(record.get("source_id") or ""),
                "url": str(record.get("url") or ""),
                "title": str(record.get("title") or ""),
                "content_hash": str(record.get("content_hash") or ""),
                "retrieved_at": str(record.get("retrieved_at") or ""),
                "heading_path": json.dumps(record.get("heading_path") or []),
            }
            metadatas.append(metadata)

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )
        return ids

    def query(self, query_vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        if not query_vector:
            return []

        results = self.collection.query(
            query_embeddings=[list(query_vector)],
            n_results=max(1, int(top_k)),
            include=["documents", "metadatas", "distances"],
        )
        if not results or not results.get("ids"):
            return []

        ids = results["ids"][0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        output: list[dict[str, Any]] = []
        for index, chunk_id in enumerate(ids):
            metadata = metadatas[index] if index < len(metadatas) else {}
            document = documents[index] if index < len(documents) else ""
            distance = distances[index] if index < len(distances) else 1.0
            output.append(
                {
                    "chunk_id": chunk_id,
                    "text": document,
                    "source_id": metadata.get("source_id"),
                    "url": metadata.get("url"),
                    "title": metadata.get("title"),
                    "content_hash": metadata.get("content_hash"),
                    "retrieved_at": metadata.get("retrieved_at"),
                    "heading_path": json.loads(metadata.get("heading_path") or "[]"),
                    "distance": float(distance),
                    "score": max(0.0, 1.0 - float(distance)),
                }
            )
        return output


def load_settings(path: Path = DEFAULT_SETTINGS) -> dict[str, Any]:
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Unable to read settings file {path}: {error}") from error

    if not isinstance(settings, dict):
        raise ValueError("Project settings must be a JSON object")

    vector_settings = settings.get("vector_store")
    if not isinstance(vector_settings, dict):
        raise ValueError("Settings must define a vector_store object")

    provider = vector_settings.get("provider", "chromadb")
    persist_directory = vector_settings.get("persist_directory", str(DEFAULT_PERSIST_DIR))
    collection_name = vector_settings.get("collection")
    if not isinstance(collection_name, str) or not collection_name.strip():
        raise ValueError("Settings must define a non-empty vector_store.collection")
    if not isinstance(persist_directory, str) or not persist_directory.strip():
        raise ValueError("Settings must define a non-empty vector_store.persist_directory")

    return {
        "provider": provider,
        "persist_directory": persist_directory,
        "collection": collection_name,
    }


def create_vector_store(
    settings: dict[str, Any] | None = None,
    *,
    settings_path: Path = DEFAULT_SETTINGS,
) -> VectorStore:
    resolved_settings = settings or load_settings(settings_path)
    provider = str(resolved_settings.get("provider", "chromadb")).lower()
    persist_directory = resolved_settings.get("persist_directory", str(DEFAULT_PERSIST_DIR))
    collection_name = str(resolved_settings.get("collection") or "mutual_fund_faq")

    if provider in {"chromadb", "chroma"}:
        try:
            return ChromaVectorStore(persist_directory, collection_name)
        except RuntimeError:
            return LocalJSONVectorStore(persist_directory, collection_name)
    return LocalJSONVectorStore(persist_directory, collection_name)


def _load_chunk_lookup(chunks_dir: Path) -> dict[str, dict[str, Any]]:
    if not chunks_dir.exists():
        return {}

    lookup: dict[str, dict[str, Any]] = {}
    for path in sorted(chunks_dir.glob("*.json")):
        if path.name == "manifest.json":
            continue
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(artifact, dict):
            continue
        for chunk in artifact.get("chunks", []):
            if not isinstance(chunk, dict):
                continue
            chunk_id = chunk.get("chunk_id")
            if isinstance(chunk_id, str) and chunk_id.strip():
                lookup[chunk_id] = chunk
    return lookup


def load_embedding_records(
    *,
    embeddings_dir: Path = DEFAULT_EMBEDDINGS_DIR,
    chunks_dir: Path = DEFAULT_CHUNKS_DIR,
) -> list[dict[str, Any]]:
    if not embeddings_dir.exists():
        raise ValueError(f"Embedding directory does not exist: {embeddings_dir}")

    chunk_lookup = _load_chunk_lookup(chunks_dir)
    records: list[dict[str, Any]] = []
    for path in sorted(embeddings_dir.glob("*.json")):
        if path.name == "manifest.json":
            continue
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Unable to read embedding artifact {path}: {error}") from error
        if not isinstance(artifact, dict):
            continue
        for record in artifact.get("embeddings", []):
            if not isinstance(record, dict):
                continue
            chunk_id = record.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id.strip():
                continue
            source_chunk = chunk_lookup.get(chunk_id)
            if source_chunk is None:
                continue
            embedding = record.get("embedding")
            if not isinstance(embedding, list) or not embedding:
                continue
            records.append(
                {
                    "chunk_id": chunk_id,
                    "source_id": source_chunk.get("source_id"),
                    "title": source_chunk.get("title") or artifact.get("source_id"),
                    "url": source_chunk.get("url"),
                    "text": source_chunk.get("text"),
                    "content_hash": source_chunk.get("content_hash") or record.get("content_hash"),
                    "retrieved_at": source_chunk.get("retrieved_at"),
                    "heading_path": source_chunk.get("heading_path") or [],
                    "embedding": [float(value) for value in embedding],
                }
            )

    if not records:
        raise ValueError(f"No embedding records were found in {embeddings_dir}")
    return records


def store_embeddings(
    *,
    embeddings_dir: Path = DEFAULT_EMBEDDINGS_DIR,
    chunks_dir: Path = DEFAULT_CHUNKS_DIR,
    settings_path: Path = DEFAULT_SETTINGS,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_settings = settings or load_settings(settings_path)
    vector_store = create_vector_store(resolved_settings, settings_path=settings_path)
    records = load_embedding_records(embeddings_dir=embeddings_dir, chunks_dir=chunks_dir)
    stored_ids = vector_store.upsert(records)
    return {
        "provider": str(getattr(vector_store, "provider", resolved_settings.get("provider", "chromadb"))).lower(),
        "persist_directory": str(resolved_settings.get("persist_directory", str(DEFAULT_PERSIST_DIR))),
        "collection": str(resolved_settings.get("collection") or "mutual_fund_faq"),
        "stored_records": len(stored_ids),
        "ids": stored_ids,
        "status": "success",
    }


def query_collection(
    query_vector: Iterable[float],
    *,
    top_k: int = 5,
    settings_path: Path = DEFAULT_SETTINGS,
    settings: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    resolved_settings = settings or load_settings(settings_path)
    vector_store = create_vector_store(resolved_settings, settings_path=settings_path)
    return vector_store.query([float(value) for value in query_vector], top_k=max(1, int(top_k)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Store persisted embeddings in the configured vector database.")
    parser.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS)
    parser.add_argument("--embeddings-dir", type=Path, default=DEFAULT_EMBEDDINGS_DIR)
    parser.add_argument("--chunks-dir", type=Path, default=DEFAULT_CHUNKS_DIR)
    args = parser.parse_args()

    try:
        manifest = store_embeddings(
            embeddings_dir=args.embeddings_dir,
            chunks_dir=args.chunks_dir,
            settings_path=args.settings,
        )
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Vector storage failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
