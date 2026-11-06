# Chatterbox

Chatterbox is a small, inspectable mutual-fund FAQ assistant built around a public-source retrieval pipeline. It is designed to answer factual questions about HDFC Mutual Fund and a small set of HDFC scheme pages while refusing investment advice and personal-information requests.

## Scope

- Public pages only
- Fact-based answers about HDFC Mutual Fund and selected schemes
- Source citations for every answer
- No investment advice or personalized portfolio recommendations
- No PAN, Aadhaar, account numbers, OTPs, email addresses, or phone numbers

## Setup

1. Create a local environment if needed:
   - `python -m venv .venv`
   - `.venv\Scripts\activate`
2. Install dependencies:
   - `python -m pip install -r requirements.txt`
3. Add provider settings locally:
   - Copy `.env.example` to `.env`
   - Set `GROQ_API_KEY` if you want to enable an external LLM provider
4. Run the local web UI:
   - `python -m uvicorn app:app --reload`
   - Open `http://127.0.0.1:8000`
5. Run the ingestion stages as needed:
   - `python src\loading\scrape_sources.py`
   - `python src\loading\load_documents.py`
   - `python src\chunking\chunk_documents.py`
   - `python src\embedding\embed_chunks.py`
   - `python src\vector_store\store.py`

## Configuration

Shared settings are stored in `config/settings.json` and source approval data in `config/sources.json`.

The default embedding model is:

- `sentence-transformers/all-MiniLM-L6-v2`

The default vector-store configuration is ChromaDB under `data/chroma/`.

## Demo behavior

The project includes a responsive web UI in `src/ui/web_page.py`, served by the FastAPI entrypoint in `app.py`. It offers selectable starter questions, source links when returned by the assistant, and the exact disclaimer “Facts-only. No investment advice.” The console UI remains available through `python -m src.ui.app`.

For Vercel, set the project root to the repository root. The `tool.vercel.entrypoint` setting in `pyproject.toml` explicitly points to the FastAPI app.

The assistant:

- rejects empty questions
- rejects likely personal-identifiers or account data
- refuses buy/sell or personalized investment advice
- returns a facts-only answer when evidence exists
- says facts could not be verified when they do not exist in the available corpus

## Known limits

- The approved initial corpus is limited to the five Groww targets in `config/sources.json`.
- The prototype does not crawl links from the target pages.
- Only curated public sources are used, and official AMC/SEBI/AMFI pages should be preferred when available.
- Generated data, local secrets, and model artifacts remain outside source control.
- The Vercel app needs the chunk corpus and a persistent hosted vector database configured before it can answer corpus questions reliably; local generated data and JSON/Chroma files are not deployed.
