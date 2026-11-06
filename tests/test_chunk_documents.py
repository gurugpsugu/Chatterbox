import json
import tempfile
import unittest
from pathlib import Path

from src.chunking.chunk_documents import chunk_document, chunk_documents
from src.loading.scrape_sources import DEFAULT_REGISTRY, load_registry


class ChunkDocumentsTests(unittest.TestCase):
    def setUp(self):
        self.source = load_registry(DEFAULT_REGISTRY)[1]
        self.document = {
            **self.source,
            "retrieved_at": "2026-11-05T07:47:57+00:00",
            "text": (
                "HDFC Large Cap Fund Direct Growth\n"
                "Minimum investments\n"
                "Min. for SIP\n"
                "₹100\n"
                "Fund size (AUM)\n"
                "₹37,293.95 Cr\n"
                "Expense ratio\n"
                "1.02%\n"
            ),
        }

    def test_chunks_are_deterministic_and_keep_source_provenance(self):
        first = chunk_document(self.document, max_chars=50)
        second = chunk_document(self.document, max_chars=50)
        self.assertEqual(first, second)
        self.assertTrue(all(chunk["source_id"] == self.source["source_id"] for chunk in first))
        self.assertTrue(all(chunk["url"] == self.source["url"] for chunk in first))
        self.assertTrue(all(chunk["retrieved_at"] == self.document["retrieved_at"] for chunk in first))
        self.assertEqual(len({chunk["chunk_id"] for chunk in first}), len(first))

    def test_keeps_fact_labels_and_values_together_and_retains_heading_path(self):
        chunks = chunk_document(self.document, max_chars=25)
        joined_text = "\n".join(chunk["text"] for chunk in chunks)
        self.assertIn("Min. for SIP: ₹100", joined_text)
        self.assertIn("Fund size (AUM): ₹37,293.95 Cr", joined_text)
        self.assertIn("Expense ratio: 1.02%", joined_text)
        self.assertTrue(
            any(chunk["heading_path"][-1] == "Minimum investments" for chunk in chunks)
        )

    def test_keeps_table_header_and_each_row_together(self):
        document = {
            **self.document,
            "text": (
                "HDFC Large Cap Fund Direct Growth\n"
                "Holdings (\n49\n)\n"
                "Name\nSector\nInstruments\nAssets\n"
                "ICICI Bank Ltd\nFinancial\nEquity\n9.79%\n"
                "HDFC Bank Ltd\nFinancial\nEquity\n7.36%\n"
                "See All\n"
            ),
        }
        chunks = chunk_document(document, max_chars=30)
        self.assertEqual(len(chunks), 2)
        for chunk in chunks:
            self.assertIn("Name | Sector | Instruments | Assets", chunk["text"])
        self.assertIn("ICICI Bank Ltd | Financial | Equity | 9.79%", chunks[0]["text"])
        self.assertIn("HDFC Bank Ltd | Financial | Equity | 7.36%", chunks[1]["text"])

    def test_persists_inspectable_chunk_artifact_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            manifest = chunk_documents([self.document], output_dir, max_chars=50)
            artifact_path = output_dir / f"{self.source['source_id']}.json"
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "success")
            self.assertEqual(artifact["chunk_count"], len(artifact["chunks"]))
            self.assertTrue(all("content_hash" in chunk for chunk in artifact["chunks"]))

    def test_rejects_invalid_chunk_size_and_missing_document_fields(self):
        with self.assertRaises(ValueError):
            chunk_document(self.document, max_chars=0)
        with self.assertRaises(ValueError):
            chunk_document({"source_id": self.source["source_id"]})


if __name__ == "__main__":
    unittest.main()
