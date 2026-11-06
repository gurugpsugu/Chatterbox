# Architecture: Mutual Fund FAQ Assistant

## 1. Purpose and scope

This document describes a small, inspectable RAG prototype for factual questions about HDFC Mutual Fund and a limited set of HDFC schemes. It follows the requirements in [PRD.md](./PRD.md): public sources, evidence-backed answers with citations, no investment advice, no personal data, and visible artifacts for every RAG phase.

The design is intentionally suitable for a local demo or notebook first. It does not include account integrations, user identity, personalized recommendations, or production financial workflows.

## 2. Architecture principles

- **Evidence before generation:** The language model may phrase retrieved facts, but it does not serve as a source of truth.
- **Provenance throughout:** Every extracted document, chunk, retrieved passage, and citation retains its source identity and freshness metadata.
- **Explicit source allowlist:** Ingestion is driven by curated URLs. It never discovers or follows links from fetched pages.
- **Inspectable stages:** Persist non-sensitive artifacts and expose their relationships for the demo.
- **One configuration path:** Ingestion and retrieval resolve the same embedding and vector-store settings.
- **Fail visibly:** Fetch, parsing, embedding, retrieval, and provider errors are reported; the system does not silently substitute sources, models, or answer content.
- **Data minimization:** User questions are transient. No personal data is requested, logged, or persisted.

## 3. Logical component diagram

```text
                         Curated source registry
                                   |
                                   v
 Public pages --> Loader --> Extractor --> Chunker --> Embedder
       |                                         |          |
       |                                         v          v
       +---------------- provenance --------> Artifact store / ChromaDB
                                                          ^
                                                          | retrieve
 User --> Minimal UI --> Input safety gate --> Query embedder
                                   |                      |
                                   |                      v
                                   |               Evidence assembler
                                   |                      |
                                   |                      v
                                   +--------------> Policy / answer router
                                                          |
                              advice/refusal <------------+----------> LLM adapter
                                  |                                      |
                                  +------------------+-------------------+
                                                     v
                                           Answer + citation + freshness
                                                     |
                                                     v
                                           UI and demo inspection view
```

The artifact store may be a local directory or a small database appropriate to the implementation. ChromaDB is the default vector store. The diagram does not require a separate production database or hosting service.

## 4. Components and responsibilities

### 4.1 Curated source registry

Maintains the approved source records used by ingestion. Each record includes:

- Stable source ID, canonical URL, publisher, page title, and page type.
- Approval/status and intended use (for example, scheme facts, statement help, or educational refusal link).
- Last-checked timestamp and, when available, the page's own effective/as-of date.
- Source policy classification (official AMC, SEBI, AMFI, or required Groww target).

The registry is an explicit list, not a crawler frontier. The five Groww targets in the PRD are required initial loading targets but are not official AMC/SEBI/AMFI pages. Until the source-policy question is resolved, do not treat them as authoritative citations. Curate additional official sources explicitly and use the authoritative source for answer evidence where available.

### 4.2 Loader and extractor

- Fetches only registry entries that are approved for loading.
- Does not follow page links, redirects to unapproved destinations, or embedded navigation targets. Redirect handling should be restricted to a validated final host/URL and reported.
- Extracts readable page text and useful structure such as title, headings, tables, and timestamps.
- Stores the original URL, resolved URL, retrieval time, extraction status, and extracted content.
- Produces an explicit error/status artifact when fetching or extraction fails.

Respect applicable site terms, rate limits, and access controls. This component must not access app backends or private endpoints.

### 4.3 Chunker

Creates content-aware chunks, preferably keeping a heading and its associated fact/table content together. Avoid splitting a value from its label or scheme context. Chunk size and overlap should be configurable only as needed for the selected embedding and corpus.

Each chunk has a stable ID and retains source ID, URL, title, section/heading path, and source timestamps. Chunking should be deterministic for unchanged input and configuration so that artifacts can be compared between runs.

### 4.4 Embedder

Embeds chunk text with the configured model. Default: `sentence-transformers/all-MiniLM-L6-v2`.

The resolved model identifier and version/revision when available are recorded with the ingestion run. Query embeddings must use the same configured model and compatible preprocessing as corpus embeddings. Model load and dimension errors are surfaced and stop the affected pipeline stage.

### 4.5 Artifact store and vector store

The artifact store retains inspectable source, extraction, chunk, run, and retrieval metadata. It should avoid storing raw user questions or any prohibited personal information.

ChromaDB is the default vector store. It stores embeddings and chunk metadata sufficient to trace a result to its source. Collection name, persistence location, and embedding configuration come from the shared configuration. Re-ingestion should have a documented strategy for updating or replacing records and removing stale chunks without leaving duplicate results.

### 4.6 Query and input safety gate

The UI sends a question to a server-side gate before embedding or model use. The gate:

- Rejects empty or clearly unsupported requests with a user-safe message.
- Detects likely PAN, Aadhaar, account-number, OTP, email, or phone-number input and rejects it before retrieval or external provider calls.
- Does not echo sensitive input in error text, application logs, traces, or stored artifacts.
- Does not persist the raw question. Operational diagnostics should use request IDs and non-sensitive status metadata only.

Detection is a defense-in-depth measure, not a guarantee of identifying every possible personal identifier. The UI should also clearly instruct users not to submit personal information.

### 4.7 Retriever and evidence assembler

- Embeds the accepted question using the shared ingestion embedding configuration.
- Queries the configured vector store for relevant chunks.
- Applies a configurable relevance threshold or no-evidence rule; it must not force a low-quality match to appear relevant.
- Does not substitute lexical overlap for vector retrieval when embeddings or query embedding are unavailable; return no evidence or surface the embedding error instead.
- Assembles a bounded evidence packet containing chunk text, source identity, citation URL, and freshness metadata.
- Makes retrieved chunk IDs and scores inspectable without retaining the raw user question.

When evidence is missing, stale, contradictory, or not from an allowed source, the answer path must say it could not verify the requested fact rather than infer an answer.

### 4.8 Policy and answer router

Classifies the request into a small set of behaviors:

1. **Supported factual request:** Continue only with relevant retrieved evidence.
2. **Advice/personalized request:** Do not call the model for substantive advice; return a polite facts-only refusal and a relevant educational link.
3. **Performance request:** Do not calculate, compare, or summarize performance; direct the user to an official factsheet.
4. **Unsupported or no-evidence request:** State that the available sources do not verify the fact and provide a relevant source link when available.

Refusal and no-evidence paths must also include a citation link and source freshness indicator where a relevant source exists. If no relevant source exists, do not invent a URL; report the missing source clearly and surface the limitation to the user.

### 4.9 LLM adapter

The adapter separates application logic from provider-specific clients. It supports configuration for Groq, Gemini, OpenAI, Anthropic, and Mistral where an implementation and valid credentials are available. Initial settings use Groq and the requested model identifier `qwen/qwen3.8-27b`, subject to provider availability.

The adapter:

- Receives only the minimum question and evidence needed to answer, after the input safety gate.
- Uses an instruction template that treats retrieved text as untrusted data, not executable instructions.
- Requires a concise response of at most three sentences, factual claims supported by supplied evidence, and no advice.
- Does not ask the model to invent citations or freshness dates. The application constructs citations and freshness metadata from source records.
- Surfaces provider, credential, rate-limit, timeout, and model errors. It never silently switches providers or models.

### 4.10 Presentation layer

The Vercel-compatible web UI is served by the FastAPI app and calls the same server-side `/api/chat` path as the query flow. The UI direction is based on the Stitch design export in `stitch_chatterbox_hdfc_assistant.zip`: a restrained white/off-white surface, graphite typography, muted grey/sage accents, a subtle dot-matrix motif, monospaced micro-labels, and quiet transitions. This is a visual reference, not a source for factual product claims or an exact reproduction of another product's identity.

The initial screen provides a welcome message, three selectable question suggestions, the required disclaimer **“Facts-only. No investment advice.”**, a privacy reminder, and a labelled question form. Selecting a suggestion submits that question. Users can create, switch, and close in-memory conversation tabs; each tab has its own pending request and transcript, and clearing a chat affects only that tab. Conversation history is not persisted across reloads.

Answers use concise, professional, considerate wording and include self-contained follow-up prompts only for numeric facts parsed from the same retrieved scheme source. Follow-ups are not generic definitions or claims that the current evidence cannot answer. The UI may send the first answered question in the current in-memory conversation as context for a follow-up that omits its scheme name; this context is neither persisted nor sent to an LLM. When a requested numeric fact is verified, `/api/chat` returns a structured metric and a single-value chart payload; the UI presents the number in its own prominent card alongside a zero-based bar plot, with the source citation and retrieval timestamp. It does not construct cross-scheme or performance comparisons. Selecting a welcome suggestion transitions the suggestion panel into the chat surface using the browser View Transitions API when available, with reduced-motion support. Each answer has a browser-native read-aloud control; a first-load dialog introduces it once per browser-tab session, and browsers without speech synthesis show the control as unavailable. Speech is generated locally by the browser.

The configured retrieval path uses the persisted embedding index when available. When it is absent, `retrieval.live_source_fallback` explicitly enables a bounded, read-only fetch from one matching URL in the curated registry. The question itself is never sent to that source; the application extracts a relevant passage locally, cites the registry URL, and records the fetch time. Redirects, non-HTML responses, oversized pages, and fetch failures are rejected rather than silently treated as evidence. Disable this option to require the persisted vector index.

The UI must not display fabricated scheme counts, synchronization states, performance figures, latency claims, audit/compliance guarantees, or source details absent from the returned answer metadata. It must not infer that a citation is official merely because it is presented as a link. Citation URLs are rendered as links only when they use HTTP or HTTPS, and answer text is inserted as text rather than interpreted as markup. Motion is brief and restrained, with reduced-motion support and visible keyboard focus.

The demo/inspection view should make the source, extracted text, chunk, embedding/model metadata, vector-store record, retrieved evidence, and final answer relationship easy to follow. It should not expose secrets, prohibited personal information, or unnecessary user-input history.

## 5. End-to-end flows

### 5.1 Ingestion flow

1. Load approved source records from the explicit registry.
2. Fetch each permitted page without crawling its links.
3. Extract content and write a source artifact containing provenance, timestamp, status, and content.
4. Chunk extracted content and persist each chunk with stable provenance.
5. Embed chunks using the configured model.
6. Upsert embeddings and metadata into the configured ChromaDB collection.
7. Record a run summary: configuration identity, counts by stage, timestamps, and explicit failures.

Stages should be independently runnable and inspectable. A failed stage must not be recorded as successful merely because an earlier stage completed.

### 5.2 Query flow

1. Receive a question in memory and run the input safety gate.
2. Route advice/performance requests to a safe refusal/redirect path.
3. For factual requests, embed the question with the ingestion model and retrieve candidate chunks from the configured vector store.
4. Validate evidence relevance, source policy, and freshness; assemble source-linked evidence.
5. If evidence is adequate, send the minimum required content to the configured LLM adapter. Otherwise, produce a no-evidence response.
6. Attach citation URL(s) and “Last updated from sources:” from the source records, not from model output.
7. Return the response. Persist only non-sensitive inspection metadata; do not persist the raw question or answer if it could contain user-provided personal data.

## 6. Data contracts

Illustrative logical schemas; exact serialization is implementation-dependent.

### Source record

| Field | Purpose |
|---|---|
| `source_id` | Stable identifier for a curated URL |
| `url` | Canonical approved public URL |
| `publisher`, `title`, `source_type` | Attribution and source-policy checks |
| `intended_use`, `approval_status` | Scope and evidence eligibility |
| `retrieved_at` | When this system fetched the page |
| `source_updated_at` | Page-provided date, if verifiable |
| `status`, `error` | Explicit fetch/extraction result |

### Chunk record

| Field | Purpose |
|---|---|
| `chunk_id` | Stable ID derived from source and chunk position/content |
| `source_id`, `url`, `title` | Traceability |
| `heading_path` | Context for the chunk |
| `text` | Extracted passage |
| `content_hash` | Detect changed content and support repeatable ingestion |
| `retrieved_at`, `chunker_version` | Freshness and reproducibility |

### Retrieval/answer metadata

Retain an opaque request ID, timestamp, selected chunk IDs, retrieval scores, provider/model identity, outcome category, citation URLs, and completion/error status only if needed for demo inspection. Do not retain raw user queries, identifiers, secrets, or unredacted provider prompts.

## 7. Configuration

Use one central configuration source for ingestion and query execution. A local environment file may supply secrets, but should be excluded from version control.

| Setting | Initial value / behavior |
|---|---|
| `embedding.model` | `sentence-transformers/all-MiniLM-L6-v2` |
| `vector_store.provider` | `chromadb` |
| `vector_store.persist_directory` | Local configurable path |
| `vector_store.collection` | Configurable collection name |
| `llm.provider` | `groq` |
| `llm.model` | `qwen/qwen3.8-27b`, validate availability |
| `llm.api_key_env` | Name of provider-specific environment variable; never the key itself |
| `sources.registry` | Explicitly curated source list |
| `retrieval.top_k` | Configurable small-corpus retrieval limit |
| `retrieval.min_relevance` | Configurable threshold/no-evidence behavior |
| `retrieval.live_source_fallback` | `true` to fetch one matching source from the curated registry when the embedding index is absent |
| `answer.max_sentences` | `3` |

Provider secrets are loaded at runtime from environment variables or a local `.env`. Configuration errors must identify the missing setting without printing secret values. Provider changes must not affect ingestion artifacts, and embedding/vector-store changes require explicit re-ingestion or migration rather than silent reuse of incompatible data.

## 8. Failure handling and observability

- **Fetch or parse failure:** Mark that source failed with a timestamp and useful non-secret error details; continue other independent sources where safe.
- **Partial ingestion:** Clearly mark the run as partial and prevent the UI from implying full coverage.
- **Embedding/store mismatch:** Stop with an explicit compatibility error; do not return empty or stale results as if successful.
- **No relevant evidence:** Return a transparent no-verification response with an appropriate link when available.
- **Provider failure:** Report that answer generation is temporarily unavailable; do not fabricate a success-shaped response.
- **Malformed or unsafe input:** Reject without logging or retaining the input.
- **Conflicting facts:** Show the conflict or state that the available sources disagree; cite the sources and avoid choosing a value without an explicit authoritative-source rule.

Logs and run summaries should focus on stage, duration, counts, status, source IDs, and opaque request IDs. Never log API keys, raw questions, prohibited personal data, or prompts containing such data.

## 9. Security, privacy, and trust boundaries

- **Public web boundary:** Treat fetched page content as untrusted. Do not execute embedded scripts or follow page-provided instructions.
- **User input boundary:** Screen before embedding and before any external LLM request; do not retain raw input.
- **Provider boundary:** Send only the minimum required, screened content. Credentials remain server-side and are never included in client code.
- **Citation boundary:** Only application-validated registry URLs may become citations; model-generated URLs are ignored.
- **Persistence boundary:** Store corpus artifacts and non-sensitive run metadata. Avoid user-level analytics and conversation history for this prototype.
- **Source authority boundary:** Distinguish required Groww starting targets from official AMC/SEBI/AMFI sources. Do not mislabel publishers or imply authority.

## 10. Deployment and demo shape

The first implementation can run locally as a small web app or notebook. Keep ingestion as an explicit command/action and query serving as a separate path so the demo can inspect saved artifacts without re-scraping on every question.

For a hosted demo, keep the same logical boundaries, store provider credentials only in server-side environment configuration, disable raw-input logging, and expose only the minimal UI and safe inspection data. Hosting, authentication, and operational hardening beyond the prototype are out of scope.

## 11. Key decisions and unresolved items

1. **Groww versus official sources:** Confirm whether Groww pages may be used as answer evidence. Until resolved, keep them identified as required loading targets but prefer explicitly curated official sources for citations.
2. **Additional sources:** The 15–25 URL list must be curated explicitly; no crawler should discover URLs from the five target pages.
3. **Statement-help coverage:** Add an official public help source if the approved corpus does not support statement-download instructions.
4. **Provider/model availability:** Validate Groq access to `qwen/qwen3.8-27b`; fail clearly if unavailable and require an explicit configuration change to use another provider/model.
5. **Freshness policy:** Distinguish fetch time from source-published update time and define an acceptable age threshold before representing a fact as current.
