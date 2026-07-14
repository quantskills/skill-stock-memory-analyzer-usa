# stock-memory-analyzer-usa

面向 MU、WDC、STX、SNDK 等美股存储产业链公司的可追溯研究分析 skill。它使用 `panda_data` 的可用市场与财务数据，并将 DRAM/NAND/HBM、库存、CapEx、技术节点和同业数据以来源、日期和假设为边界生成 HTML 研究报告。

## 状态与边界

- 项目类型：QUANTSKILLS Community Project
- 状态：未获 QUANTSKILLS 官方认证、验证、背书或生产可用认定
- 用途：研究与教育；不构成投资建议，不承诺收益，也不输出个性化买卖或仓位建议
- 许可证：`GPL-3.0-only`，详见 [LICENSE](LICENSE)

完整的使用流程、数据来源要求、风险边界和维护说明见 [SKILL.md](SKILL.md)。

## 支持标的

当前版本可分析以下美股存储公司：

| 代码 | 公司 | 分类 |
| --- | --- | --- |
| `MU` | Micron Technology | DRAM / HBM / NAND |
| `SNDK` | Sandisk | NAND / 闪存 |
| `WDC` | Western Digital | HDD 存储基础设施 |
| `STX` | Seagate Technology | HDD 存储基础设施 |

每次正式分析请选择一只标的。`WDC` 与 `STX` 属于 HDD 存储基础设施公司，报告不会把 DRAM 或 HBM 结论直接套用到它们。

## 快速开始

### 1. 安装依赖

本 Skill 使用 `panda_data` 获取行情、财务和估值数据；首次使用需安装 Python 依赖：

```powershell
cd D:\PandaAi_skills\.claude\skills\stock-memory-analyzer
python -m pip install -r requirements.txt
```

如遇网络或权限问题，请确认 Python 可以访问包仓库和 `panda_data` API 后重试。

### 2. 登录 panda_data

需要可用的 `panda_data` 账号才能生成正式报告。

在支持此 Skill 的聊天环境中，可以直接发送以下格式，并同时指定一只股票：

```text
账号：你的 panda_data 账号；密码：你的 panda_data 密码；分析 MU
```

Skill 只在本次分析中使用凭据，不在回复、HTML 报告、文件或程序日志中输出其具体内容。

也可以在本地 PowerShell 通过环境变量登录：

```powershell
$env:PANDA_DATA_USERNAME = 'your_username'
$env:PANDA_DATA_PASSWORD = 'your_password'
```

先检查依赖和凭据是否就绪：

```powershell
python analyze.py --check-env
```

### 3. 生成 HTML 研究报告

登录验证通过后，运行单只标的分析。默认使用 5 年历史窗口：

```powershell
python analyze.py --ticker MU
```

如需其他已支持标的，将 `MU` 替换为 `SNDK`、`WDC` 或 `STX`。可选的历史窗口包括 `1y`、`2y`、`5y`、`10y` 和 `max`：

```powershell
python analyze.py --ticker SNDK --period 2y
```

### 4. 查看报告

成功运行后，终端会输出报告路径，文件保存至 `output/`：

```text
output/MU_analysis_YYYYMMDD_HHMMSS.html
```

使用浏览器打开该 HTML 文件即可查看行情与财务概览、库存与价格周期、HBM / 下游需求、技术节点、同业对标、数据新鲜度提示及研究信号拆解。报告中的估算和历史诊断均有局限说明，不代表未来表现。

## 常见问题

**提示缺少依赖怎么办？**

执行 `python -m pip install -r requirements.txt`，随后再次运行 `python analyze.py --check-env`。

**可以不登录直接使用公开网页数据吗？**

不可以。正式报告依赖 `panda_data` 的行情和基本面数据；未登录、依赖缺失或网络不可用时，Skill 会停留在设置阶段，不会用网页数据补成报告。

**密码会出现在报告或运行日志中吗？**

不会。Skill 与脚本都禁止回显账号、密码和 token；请勿将凭据写入代码、配置文件或提交到仓库。

## 来源与维护

- 上游组织：[QuantSkills](https://github.com/quantskills)
- 上游仓库：[skill-stock-memory-analyzer-usa](https://github.com/quantskills/skill-stock-memory-analyzer-usa)
- 维护者：repository contributors

请勿提交账号密码、API key、私有数据集或其他敏感信息。使用第三方数据、代码、论文或报告时，请保留归因并遵守许可证。

## 运行时入口

`SKILL.md` 是 Codex 和 Claude Code 的主入口；Cursor 使用 [agents/cursor-rule.mdc](agents/cursor-rule.mdc)，Hermes 与 OpenClaw 使用 [agents/portable-loader.md](agents/portable-loader.md)。这些适配文件只负责加载同一份主规范，避免多处维护产生偏差。
