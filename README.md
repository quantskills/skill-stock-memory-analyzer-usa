# stock-memory-analyzer-usa

面向 MU、WDC、STX、SNDK 等美股存储产业链公司的可追溯研究分析 skill。它使用 `panda_data` 的可用市场与财务数据，并将 DRAM/NAND/HBM、库存、CapEx、技术节点和同业数据以来源、日期和假设为边界生成 HTML 研究报告。

## 状态与边界

- 项目类型：QUANTSKILLS Community Project
- 状态：未获 QUANTSKILLS 官方认证、验证、背书或生产可用认定
- 用途：研究与教育；不构成投资建议，不承诺收益，也不输出个性化买卖或仓位建议
- 许可证：`GPL-3.0-only`，详见 [LICENSE](LICENSE)

完整的使用流程、数据来源要求、风险边界和维护说明见 [SKILL.md](SKILL.md)。

## 来源与维护

- 上游组织：[QuantSkills](https://github.com/quantskills)
- 上游仓库：[skill-stock-memory-analyzer-usa](https://github.com/quantskills/skill-stock-memory-analyzer-usa)
- 维护者：repository contributors

请勿提交账号密码、API key、私有数据集或其他敏感信息。使用第三方数据、代码、论文或报告时，请保留归因并遵守许可证。

## 运行时入口

`SKILL.md` 是 Codex 和 Claude Code 的主入口；Cursor 使用 [agents/cursor-rule.mdc](agents/cursor-rule.mdc)，Hermes 与 OpenClaw 使用 [agents/portable-loader.md](agents/portable-loader.md)。这些适配文件只负责加载同一份主规范，避免多处维护产生偏差。
