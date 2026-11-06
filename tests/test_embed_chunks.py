import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.embedding.embed_chunks import (
    embed_chunks,
    embed_query,
    embed_texts,
    load_chunks,
    load_settings,
)


class FakeModel:
    def __init__(self, dimension=3, vectors=None):
        self.dimension = dimension
        self.vectors = vectors
        self.calls = []

    def get_sentence_embedding_dimension(self):
        return self.dimension

    def encode(
        self,
        sentences,
        *,
        convert_to_numpy,
        normalize_embeddings,
        show_progress_bar,
    ):
        self.calls.append(
            {
                "sentences": sentences,
                "convert_to_numpy": convert_to_numpy,
                "normalize_embeddings": normalize_embeddings,
                "show_progress_bar": show_progress_bar,
            }
        )
        return self.vectors or [[0.1, 0.2, 0.3] for _ in sentences]


def make_chunk(chunk_id="source-1", source_id="source", text="Fund expense ratio"):
    return {
        "chunk_id": chunk_id,
        "source_id": source_id,
        "url": "https://example.com/fund",
        "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text": text,
    }


class EmbedChunksTests(unittest.TestCase):
    def test_loads_shared_embedding_configuration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text(
                json.dumps(
                    {
                        "embedding": {
                            "model": "example/model",
                            "normalize_embeddings": False,
                        }
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                load_settings(settings_path),
                {"model": "example/model", "normalize_embeddings": False},
            )

    def test_validates_chunk_artifacts_and_hashes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir)
            chunk = make_chunk()
            (input_dir / "source.json").write_text(
                json.dumps({"source_id": "source", "chunks": [chunk]}),
                encoding="utf-8",
            )
            self.assertEqual(load_chunks(input_dir), [chunk])
            chunk["content_hash"] = "invalid"
            (input_dir / "source.json").write_text(
                json.dumps({"source_id": "source", "chunks": [chunk]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "content hash mismatch"):
                load_chunks(input_dir)

    def test_encodes_vectors_with_normalization_and_dimension_validation(self):
        model = FakeModel()
        vectors, dimensions, _, _ = embed_texts(
            ["Fund expense ratio"],
            "example/model",
            normalize_embeddings=True,
            model=model,
        )
        self.assertEqual(vectors, [[0.1, 0.2, 0.3]])
        self.assertEqual(dimensions, 3)
        self.assertTrue(model.calls[0]["normalize_embeddings"])

    def test_rejects_mismatched_nonfinite_and_empty_vectors(self):
        with self.assertRaisesRegex(RuntimeError, "dimension mismatch"):
            embed_texts(["text"], "model", model=FakeModel(dimension=2))
        with self.assertRaisesRegex(RuntimeError, "non-finite"):
            embed_texts(
                ["text"],
                "model",
                model=FakeModel(vectors=[[float("nan"), 0.2, 0.3]]),
            )
        with self.assertRaisesRegex(ValueError, "empty text list"):
            embed_texts([], "model", model=FakeModel())

    def test_persists_embeddings_and_model_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            chunks = [make_chunk(), make_chunk("source-2", text="Fund minimum SIP")]
            manifest = embed_chunks(
                chunks,
                Path(temp_dir),
                "example/model",
                model=FakeModel(),
                library_version="test",
            )
            artifact = json.loads(
                (Path(temp_dir) / "source.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["chunk_count"], 2)
            self.assertEqual(manifest["dimensions"], 3)
            self.assertEqual(artifact["model"], "example/model")
            self.assertEqual(
                [record["chunk_id"] for record in artifact["embeddings"]],
                ["source-1", "source-2"],
            )
            self.assertEqual(artifact["embeddings"][0]["content_hash"], chunks[0]["content_hash"])

    def test_query_embedding_uses_the_same_shared_model_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text(
                json.dumps({"embedding": {"model": "shared/model"}}),
                encoding="utf-8",
            )
            model = FakeModel()
            from unittest.mock import patch

            with patch("src.embedding.embed_chunks.DEFAULT_SETTINGS", settings_path):
                vector = embed_query("What is the expense ratio?", model=model)
            self.assertEqual(vector, [0.1, 0.2, 0.3])
            self.assertEqual(model.calls[0]["sentences"], ["What is the expense ratio?"])


if __name__ == "__main__":
    unittest.main()
