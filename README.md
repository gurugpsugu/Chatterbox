# Chatterbox

Chatterbox is an inspectable mutual-fund FAQ assistant built around approved public sources. It answers supported factual questions about 12 schemes across six AMCs, cites its sources, and refuses investment advice and personal-information requests.

## Scope

- Public pages only
- Fact-based answers about selected schemes from six AMCs
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
   - `python src\loading\build_fund_fact_cache.py`
   - `python src\chunking\chunk_documents.py`
   - `python src\embedding\embed_chunks.py`
   - `python src\vector_store\store.py`

## Configuration

Shared settings are stored in `config/settings.json` and source approval data in `config/sources.json`.

The default embedding model is:

- `sentence-transformers/all-MiniLM-L6-v2`

The default vector-store configuration is ChromaDB under `data/chroma/`.

## Demo behavior

The project includes a responsive web UI in `src/ui/web_page.py`, served by the FastAPI entrypoint in `app.py`. It offers 12 schemes across six AMCs and answers common numeric questions from the checked-in, date-stamped `data/fund_facts.json` cache, avoiding a live source request for those facts. The console UI remains available through `python -m src.ui.app`.

For Vercel, set the project root to the repository root. The `tool.vercel.entrypoint` setting in `pyproject.toml` explicitly points to the FastAPI app.

The assistant:

- rejects empty questions
- rejects likely personal-identifiers or account data
- refuses buy/sell or personalized investment advice
- returns a facts-only answer when evidence exists
- says facts could not be verified when they do not exist in the available corpus

## Sources

The approved source registry in `config/sources.json` contains scheme pages from the relevant AMCs and Groww fallbacks. Pages are fetched only from this allowlist; the scraper does not crawl links from them.

| Scheme | Approved source links |
|---|---|
| HDFC Large Cap Fund Direct Growth | [Groww](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth) |
| SBI Large Cap Fund Direct Plan Growth | [SBI Mutual Fund](https://www.sbimf.com/sbimf-scheme-details/sbi-large-cap-fund-(formerly-known-as-sbi-bluechip-fund)-43) · [Groww](https://groww.in/mutual-funds/sbi-large-cap-direct-plan-growth) |
| HDFC Mid Cap Fund Direct Growth | [Groww](https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth) |
| ICICI Prudential Mid Cap Fund Direct Plan Growth | [ICICI Prudential](https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-midcap-fund/15) · [Groww](https://groww.in/mutual-funds/icici-prudential-mid-cap-direct-plan-growth) |
| SBI Small Cap Fund Direct Growth | [SBI Mutual Fund](https://www.sbimf.com/sbimf-scheme-details/sbi-small-cap-fund-329) · [Groww](https://groww.in/mutual-funds/sbi-small-midcap-fund-direct-growth) |
| HDFC Flexi Cap Fund Direct Plan Growth | [Groww](https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth) |
| Nippon India Flexi Cap Fund Direct Growth | [Nippon India Mutual Fund](https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Flexi-Cap-Fund.aspx) · [Groww](https://groww.in/mutual-funds/nippon-india-flexi-cap-fund-direct-growth) |
| HDFC ELSS Tax Saver Fund Direct Plan Growth | [Groww](https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth) |
| Axis ELSS Tax Saver Fund Direct Growth | [Axis Mutual Fund](https://www.axismf.com/mutual-funds/equity-funds/axis-elss-tax-saver-fund/ts-dg/direct) · [Groww](https://groww.in/mutual-funds/axis-elss-tax-saver-direct-growth) |
| Kotak Nifty 50 Index Fund Direct Growth | [Kotak Mutual Fund](https://www.kotakmf.com/mutual-funds/passive-funds/kotak-nifty-50-index-fund/dir-g) · [Groww](https://groww.in/mutual-funds/kotak-nifty-50-index-fund-direct-growth) |
| ICICI Prudential Corporate Bond Fund Direct Plan Growth | [ICICI Prudential](https://www.icicipruamc.com/mutual-fund/debt-funds/icici-prudential-corporate-bond-fund/281) · [Groww](https://groww.in/mutual-funds/icici-prudential-corporate-bond-fund-direct-plan-growth) |
| Nippon India Balanced Advantage Fund Direct Growth | [Nippon India Mutual Fund](https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Balanced-Advantage-Fund.aspx) · [Groww](https://groww.in/mutual-funds/nippon-india-balanced-advantage-fund-direct-growth) |

The [HDFC AMC overview](https://groww.in/mutual-funds/amc/hdfc-mutual-funds) is also approved for AMC-level facts. Groww is a third-party source, not an official AMC, SEBI, or AMFI publication.

## Sample Q&A

These examples describe the kinds of questions the assistant handles. Answers depend on the available source evidence and include citations; if a fact cannot be verified, the assistant says so.

| Question | Example response | Example source |
|---|---|---|
| What is the expense ratio of HDFC Large Cap Fund Direct Growth? | The assistant looks up the scheme fact in the available source and cites it. | [HDFC Large Cap Fund](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth) |
| What is the minimum SIP amount for HDFC Mid Cap Fund? | The assistant checks the minimum SIP requirement in the scheme source and cites it. | [HDFC Mid Cap Fund](https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth) |
| What is the ELSS lock-in period? | The assistant answers from the HDFC ELSS source when evidence is available and cites it. | [HDFC ELSS Tax Saver Fund](https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth) |
| Should I buy HDFC Mutual Fund? | I can provide factual information, but I can’t make buy/sell recommendations. | [SEBI investor education](https://www.sebi.gov.in/) |

## Disclaimer

**Facts-only. No investment advice.** Responses reflect information available from cited sources and are not investment recommendations. Mutual fund investments are subject to market risks. Please read all scheme-related documents carefully. Past performance may or may not be sustained in the future. Please consult your financial adviser before investing.

## Known limits

- The checked-in fact cache contains numeric facts extracted from the approved pages as of each source's retrieval timestamp; refresh it after scraping.
- The prototype does not crawl links from the target pages.
- Only curated public sources are used, and official AMC/SEBI/AMFI pages should be preferred when available.
- Generated data, local secrets, and model artifacts remain outside source control.
- The full chunk corpus and vector index are not deployed; questions outside the cached numeric facts may need a live source lookup.
