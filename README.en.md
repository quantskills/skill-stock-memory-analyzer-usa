# stock-memory-analyzer-usa

A traceable research skill for US memory-industry companies such as MU, WDC, STX, and SNDK. It combines available `panda_data` market and financial data with cited DRAM/NAND/HBM, inventory, CapEx, technology-node, and peer inputs to create an HTML research report.

## Status and boundaries

- Project type: QUANTSKILLS Community Project
- Status: not officially certified, verified, endorsed, or production-ready
- Purpose: research and education only; it does not provide investment advice, trading instructions, position sizing, or return guarantees
- License: `GPL-3.0-only`; see [LICENSE](LICENSE)

Read [SKILL.md](SKILL.md) for the workflow, source-provenance requirements, assumptions, limitations, and risk boundaries.

## Runtime entrypoints

`SKILL.md` is the primary entrypoint for Codex and Claude Code. Cursor loads [agents/cursor-rule.mdc](agents/cursor-rule.mdc); Hermes and OpenClaw load [agents/portable-loader.md](agents/portable-loader.md). Each adapter points to the same primary instructions to prevent drift.

## Upstream and maintenance

- Organization: [QuantSkills](https://github.com/quantskills)
- Repository: [skill-stock-memory-analyzer-usa](https://github.com/quantskills/skill-stock-memory-analyzer-usa)
- Maintainer: repository contributors

Never commit credentials, API keys, private datasets, or other sensitive information. Attribute third-party data, code, papers, and reports, and comply with their licenses.
