"""Fetch and extract only the explicitly configured public source URLs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = PROJECT_ROOT / "config" / "sources.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "raw"
USER_AGENT = "ChatterboxPublicPageFetcher/1.0"
BLOCKED_TAGS = {"script", "style", "noscript", "svg", "nav", "footer"}
BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl",
    "dt", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "li", "main",
    "ol", "p", "section", "table", "tbody", "td", "th", "thead", "tr", "ul",
}


class PageTextExtractor(HTMLParser):
    """Extract visible page text without following or resolving hyperlinks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._blocked_depth = 0
        self._parts: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in BLOCKED_TAGS:
            self._blocked_depth += 1
            return
        if self._blocked_depth:
            return
        if tag == "title":
            self._in_title = True
        if tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in BLOCKED_TAGS and self._blocked_depth:
            self._blocked_depth -= 1
            return
        if self._blocked_depth:
            return
        if tag == "title":
            self._in_title = False
        if tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title:
            self.title = f"{self.title} {text}".strip()
        if not self._blocked_depth:
            self._parts.append(text)

    def get_text(self) -> str:
        lines = (" ".join(part.split()) for part in self._parts)
        return "\n".join(line for line in lines if line).strip()


def load_registry(path: Path) -> list[dict[str, Any]]:
    try:
        registry_data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Unable to read source registry {path}: {error}") from error

    sources = registry_data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Source registry must contain a non-empty 'sources' list")

    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("Every source registry entry must be an object")
        source_id = source.get("source_id")
        url = source.get("url")
        if not isinstance(source_id, str) or not re.fullmatch(r"[a-z0-9-]+", source_id):
            raise ValueError(f"Invalid source_id: {source_id!r}")
        if not isinstance(url, str) or not url.startswith("https://groww.in/mutual-funds/"):
            raise ValueError(f"Source {source_id} has a URL outside the approved Groww page scope")
        if source_id in seen_ids or url in seen_urls:
            raise ValueError(f"Duplicate source ID or URL: {source_id}")
        if not all(isinstance(source.get(field), str) and source[field].strip()
                   for field in ("title", "publisher", "source_type", "intended_use")):
            raise ValueError(f"Source {source_id} is missing required metadata")
        seen_ids.add(source_id)
        seen_urls.add(url)

    return sources


def scrape_source(source: dict[str, Any], timeout: float) -> dict[str, Any]:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    result: dict[str, Any] = {
        "source_id": source["source_id"],
        "url": source["url"],
        "publisher": source["publisher"],
        "title": source["title"],
        "source_type": source["source_type"],
        "intended_use": source["intended_use"],
        "retrieved_at": retrieved_at,
    }
    try:
        curl = shutil.which("curl.exe") or shutil.which("curl")
        if curl is None:
            result.update(status="failed", error="curl is required but was not found on PATH")
            return result
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "page.html"
            completed = subprocess.run(
                [
                    curl,
                    "--silent",
                    "--show-error",
                    "--proto",
                    "=https",
                    "--max-redirs",
                    "0",
                    "--max-time",
                    str(timeout),
                    "--user-agent",
                    USER_AGENT,
                    "--output",
                    str(output_path),
                    "--write-out",
                    "%{http_code}\t%{content_type}",
                    source["url"],
                ],
                capture_output=True,
                check=False,
                timeout=timeout + 5,
            )
            if completed.returncode != 0:
                error = completed.stderr.decode("utf-8", errors="replace").strip()
                result.update(status="failed", error=f"Fetch failed: {error or 'curl exited unsuccessfully'}")
                return result
            metadata = completed.stdout.decode("utf-8", errors="replace").strip()
            status_text, separator, content_type = metadata.partition("\t")
            if not separator or not status_text.isdigit():
                result.update(status="failed", error="Fetcher returned invalid HTTP metadata")
                return result
            if not 200 <= int(status_text) < 300:
                result.update(status="failed", error=f"HTTP {status_text}; redirects are not followed")
                return result
            content_type = content_type.split(";", maxsplit=1)[0].strip().lower()
            if content_type not in {"text/html", "application/xhtml+xml"}:
                result.update(status="failed", error=f"Unexpected content type: {content_type}")
                return result
            html = output_path.read_bytes().decode("utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired) as error:
        result.update(status="failed", error=f"Fetch failed: {error}")
        return result

    extractor = PageTextExtractor()
    extractor.feed(html)
    extractor.close()
    text = extractor.get_text()
    if not text:
        result.update(status="failed", error="No readable HTML text was extracted")
        return result

    result.update(
        status="success",
        page_title=extractor.title or source["title"],
        content_type=content_type,
        content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        text=text,
    )
    return result


def run_scrape(
    sources: list[dict[str, Any]],
    output_dir: Path,
    timeout: float = 20.0,
    delay: float = 0.5,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "requested_source_count": len(sources),
        "results": [],
    }

    for index, source in enumerate(sources):
        result = scrape_source(source, timeout)
        output_path = output_dir / f"{source['source_id']}.json"
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        manifest["results"].append(
            {
                "source_id": source["source_id"],
                "url": source["url"],
                "status": result["status"],
                "path": str(output_path),
                **({"error": result["error"]} if "error" in result else {}),
            }
        )
        if index + 1 < len(sources) and delay > 0:
            time.sleep(delay)

    successful = sum(result["status"] == "success" for result in manifest["results"])
    manifest.update(
        completed_at=datetime.now(timezone.utc).isoformat(),
        succeeded=successful,
        failed=len(sources) - successful,
        status="success" if successful == len(sources) else "partial" if successful else "failed",
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch only URLs in the approved source registry.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()
    if args.timeout <= 0 or args.delay < 0:
        parser.error("--timeout must be positive and --delay cannot be negative")

    try:
        sources = load_registry(args.registry)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    manifest = run_scrape(sources, args.output, args.timeout, args.delay)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
