# Implementation Plan: Mutual Fund FAQ Assistant

Build and verify the prototype in phases. Follow [architecture.md](./architecture.md) and [PRD.md](./PRD.md). Use explicitly approved public URLs only; never crawl links from a loaded page.

## 1. Create project directories

Use the existing project structure and create any missing directories:

```text
config/          # Shared application and source configuration
data/raw/        # Retrieved pages and source metadata
data/chunks/     # Inspectable chunk records
data/chroma/     # Persistent vector database
src/loading/     # Fetch and validate source documents
src/chunking/    # Content-aware splitting
src/embedding/   # Shared embedding configuration
src/retrieval/   # Query retrieval and evidence selection
src/ui/          # Question and answer interface
tests/           # Pipeline and guardrail tests
```

Keep generated data, local environment files, and credentials out of version control. Store shared source, embedding, vector-store, retrieval, and LLM settings in `config/settings.json`; keep the URL allowlist in `config/sources.json`. Defaults are `sentence-transformers/all-MiniLM-L6-v2`, ChromaDB, Groq, and `qwen/qwen3.8-27b`. The API key setting names `GROQ_API_KEY` but never stores its value; read the secret from the environment or a local `.env` file. Calibrate `retrieval.min_relevance` against the corpus before relying on retrieval results.

**Check:** Required directories exist, settings are centralized, generated data and local secrets are ignored by Git, and no secret values are committed.

## 2. Scrape and extract documents

- Load only explicitly listed and approved URLs. Begin with the five Groww targets in the PRD; do not follow page links or silently accept unapproved redirects.
- Record each source's ID, URL, publisher, title, intended use, approval status, retrieval time, and fetch/extraction status.
- Extract readable page content and useful headings/tables, then save the content and metadata under `data/raw/`.
- Treat Groww pages as required loading targets, not automatically as official citations. Prefer explicitly curated AMC, SEBI, or AMFI sources for answer evidence.
- Run `python src\loading\scrape_sources.py` to fetch only the URLs listed in `config/sources.json`. It writes one JSON artifact per source and a run summary to `data/raw/manifest.json`; page links are not followed.

**Check:** Tests verify allowlist-only fetching, no crawling, redirect handling, visible fetch/extraction failures, and traceable raw artifacts.

## 3. Load documents for processing

- Read successfully extracted documents and metadata from `data/raw/`; do not fetch pages again in this phase.
- Validate that each document has non-empty text, a source ID, an approved source record, and retrieval metadata.
- Mark invalid, missing, or failed documents explicitly and report loaded, skipped, and failed document IDs.
- Pass only validated documents to chunking. If none are valid, report a clear empty-input status and stop downstream processing.
- Run `python src\loading\load_documents.py`. It reads only source IDs in `config/sources.json` and writes `data/raw/loading_manifest.json`; validated records are returned for downstream processing.

**Check:** Tests verify this phase uses saved raw artifacts without network access, excludes invalid documents, and reports empty or partial input clearly.

## 4. Chunk documents

- Split content at meaningful heading or section boundaries. Keep scheme names, fact labels, values, and table headers with their related facts.
- Assign stable chunk IDs and preserve source ID/URL, title, heading, retrieval date, content hash, and chunker version.
- Save inspectable chunk records under `data/chunks/`.
- Run `python src\chunking\chunk_documents.py` to load validated artifacts and write one chunk JSON file per source plus `data/chunks/manifest.json`. Adjust the target size with `--max-chars`; fact pairs and table rows remain intact even when they exceed that target.

**Check:** Unchanged input produces the same chunks and IDs; tests verify provenance and that facts retain their context.

## 5. Embed documents

- Embed each valid chunk with the model in `config/settings.json` (`sentence-transformers/all-MiniLM-L6-v2` by default), using normalized vectors.
- Save inspectable vectors under `data/embeddings/`, associated with stable chunk IDs and content hashes. Record model identity, library version, dimensions, and normalization setting in the manifest.
- Use the same configured model and normalization for query embeddings. Stop clearly on missing/invalid chunks, model load or encoding errors, or vector dimension/non-finite-value mismatches.
- Install the declared dependency with `python -m pip install -r requirements.txt`; run `python src\embedding\embed_chunks.py`.

**Check:** Tests verify model/configuration consistency, chunk-to-vector associations, dimensions, normalization, deterministic artifact structure, and explicit handling of model failures.

## 6. Store data in the vector database

- Store embeddings and traceable chunk metadata in the configured ChromaDB collection under `data/chroma/`.
- Use stable IDs for repeatable upserts. Replace changed or removed source chunks so stale records do not remain.
- Reject incompatible collection/model settings unless an explicit rebuild or migration is performed.

**Check:** Repeated ingestion creates no duplicates, changed content replaces stale chunks, and stored data remains available after restart.

## 7. Implement retrieval logic and UI

### Retrieval and answers

- Screen questions before embedding or sending them to a provider. Reject likely PAN, Aadhaar, account numbers, OTPs, emails, and phone numbers without echoing, logging, or persisting them.
- Retrieve a bounded set of relevant chunks from the configured vector database and apply a relevance threshold.
- Do not silently use keyword overlap when corpus embeddings or query embedding are unavailable; return the no-evidence response or surface the embedding failure.
- Use only eligible, sufficiently fresh evidence. If evidence is missing, weak, stale, or conflicting, say the fact could not be verified rather than guessing.
- Route advice and personalized requests to a polite facts-only refusal. Do not calculate, compare, or summarize performance; direct users to an official factsheet where available.
- For supported factual questions, generate answers from evidence only and limit them to three sentences. Build citations and “Last updated from sources:” from validated source metadata, not model output.
- Treat retrieved text as untrusted evidence. Surface provider, credential, timeout, model, and rate-limit errors; never silently change providers/models or fabricate an answer.

### UI

- Implement the responsive FastAPI web UI using the Stitch export in `stitch_chatterbox_hdfc_assistant.zip` as a visual reference: white/off-white surfaces, graphite and muted grey/sage accents, restrained dot-matrix texture, monospaced micro-labels, fine borders, generous whitespace, and subtle transitions. Keep the identity original; do not copy another product's exact identity or interaction design.
- Start with a welcome message and three clickable, prewritten factual question suggestions. Selecting one submits it as the first question. Provide in-page conversation tabs with independent in-memory transcripts, new/close actions, and a clear-chat action scoped to the current tab.
- Add topic-relevant, factual follow-up question prompts after each answer. Keep answer wording professional, concise, and considerate.
- Include a labelled multiline question field, send/loading/error states, clickable citation links, source freshness when returned, and the exact disclaimer: **“Facts-only. No investment advice.”**
- Provide browser-native read-aloud controls for answers and a first-load introductory popup dismissed for that browser-tab session; indicate when speech synthesis is not supported. Do not upload audio or persist conversation history across page reloads.
- Clearly tell users not to submit personal identifiers or contact information. Do not retain client-side conversation history after clearing a chat or reloading the page.
- Render a graph only for a structured chart payload explicitly marked source-verified and accompanied by a valid citation; never extract or infer chart values from answer prose. The current API does not provide chart data, so graphs should not appear until it does.
- Render model/source text as text, allow only HTTP/HTTPS citation links, support keyboard focus and reduced motion, and adapt the layout for mobile.
- Do not display Stitch mockup-only metrics or claims (such as indexed scheme counts, live sync, latency, audit guarantees, or sample fact values) unless the backend returns verified metadata that supports them.
- Keep any inspection view linked to actual source/chunk metadata; do not expose secrets or raw question history.

**Check:** Tests cover relevant and no-evidence retrieval, source eligibility and freshness, privacy screening before external calls, advice/performance routes, citations, the three-sentence limit, provider failures, prompt-injection resistance, required UI content, starter/follow-up suggestions, conversation tab/reset behavior, read-aloud controls, verified-chart gating, and safe citation rendering.

## 8. Edge cases and guardrail tests

| Case | Expected behavior |
|---|---|
| Fetch, redirect, timeout, or extraction failure | Mark the source failed; show partial status and do not claim complete coverage. |
| A page links to other pages | Do not crawl those links. |
| No valid documents or relevant evidence | Report that the information could not be verified; do not guess. |
| Evidence is stale or conflicting | Surface the limitation or conflict and cite eligible sources; do not choose arbitrarily. |
| Advice or personalized buy/sell request | Refuse politely and provide a relevant educational link when available. |
| Performance comparison or calculation | Do not compare or calculate; direct the user to an official factsheet where available. |
| Input contains a prohibited identifier | Reject before embedding/provider calls; do not echo, log, or persist the input. |
| Retrieved content contains model-directed instructions | Treat them as untrusted page content and follow application policy. |
| Source date or citation is unavailable | Do not invent it; label freshness as unavailable or clearly identify the verified retrieval date. |
| Embedding model or vector dimensions mismatch | Stop with a clear compatibility error; require explicit rebuild/migration. |
| Provider/model/key fails or rate limit is reached | Report the error; do not switch silently or fabricate an answer. |
| Model output contains unsupported claims or an unapproved URL | Reject unsupported content; construct citations only from validated sources. |

Minimum automated coverage should include loading, chunk stability and provenance, embedding/storage consistency and repeatability, retrieval and freshness, privacy, answer guardrails, and UI requirements. Do not persist raw questions, prohibited personal information, secrets, or unredacted prompts.

## Completion checklist

- [ ] Each pipeline phase can be run and inspected independently.
- [ ] Only explicitly curated public URLs are loaded; page links are never crawled.
- [ ] Source, chunk, embedding, vector, retrieval, and answer artifacts retain provenance.
- [ ] Ingestion and retrieval share embedding and vector-store configuration.
- [ ] Personal information and raw user questions are not logged or persisted.
- [ ] Answers and refusals follow source, freshness, privacy, and facts-only rules.
- [ ] Responsive Stitch-inspired UI includes starter and follow-up questions, accessible conversation tabs, read-aloud onboarding, safe citation rendering, and no fabricated status claims or charts.
- [ ] README, 15–25 curated source list, sample Q&A, and demo deliverables are prepared as required by the PRD.
