import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.loading.load_documents import load_documents, validate_artifact
from src.loading.scrape_sources import DEFAULT_REGISTRY, load_registry


class LoadDocumentsTests(unittest.TestCase):
    def setUp(self):
        self.sources = load_registry(DEFAULT_REGISTRY)
        self.source = self.sources[0]
        self.artifact = {
            **self.source,
            "retrieved_at": "2026-11-05T07:47:57+00:00",
            "status": "success",
            "text": "HDFC Mutual Fund overview",
        }

    def test_validates_successful_artifact_and_registry_provenance(self):
        document, error = validate_artifact(self.artifact, self.source)
        self.assertIsNone(error)
        self.assertEqual(document["source_id"], self.source["source_id"])

    def test_rejects_artifact_with_mismatched_url(self):
        artifact = {**self.artifact, "url": "https://example.com/other"}
        document, error = validate_artifact(artifact, self.source)
        self.assertIsNone(document)
        self.assertIn("does not match the source registry", error)

    def test_rejects_empty_text_and_bad_retrieval_timestamp(self):
        empty_document, empty_error = validate_artifact(
            {**self.artifact, "text": "  "},
            self.source,
        )
        bad_date_document, bad_date_error = validate_artifact(
            {**self.artifact, "retrieved_at": "yesterday"},
            self.source,
        )
        self.assertIsNone(empty_document)
        self.assertIn("text is empty", empty_error)
        self.assertIsNone(bad_date_document)
        self.assertIn("ISO 8601", bad_date_error)

    def test_rejects_content_hash_mismatch(self):
        document, error = validate_artifact(
            {**self.artifact, "content_sha256": "0" * 64},
            self.source,
        )
        self.assertIsNone(document)
        self.assertIn("does not match", error)

    def test_loading_reads_only_registry_artifacts_and_reports_missing_or_invalid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir)
            valid_source = self.sources[0]
            invalid_source = self.sources[1]
            (input_dir / f"{valid_source['source_id']}.json").write_text(
                json.dumps({**self.artifact, "source_id": valid_source["source_id"]}),
                encoding="utf-8",
            )
            (input_dir / f"{invalid_source['source_id']}.json").write_text(
                "{invalid json",
                encoding="utf-8",
            )
            (input_dir / "unregistered-source.json").write_text(
                json.dumps(self.artifact),
                encoding="utf-8",
            )

            with patch("src.loading.load_documents.json.loads", wraps=json.loads) as loads:
                documents, manifest = load_documents(self.sources[:2], input_dir)

            self.assertEqual(len(documents), 1)
            self.assertEqual(manifest["loaded_document_ids"], [valid_source["source_id"]])
            self.assertEqual(manifest["failed_document_ids"], [invalid_source["source_id"]])
            self.assertEqual(manifest["skipped_document_ids"], [])
            self.assertEqual(manifest["status"], "partial")
            self.assertEqual(loads.call_count, 2)

    def test_missing_and_failed_fetches_are_skipped_with_no_documents_status_failed(self):
        failed_source = self.sources[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir)
            (input_dir / f"{failed_source['source_id']}.json").write_text(
                json.dumps({**self.artifact, "status": "failed"}),
                encoding="utf-8",
            )
            documents, manifest = load_documents(self.sources[:2], input_dir)

        self.assertEqual(documents, [])
        self.assertEqual(
            manifest["skipped_document_ids"],
            [failed_source["source_id"], self.sources[1]["source_id"]],
        )
        self.assertEqual(manifest["status"], "failed")

    def test_loading_makes_no_network_requests(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("urllib.request.urlopen", side_effect=AssertionError("network used")):
                documents, manifest = load_documents(self.sources, Path(temp_dir))
        self.assertEqual(documents, [])
        self.assertEqual(manifest["requested_source_count"], len(self.sources))


if __name__ == "__main__":
    unittest.main()
