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
