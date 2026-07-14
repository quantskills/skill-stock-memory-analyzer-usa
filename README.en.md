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

This skill uses `panda_data` for market, financial, and valuation data. Install the Python dependencies before the first run:

```powershell
cd D:\PandaAi_skills\.claude\skills\stock-memory-analyzer
python -m pip install -r requirements.txt
```

If installation fails because of network or permissions, ensure that Python can access the package repository and the `panda_data` API, then retry.

### 2. Sign in to panda_data

A valid `panda_data` account is required to generate a full report.

In a chat environment that supports this skill, you may provide the credentials together with one ticker:

```text
Account: your panda_data account; Password: your panda_data password; Analyze MU
```

The skill uses the credentials only for the current analysis and does not display their contents in replies, HTML reports, files, or program logs.

Alternatively, set credentials in a local PowerShell session:

```powershell
$env:PANDA_DATA_USERNAME = 'your_username'
$env:PANDA_DATA_PASSWORD = 'your_password'
```

Check that the dependencies and credentials are available:

```powershell
python analyze.py --check-env
```

### 3. Generate an HTML research report

After sign-in succeeds, run one ticker. The default history window is five years:

```powershell
python analyze.py --ticker MU
```

Replace `MU` with `SNDK`, `WDC`, or `STX` for another supported ticker. Available history windows are `1y`, `2y`, `5y`, `10y`, and `max`:

```powershell
python analyze.py --ticker SNDK --period 2y
```

### 4. View the report

After a successful run, the terminal prints the report path. Reports are saved in `output/`:

```text
output/MU_analysis_YYYYMMDD_HHMMSS.html
```

Open the HTML file in a browser to view market and financial summaries, inventory and pricing cycles, HBM and end-market demand, technology nodes, peer comparisons, data-freshness notices, and the research-signal breakdown. Estimates and historical diagnostics include limitations and do not represent future performance.

## Troubleshooting

**A dependency is missing. What should I do?**

Run `python -m pip install -r requirements.txt`, then run `python analyze.py --check-env` again.

**Can I use public web data without signing in?**

No. A full report requires `panda_data` market and fundamentals data. If sign-in, dependencies, or network access is unavailable, the skill remains in setup mode and does not substitute web data into a report.

**Will my credentials appear in the report or logs?**

No. The skill and scripts do not echo account names, passwords, or tokens. Do not place credentials in source code, configuration files, or repository commits.

## Runtime entrypoints

`SKILL.md` is the primary entrypoint for Codex and Claude Code. Cursor loads [agents/cursor-rule.mdc](agents/cursor-rule.mdc); Hermes and OpenClaw load [agents/portable-loader.md](agents/portable-loader.md). Each adapter points to the same primary instructions to prevent drift.

## Upstream and maintenance

- Organization: [QuantSkills](https://github.com/quantskills)
- Repository: [skill-stock-memory-analyzer-usa](https://github.com/quantskills/skill-stock-memory-analyzer-usa)
- Maintainer: repository contributors

Never commit credentials, API keys, private datasets, or other sensitive information. Attribute third-party data, code, papers, and reports, and comply with their licenses.
