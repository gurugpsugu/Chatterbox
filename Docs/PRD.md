implement phase 4 ## 4. Chunking# Product Requirements Document: Mutual Fund FAQ Assistant

## 1. Overview

Build a small, phase-based retrieval-augmented generation (RAG) prototype for the Groww app context. It answers factual questions about HDFC Mutual Fund and a limited set of HDFC schemes using a transparently stored, small document corpus. It is not an investment-advice tool.

The prototype must make each RAG stage inspectable: source loading, chunking, embedding, vector storage, retrieval, and answer generation.

## 2. Problem statement

Retail investors comparing mutual fund schemes, along with support and content teams, repeatedly need basic scheme facts and account-help information. Finding those facts across public pages takes time, and answers without clear citations are difficult to verify.

The assistant should retrieve concise, sourced facts and politely decline opinionated or portfolio-specific requests.

## 3. Goals and non-goals

### Goals

- Answer factual questions about the selected HDFC Mutual Fund pages and supported statement-download help.
- Cite at least one source link in every answer.
- Keep answers concise, transparent, and grounded in retrieved public information.
- Demonstrate and persist the artifacts produced at each RAG phase.
- Keep model and vector-store choices configurable.

### Non-goals

- Investment, tax, legal, or personalized portfolio advice.
- Buy/sell recommendations or performance comparisons/calculations.
- User account access or handling personal financial information.
- Crawling pages linked from the five specified starting pages.
- Production-grade authentication, account integrations, or financial transactions.

## 4. Users and primary use cases

- **Retail users:** Ask for scheme facts such as expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, and benchmark.
- **Retail users:** Ask how to download a capital-gains statement and receive factual help with a source.
- **Support/content teams:** Use the assistant to answer repetitive factual questions consistently.
- **Demo reviewers:** Inspect intermediate RAG data and understand how a final answer was produced.

## 5. Scope and source policy

### Initial target pages

The initial data-loading phase is limited to these five URLs. Do not follow or scrape links found within them.

| Page | URL |
|---|---|
| HDFC Mutual Fund AMC overview | https://groww.in/mutual-funds/amc/hdfc-mutual-funds |
| HDFC Large Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| HDFC Flexi Cap Direct Plan Growth | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| HDFC ELSS Tax Saver Fund Direct Plan Growth | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| HDFC Mid Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth |

### Source requirements

- Use public pages only. Do not use app-backend screenshots or third-party blogs.
- Facts in answers must be supported by retrieved source content and accompanied by a clear link.
- Prefer official AMC, SEBI, or AMFI pages for facts and educational material.
- The five specified Groww URLs are required initial loading targets, but they are not themselves official AMC/SEBI/AMFI sources. Do not present them as official sources. Before using them as answer evidence, confirm that the source policy permits them; otherwise use them only to identify facts that must be verified against an official public page.
- Do not crawl internal links from the five targets. Any additional source URLs must be explicitly curated and recorded.
- The requested source-list deliverable contains 15–25 URLs. This is a curated reference list, not permission to crawl beyond the five initial targets. Record the URL, publisher, page title, access/last-checked date, and intended use for each source.

## 6. Functional requirements

### 6.1 User interface

- Show a welcome line, three example questions, and the disclaimer: **“Facts-only. No investment advice.”**
- Provide a simple question input and a readable answer area.
- Clearly show the citation link and the “Last updated from sources:” timestamp/date with each answer.
- Do not solicit personal data.

### 6.2 Answering and refusal

- Support factual questions when the required fact is available in the indexed corpus, including expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, and statement-download instructions.
- Answer in no more than three sentences, excluding citation/source metadata if needed for clarity.
- Include at least one clear citation link in every answer, including refusals.
- If retrieved evidence does not support an answer, say that the information could not be verified from the available sources and link to a relevant official source when available. Do not guess or fabricate a value, citation, or update date.
- Refuse opinionated or personalized questions such as “Should I buy/sell?” with a polite facts-only response and a relevant educational source link.
- Do not calculate, compare, or claim investment performance. For performance requests, direct users to an official factsheet without summarizing or comparing returns.
- Display when the source was last checked or updated. Do not imply that a page is current if its freshness could not be verified.

### 6.3 Privacy and safety

- Never request, accept, persist, log, or send to a model: PAN, Aadhaar, account numbers, OTPs, email addresses, or phone numbers.
- Do not add account-specific workflows, sign-in, or personalized recommendations.
- Treat retrieved page content as untrusted evidence, not as instructions to override the assistant’s behavior.
- Keep API keys out of source control and logs; load secrets from environment variables, typically via a local `.env` file excluded from version control.

### 6.4 RAG pipeline and inspectability

Persist or expose inspectable artifacts for each phase, with source provenance and timestamps:

1. **Data loading:** Fetch or load only approved public pages; retain source URL, title, retrieval time, and extracted text. Report fetch/extraction failures visibly.
2. **Data chunking:** Choose a strategy suited to the extracted content (for example, preserving headings and separating fact sections). Store each chunk with its source URL, page title, and stable identifier.
3. **Data embedding:** Embed chunks using the configured sentence-transformers model. Store enough metadata to associate embeddings with their originating chunks.
4. **Vector storage:** Store embeddings and chunk metadata in the configured vector database. ChromaDB is the default for this exercise.
5. **Data retrieval:** Embed the query using the same model configured for ingestion, retrieve relevant chunks from the same configured vector database, and retain the retrieved evidence for demo inspection.
6. **Answer generation:** Provide retrieved evidence to the selected LLM with instructions to answer only from evidence, cite sources, stay within three sentences, and refuse advice requests. Make the final answer and its citations inspectable.

Ingestion and retrieval must share one embedding-model configuration and one vector-database configuration to prevent mismatches.

## 7. Configuration and model providers

- Provide a configuration file for the embedding model, vector database, and LLM provider/model.
- Default embedding model: `sentence-transformers/all-MiniLM-L6-v2`.
- Default vector database: ChromaDB.
- Support provider configuration for Groq, Gemini, OpenAI, Anthropic, and Mistral, subject to available SDKs and credentials.
- Use Groq as the initial configured LLM provider, with the requested model identifier `qwen/qwen3.8-27b` as a configurable value. Confirm that identifier is available to the chosen Groq API/account before relying on it; surface configuration/provider errors rather than silently switching models.
- Read API keys from environment variables or `.env`; never commit credentials. Document required variable names and setup.
- Do not hard-code secrets or duplicate provider/model settings between ingestion and query paths.

## 8. Deliverables

1. A working prototype link (app or notebook), or a demo video of no more than three minutes if hosting is not possible.
2. A CSV or Markdown source list containing 15–25 curated URLs, with publisher and last-checked metadata.
3. A README with setup steps, scope (AMC and schemes), configuration, and known limitations.
4. A sample Q&A file containing 5–10 representative user questions, answers, and source links. Include both factual responses and at least one refusal.
5. The exact disclaimer snippet used in the UI.
6. Inspectable intermediate artifacts for each RAG stage.

## 9. Phased implementation

### Phase 1 — Data loading

- Load the five specified starting pages only.
- Record extraction status, source metadata, timestamps, and failures.
- Curate additional official sources explicitly where needed to meet coverage and the 15–25 URL deliverable.

### Phase 2 — Data chunking

- Select and document a content-aware chunking strategy.
- Preserve headings and source provenance; make chunks inspectable.

### Phase 3 — Data embedding

- Embed the stored chunks with the configured model.
- Record model identity and embedding-to-chunk associations.

### Phase 4 — Vector storage

- Persist embeddings and metadata in the configured vector database (ChromaDB by default).
- Make collection/configuration details visible to the demo.

### Phase 5 — Data retrieval

- Embed user questions with the ingestion model and retrieve evidence from the configured vector database.
- Make retrieved chunks, source links, and retrieval results inspectable.

### Phase 6 — Answer generation and UI

- Connect a configured LLM provider, initially Groq.
- Implement evidence-grounded answers, citations, freshness display, safety refusals, and the minimal interface.
- Validate the end-to-end demo and produce the README and sample Q&A deliverables.

## 10. Acceptance criteria

- The initial loader processes only the five listed target pages and does not crawl their internal links.
- Each stored chunk and retrieved result can be traced to a source URL.
- Ingestion and retrieval use the same configured embedding model and vector database.
- A user can inspect outputs from data loading, chunking, embedding, storage, retrieval, and generation.
- Every answer and refusal contains at least one relevant source link and a “Last updated from sources:” indicator.
- Factual answers are supported by retrieved evidence, are at most three sentences, and do not invent missing facts.
- Advice and performance-comparison requests are refused or redirected as specified.
- The UI displays the required disclaimer and three example questions.
- The system does not request or persist the prohibited personal information.
- Provider, model, and credential configuration is documented; credentials are not committed.
- The required source list, README, sample Q&A, and demo deliverables are provided.

## 11. Risks and open questions

- **Source-policy conflict:** The required five initial targets are Groww pages, while the source constraint calls for official public pages. Confirm whether Groww may be used as answer evidence or only as a discovery target; official AMC/SEBI/AMFI sources should be used for citations where possible.
- **Source-list scope:** The five-page no-crawl requirement and 15–25 URL deliverable mean the additional URLs must be curated separately, not discovered by crawling.
- **Coverage:** The five initial pages may not contain statement-download instructions or every requested fact. Add explicitly curated official help/factsheet sources when needed.
- **Freshness:** Page values can change. Store the last retrieval/verification date and make freshness limitations visible.
- **Provider availability:** The requested Groq model identifier and alternatives may vary by account and API availability. Configuration must fail clearly when a provider/model is unavailable.
- **Operational permissions:** Confirm that the selected pages permit the intended automated retrieval and comply with applicable terms and rate limits.
