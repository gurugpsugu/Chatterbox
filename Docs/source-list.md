# Source list

The approved registry is [`config/sources.json`](../config/sources.json). Fetching is restricted to these explicit HTTPS URLs; the scraper does not follow links to discover more sources. Where available, official AMC pages are preferred, with Groww pages used as labelled third-party fallbacks.

| Scheme | Official AMC source | Groww fallback |
|---|---|---|
| HDFC Large Cap Fund Direct Growth | — | [Groww](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth) |
| SBI Large Cap Fund Direct Plan Growth | [SBI Mutual Fund](https://www.sbimf.com/sbimf-scheme-details/sbi-large-cap-fund-(formerly-known-as-sbi-bluechip-fund)-43) | [Groww](https://groww.in/mutual-funds/sbi-large-cap-direct-plan-growth) |
| HDFC Mid Cap Fund Direct Growth | — | [Groww](https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth) |
| ICICI Prudential Mid Cap Fund Direct Plan Growth | [ICICI Prudential](https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-midcap-fund/15) | [Groww](https://groww.in/mutual-funds/icici-prudential-mid-cap-direct-plan-growth) |
| SBI Small Cap Fund Direct Growth | [SBI Mutual Fund](https://www.sbimf.com/sbimf-scheme-details/sbi-small-cap-fund-329) | [Groww](https://groww.in/mutual-funds/sbi-small-midcap-fund-direct-growth) |
| HDFC Flexi Cap Fund Direct Plan Growth | — | [Groww](https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth) |
| Nippon India Flexi Cap Fund Direct Growth | [Nippon India Mutual Fund](https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Flexi-Cap-Fund.aspx) | [Groww](https://groww.in/mutual-funds/nippon-india-flexi-cap-fund-direct-growth) |
| HDFC ELSS Tax Saver Fund Direct Plan Growth | — | [Groww](https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth) |
| Axis ELSS Tax Saver Fund Direct Growth | [Axis Mutual Fund](https://www.axismf.com/mutual-funds/equity-funds/axis-elss-tax-saver-fund/ts-dg/direct) | [Groww](https://groww.in/mutual-funds/axis-elss-tax-saver-direct-growth) |
| Kotak Nifty 50 Index Fund Direct Growth | [Kotak Mutual Fund](https://www.kotakmf.com/mutual-funds/passive-funds/kotak-nifty-50-index-fund/dir-g) | [Groww](https://groww.in/mutual-funds/kotak-nifty-50-index-fund-direct-growth) |
| ICICI Prudential Corporate Bond Fund Direct Plan Growth | [ICICI Prudential](https://www.icicipruamc.com/mutual-fund/debt-funds/icici-prudential-corporate-bond-fund/281) | [Groww](https://groww.in/mutual-funds/icici-prudential-corporate-bond-fund-direct-plan-growth) |
| Nippon India Balanced Advantage Fund Direct Growth | [Nippon India Mutual Fund](https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Balanced-Advantage-Fund.aspx) | [Groww](https://groww.in/mutual-funds/nippon-india-balanced-advantage-fund-direct-growth) |

AMC-level information is also sourced from [Groww's HDFC Mutual Fund overview](https://groww.in/mutual-funds/amc/hdfc-mutual-funds). Groww is a third-party source, not an official AMC, SEBI, or AMFI publication.

The performance panel displays available source-published annualised returns and SIP-history results, with a citation next to each dataset. The riskometer shows the published category and its position on the six-category scale. It does not derive a risk percentage; a number is shown only if the cited source explicitly publishes one.

The deployable numeric facts are refreshed from scraped artifacts with:

```powershell
python src\loading\scrape_sources.py
python src\loading\build_fund_fact_cache.py
```
