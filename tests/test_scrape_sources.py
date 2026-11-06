import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from src.loading.scrape_sources import (
    DEFAULT_REGISTRY,
    PageTextExtractor,
    load_registry,
    run_scrape,
    scrape_source,
)


class ScrapeSourcesTests(unittest.TestCase):
    def test_registry_contains_only_the_five_explicit_targets(self):
        sources = load_registry(DEFAULT_REGISTRY)
        self.assertEqual(len(sources), 5)
        self.assertTrue(all(source["url"].startswith("https://groww.in/mutual-funds/") for source in sources))

    def test_extractor_ignores_scripts_and_does_not_resolve_links(self):
        parser = PageTextExtractor()
        parser.feed(
            "<html><title>Page title</title><body><h1>Fund facts</h1>"
            "<a href='/internal'>Expense ratio: 0.5%</a>"
            "<script>secret = 'not visible'</script></body></html>"
        )
        self.assertIn("Expense ratio: 0.5%", parser.get_text())
        self.assertNotIn("not visible", parser.get_text())
        self.assertNotIn("/internal", parser.get_text())
        self.assertEqual(parser.title, "Page title")

    def test_scraper_requests_only_the_configured_url(self):
        source = load_registry(DEFAULT_REGISTRY)[0]

        def fake_curl(args, **kwargs):
            output_path = Path(args[args.index("--output") + 1])
            output_path.write_bytes(b"<html><body><p>AMC overview</p></body></html>")
            return CompletedProcess(args, 0, stdout=b"200\ttext/html", stderr=b"")

        with patch("src.loading.scrape_sources.shutil.which", return_value="curl.exe"):
            with patch("src.loading.scrape_sources.subprocess.run", side_effect=fake_curl) as run:
                result = scrape_source(source, timeout=1)
        run.assert_called_once()
        args = run.call_args.args[0]
        self.assertEqual(args[-1], source["url"])
        self.assertIn("--max-redirs", args)
        self.assertEqual(args[args.index("--max-redirs") + 1], "0")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["text"], "AMC overview")

    def test_scraper_does_not_follow_redirects(self):
        source = load_registry(DEFAULT_REGISTRY)[0]

        def fake_curl(args, **kwargs):
            return CompletedProcess(args, 0, stdout=b"301\ttext/html", stderr=b"")

        with patch("src.loading.scrape_sources.shutil.which", return_value="curl.exe"):
            with patch("src.loading.scrape_sources.subprocess.run", side_effect=fake_curl):
                result = scrape_source(source, timeout=1)
        self.assertEqual(result["status"], "failed")
        self.assertIn("redirects are not followed", result["error"])

    def test_manifest_reports_per_source_failures(self):
        source = load_registry(DEFAULT_REGISTRY)[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "src.loading.scrape_sources.scrape_source",
                return_value={"source_id": source["source_id"], "url": source["url"], "status": "failed",
                              "error": "test failure"},
            ):
                manifest = run_scrape([source], Path(temp_dir), delay=0)
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["failed"], 1)
            saved = json.loads((Path(temp_dir) / f"{source['source_id']}.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "failed")
            self.assertTrue((Path(temp_dir) / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
