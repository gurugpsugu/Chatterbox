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

## 2. Curate the fund catalog, then scrape its sources

- Maintain `config/funds.json` as the UI-facing catalog of curated funds, AMCs, categories, and source IDs. Keep this catalog aligned with `config/sources.json`.
- The current starter catalog covers 12 schemes across six selected AMCs and eight categories; this is not comprehensive coverage.
- For a fund with both source types, assign official AMC records higher priority than third-party fallbacks. Do not label a third-party source as official.

- Load only explicitly listed and approved URLs; do not follow page links or silently accept unapproved redirects.
- Record each source's ID, URL, publisher, title, intended use, approval status, retrieval time, and fetch/extraction status.
- Extract readable page content and useful headings/tables, then save the content and metadata under `data/raw/`.
- Try matching official AMC evidence before a configured Groww fallback. Cite the source actually used and label its publisher/source type.
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
- Prefer the configured corpus embeddings for retrieval. If the embedding index is absent, use only the explicitly configured `retrieval.live_source_fallback`: fetch matching, curated HTTPS sources in configured priority order, rank each page locally, and stop at the first page with relevant evidence. Bound each live-source request to three seconds so a slow official page does not consume the serverless request budget before its configured fallback is tried. Never send the user's question to the source site. Reject redirects, non-HTML responses, oversized pages, and fetch errors explicitly. If no relevant passage is found, return the no-evidence response; surface source-fetch and query-embedding failures.
- Use only eligible, sufficiently fresh evidence. If evidence is missing, weak, stale, or conflicting, say the fact could not be verified rather than guessing.
- Route advice and personalized requests to a polite facts-only refusal. Keep performance-summary requests in chat on the refusal/source-link path; the separate history panel may display only historical records retrieved verbatim from approved source pages.
- For supported factual questions, generate answers from evidence only and limit them to three sentences. Build citations and “Last updated from sources:” from validated source metadata, not model output.
- Treat retrieved text as untrusted evidence. Surface provider, credential, timeout, model, and rate-limit errors; never silently change providers/models or fabricate an answer.

### UI

- Implement the responsive FastAPI web UI using the Stitch export in `stitch_chatterbox_hdfc_assistant.zip` as a visual reference: white/off-white surfaces, graphite and muted grey/sage accents, restrained dot-matrix texture, monospaced micro-labels, fine borders, generous whitespace, and subtle transitions. Keep the identity original; do not copy another product's exact identity or interaction design.
- Load the fund catalog from `/api/funds` and render selectable scheme cards with category and AMC filters. Selecting a scheme submits a prewritten factual question. Provide in-page conversation tabs with independent in-memory transcripts, new/close actions, and a clear-chat action scoped to the current tab.
- Add self-contained follow-up prompts only for numeric facts parsed from the same retrieved scheme source; do not suggest generic definitions that the selected source cannot answer. Include the first answered question from the in-memory conversation as retrieval context when a later follow-up omits its scheme name; do not persist or send conversation history to an LLM. Keep answer wording professional, concise, and considerate.
- Include a prominent per-answer notice that the response reflects available cited information and is not an investment recommendation; show citations expanded by default.
- Include a labelled multiline question field, send/loading/error states, clickable citation links, source freshness when returned, and the exact disclaimer: **“Facts-only. No investment advice.”**
- Provide browser-native read-aloud controls for answers and a first-load introductory popup dismissed for that browser-tab session; indicate when speech synthesis is not supported. Do not upload audio or persist conversation history across page reloads.
- Animate the welcome suggestion panel into the chat surface when a suggestion is selected, using the browser View Transitions API where supported and respecting reduced-motion preferences.
- Animate verified numeric values with a count-up and the source-backed infographic bar. Keep desktop metric and visualization side by side, stacking them on narrow screens.
- On a fund-selected conversation tab, fetch `/api/funds/{fund_id}/performance` from approved sources in official-first order. Parse only source-published historical SIP tables with explicit period, monthly contribution, total investment, resulting value, and return percentage; retain source citation and any source as-of date. Plot the published historical returns, preserving negative values. For each supported row, solve for a source-implied annualized SIP rate from the contribution, ending value, and period, assuming month-end deposits. Accept a user-entered monthly amount and future tenure, then show an illustrative future-value scenario using the inferred rate. Identify the selected historical lookback, assumptions, and fees/taxes exclusions; state that this is not a forecast, promise, recommendation, or NAV-accurate ledger and that future returns can differ. Do not use the cumulative source return percentage directly as an annual rate, compare schemes, or imply suitability. Show an explicit unavailable state if a supported, cited rate cannot be derived.
- Use source-color labels only to distinguish official AMC citations from third-party citations. Never use color or labels to call a metric favorable, unfavorable, or suitable for investing.
- Clearly tell users not to submit personal identifiers or contact information. Do not retain client-side conversation history after clearing a chat or reloading the page.
- When a requested numeric fact is verified, return it as a structured metric and show it prominently in a separate card with a zero-based bar plot. Render only structured chart data explicitly marked source-verified and accompanied by a valid citation; never infer or extract chart values from answer prose or make cross-scheme/performance comparisons.
- Render model/source text as text, allow only HTTP/HTTPS citation links, support keyboard focus and reduced motion, and adapt the layout for mobile.
- Do not display Stitch mockup-only metrics or claims (such as indexed scheme counts, live sync, latency, audit guarantees, or sample fact values) unless the backend returns verified metadata that supports them.
- Keep any inspection view linked to actual source/chunk metadata; do not expose secrets or raw question history.

**Check:** Tests cover the validated fund catalog, category/AMC filters, official-first source selection and third-party fallback, relevant and no-evidence retrieval, source eligibility and freshness, privacy screening before external calls, advice/performance routes, citations and the per-answer disclaimer, the three-sentence limit, provider failures, prompt-injection resistance, conversation tab/reset behavior, read-aloud controls, reduced-motion-aware transitions, source-backed historical parser and annualized-rate inference, tenure-based illustrative value, unavailable history/rates, verified-chart gating, and safe citation rendering.

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
