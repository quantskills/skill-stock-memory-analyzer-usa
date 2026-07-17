# stock-memory-analyzer-usa

A traceable research skill for US memory-industry companies such as MU, WDC, STX, and SNDK. It combines available `panda_data` market and financial data with cited DRAM/NAND/HBM, inventory, CapEx, technology-node, and peer inputs to create an HTML research report.

## Status and boundaries

- Project type: QUANTSKILLS Community Project
- Status: not officially certified, verified, endorsed, or production-ready
- Purpose: research and education only; it does not provide investment advice, trading instructions, position sizing, or return guarantees
- License: `GPL-3.0-only`; see [LICENSE](LICENSE)

Read [SKILL.md](SKILL.md) for the workflow, source-provenance requirements, assumptions, limitations, and risk boundaries.

## Supported tickers

The current version supports the following US-listed storage companies:

| Ticker | Company | Category |
| --- | --- | --- |
| `MU` | Micron Technology | DRAM / HBM / NAND |
| `SNDK` | Sandisk | NAND / flash memory |
| `WDC` | Western Digital | HDD storage infrastructure |
| `STX` | Seagate Technology | HDD storage infrastructure |

Choose one ticker for each full analysis. `WDC` and `STX` are HDD storage-infrastructure companies, so the report does not directly apply DRAM or HBM conclusions to them.

## Core evaluation logic

The report uses a two-layer evaluation model. It first combines memory-industry cycle signals into a memory-cycle score, then combines that score with short-term technicals, analyst consensus, company and shareholder activity, peer valuation, and financial quality to produce the final research signal. Market, financial, and valuation data come from `panda_data`; the GPU/HBM modules are anchored to official sources verified for the current run. GPU shipments, model mix, and HBM supply that are not directly disclosed are explicitly labeled as model estimates.

### Layer 1: Memory-cycle score

The memory-cycle score starts at 50, applies adjustments from six memory-specific modules, and is then bounded to `0–100`:

```text
C = clamp(50 + Δinventory + Δpricing + ΔCapEx + ΔHBM + Δend-market + Δtechnology, 0, 100)
```

| Module | Main rule in the current implementation | Score contribution |
| --- | --- | --- |
| Inventory cycle | Recent inventory-days direction and its position relative to the historical average | `+20 / +10 / 0 / -10 / -20` |
| DRAM/NAND pricing cycle | Recent contract-price direction, cross-checked and adjusted with the company's gross-margin trend | `+25 / +12 / 0 / -12 / -25` |
| CapEx | Annual capital-expenditure growth classified as aggressive expansion, moderate expansion, maintenance, or contraction | `+12 / +6 / 0 / -6` |
| HBM supply and demand | NVIDIA Compute revenue, assumed GPU ASP and model mix, HBM per GPU, and supply parameters form a gap model | A base score for shortage, tight balance, or ample supply multiplied by the company's HBM-exposure factor |
| End-market demand | DRAM, NAND, HBM, and HDD industry growth weighted by the company's revenue mix | `+12 / +6 / +2 / -5` |
| Technology nodes | The company's DRAM and NAND node position | `0–7` |

The HBM-exposure factors are `1.0` for a major supplier, `0.6` for partial exposure, and `0.3` for a company without direct HBM participation. The model therefore does not apply MU's HBM sensitivity unchanged to WDC or STX.

### Layer 2: Final research signal

The final report converts each dimension into a score near the `0–100` scale and applies the current implementation formula:

```text
S = 0.10 × short-term technicals
  + 0.25 × memory cycle
  + 0.12 × analyst consensus
  + 0.08 × HBM supply and demand
  + 0.08 × end-market demand
  + 0.08 × insider activity
  + 0.08 × shareholder changes
  + 0.04 × technology nodes
  + 0.05 × peer comparison
  + financial-quality adjustment

Final research signal = clamp(S, 10, 95)
```

The first nine terms are scoring coefficients. The financial-quality adjustment directly adds or subtracts points based on net margin, gross margin, ROE, debt-to-equity, price-to-book, and Beta. These terms are not a normalized 100% asset-pricing model. In the current implementation, HBM, end-market demand, and technology nodes contribute both to the first-layer memory-cycle score and to the second layer as company-specific sub-scores; the report displays both breakdowns.

| Final research signal | Interpretation |
| --- | --- |
| `65–95` | Research indicators are broadly strong, but data freshness and model assumptions still require review |
| `50–64` | Indicators are in the middle range; verify cycle inflections and missing data |
| `35–49` | Several indicators are weak; continue checking fundamentals and data timing |
| `10–34` | Risk or data-quality warnings dominate; verify completeness before drawing conclusions |

The research signal is only an explainable summary of the evidence under the current data, sources, and assumptions. It is not a buy or sell recommendation, price target, probability of appreciation, or return guarantee.

## Evaluation dimensions

| Dimension | What it evaluates | Primary source or method |
| --- | --- | --- |
| Short-term technicals | RSI(14), MACD Histogram, volume ratio, and MA5 direction | `panda_data` daily prices and `utils/indicators.py` |
| Financials and valuation | Revenue, net margin, gross margin, ROE, leverage, PE, PB, and Beta | `panda_data` financial and valuation endpoints |
| Inventory cycle | Inventory-days direction, historical average, and inferred cycle phase | Quarterly inventory and COGS |
| DRAM/NAND pricing | Contract-price direction and whether gross margin confirms it | Cited industry material and company financial data |
| HBM/GPU | GPU specifications, Compute revenue, shipments and model mix, HBM per GPU, and the supply-demand gap | NVIDIA, SEC, and memory-supplier disclosures plus explicit models |
| End-market demand | DRAM, NAND, HBM, and HDD end-market structure and company-weighted exposure | Industry material, company business mix, and model weighting |
| CapEx and technology nodes | Expansion pace and DRAM/NAND process position | Company financials, company disclosures, and industry road maps |
| Market participants | Analyst consensus, insider transactions, and shareholder-position changes | Relevant `panda_data` endpoints and public-filing-derived data |
| Peer comparison | Current PE relative to the configured peer average | `panda_data` valuation data |
| Data quality | Source, data period, current-run verification, missing fields, conflicts, and old-snapshot authorization | Industry-refresh gate and report freshness panels |
| Historical-sample diagnostics | IC, bucketed returns, and win rates between a simplified score and subsequent 3/6/12-month returns | Historical market, financial, and industry inputs |

The historical module uses a simplified score that is different from the live research signal and serves only as a correlation diagnostic. Small samples, backfilled data, timing mismatches, survivorship bias, overfitting, and omitted transaction costs can materially affect the result. It does not prove that a strategy works or predict future performance.

## Skill highlights

- **Pre-analysis refresh gate:** Every full analysis first verifies `gpu_specs`, `nvda_compute_revenue`, `gpu_shipments`, `gpu_mix`, and `hbm_supply`. If refresh is incomplete, the user must explicitly decide whether the run may use a complete prior snapshot.
- **Facts and estimates remain separate:** Official facts, third-party industry material, and model estimates are displayed separately; models retain their inputs, formulas, assumptions, confidence, and limitations.
- **Company-specific exposure:** Revenue mix, HBM exposure, and actual technology nodes adjust the impact for MU, SNDK, WDC, and STX instead of applying one memory-vendor template to HDD companies.
- **Industry/company cross-check:** DRAM/NAND contract prices provide the industry signal, while the company's gross-margin trend confirms or adjusts the cycle assessment.
- **Traceable sources and timing:** Reports display source links, `published_at`, `as_of`, `verified_at`, data freshness, and the current run mode.
- **Secure local sign-in:** Windows uses a visible PowerShell window and macOS uses Terminal.app. Password characters are hidden, and credentials do not enter chat, HTML, files, command history, or logs.
- **Interactive research report:** The HTML report combines market data, financials, valuation, memory cycles, HBM, end markets, technology nodes, peer comparison, score breakdowns, and historical-sample diagnostics.

## Quick start

### 1. Install dependencies

This skill uses `panda_data` for market, financial, and valuation data. Install the Python dependencies before the first run.

Windows PowerShell:

```powershell
cd D:\PandaAi_skills\.claude\skills\stock-memory-analyzer
python -m pip install -r requirements.txt
python analyze.py --check-deps
```

macOS Terminal:

```bash
cd /path/to/stock-memory-analyzer
python3 -m pip install -r requirements.txt
python3 analyze.py --check-deps
```

If installation fails because of network or permissions, ensure that Python can access the package repository and the `panda_data` API, then retry.

### 2. Sign in to panda_data in a temporary local window

A valid `panda_data` account is required to generate a full report. Do not send an account name or password in chat. First choose one ticker in the conversation, for example, "Analyze MU."

Before opening the login window, the skill re-verifies GPU specifications and NVIDIA Compute revenue from official China/global NVIDIA, SEC, Micron, SK hynix, Samsung, and TSMC endpoints, then recomputes the GPU-shipment, model-mix, and HBM-supply estimates. The report separates facts from model estimates and displays both `as_of` and the current run's `verified_at`. If one regional endpoint is unavailable, the skill tries another official endpoint from the same publisher.

If refresh is incomplete, the skill lists the failed modules and the prior valid snapshot dates, then asks whether this run may use old data. It continues only after explicit approval and only when a complete valid snapshot exists; refusal, no answer, or no valid snapshot stops the run without silent fallback.

Before opening the login window, the skill explains that Windows will open PowerShell or macOS will open Terminal.app, request credentials locally, hide password characters, automatically close the temporary window when finished, and then continue checking the report.

The program opens a visible temporary PowerShell window on Windows or Terminal.app window on macOS. Enter the account locally; password characters are hidden. Credentials exist only in that child process and are not written to chat, files, HTML reports, command history, or program logs. The process clears them before the window closes.

You can also start the same flow manually from the project directory.

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_with_prompt.ps1 -Ticker MU -Period 5y -IndustryRunManifest output/runtime/industry_run.json
```

macOS:

```bash
bash scripts/run_with_prompt.sh --ticker MU --period 5y --industry-run-manifest output/runtime/industry_run.json
```

### 3. Generate an HTML research report

After sign-in succeeds in the temporary window, the script automatically analyzes the selected ticker and generates the report. No second command is required. The default history window is five years.

Replace `MU` with `SNDK`, `WDC`, or `STX` for another supported ticker. Available history windows are `1y`, `2y`, `5y`, `10y`, and `max`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_with_prompt.ps1 -Ticker SNDK -Period 2y -IndustryRunManifest output/runtime/industry_run.json
```

```bash
bash scripts/run_with_prompt.sh --ticker SNDK --period 2y --industry-run-manifest output/runtime/industry_run.json
```

### 4. View the report

After a successful run, the terminal prints the report path. Reports are saved in `output/`:

```text
output/MU_analysis_YYYYMMDD_HHMMSS.html
```

Open the HTML file in a browser to view market and financial summaries, inventory and pricing cycles, HBM and end-market demand, technology nodes, peer comparisons, data-freshness notices, and the research-signal breakdown. The GPU/HBM provenance panel shows official links, publication dates, data periods, current-run verification times, formulas, and assumptions; an old-snapshot run has a prominent warning. Estimates and historical diagnostics include limitations and do not represent future performance.

## Troubleshooting

**A dependency is missing. What should I do?**

On Windows, run `python -m pip install -r requirements.txt`; on macOS, run `python3 -m pip install -r requirements.txt`. Then start the platform-specific `run_with_prompt` script again.

**Can I use public web data without signing in?**

No. A full report requires `panda_data` market and fundamentals data. If sign-in, dependencies, or network access is unavailable, the skill remains in setup mode and does not substitute web data into a report.

**Will my credentials appear in the report or logs?**

No. Password characters are hidden in the temporary PowerShell or Terminal.app window, and the skill and scripts do not echo account names, passwords, or tokens to chat, reports, files, or logs. Do not place credentials in source code, configuration files, or repository commits.

**Why does macOS show a permission prompt the first time?**

macOS may ask the current application for permission to automate Terminal.app. This system permission is required to open the visible login window. If denied, enable it later under System Settings → Privacy & Security → Automation.

## Runtime entrypoints

`SKILL.md` is the primary entrypoint for Codex and Claude Code. Cursor loads [agents/cursor-rule.mdc](agents/cursor-rule.mdc); Hermes and OpenClaw load [agents/portable-loader.md](agents/portable-loader.md). Each adapter points to the same primary instructions to prevent drift.

## Upstream and maintenance

- Organization: [QuantSkills](https://github.com/quantskills)
- Repository: [skill-stock-memory-analyzer-usa](https://github.com/quantskills/skill-stock-memory-analyzer-usa)
- Maintainer: repository contributors

Never commit credentials, API keys, private datasets, or other sensitive information. Attribute third-party data, code, papers, and reports, and comply with their licenses.
