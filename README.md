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

## 核心评估逻辑

报告采用两层评估：先把存储行业特有的周期信号汇总为“存储周期评分”，再将该评分与短期技术、分析师、公司行为、同行估值和财务质量合成为最终“研究信号”。行情、财务和估值来自 `panda_data`；GPU/HBM 模块以本轮官方来源核验结果为锚；无法直接披露的 GPU 出货、型号占比和 HBM 供给明确标为模型估算。

### 第一层：存储周期评分

存储周期评分从 50 分起步，按六个存储专属模块加减分，最后限制在 `0–100`：

```text
C = clamp(50 + Δ库存 + Δ价格 + ΔCapEx + ΔHBM + Δ下游 + Δ技术节点, 0, 100)
```

| 模块 | 当前实现的主要判断 | 评分贡献 |
| --- | --- | --- |
| 库存周期 | 最近库存天数趋势及其相对历史均值的位置 | `+20 / +10 / 0 / -10 / -20` |
| DRAM/NAND 价格周期 | 最近合约价变化为主，公司毛利率趋势用于交叉修正 | `+25 / +12 / 0 / -12 / -25` |
| CapEx | 年度资本开支增速对应激进扩产、温和扩产、维持或收缩 | `+12 / +6 / 0 / -6` |
| HBM 供需 | NVIDIA Compute 营收、GPU ASP/型号占比、单卡 HBM 与供应参数形成缺口模型 | 先按紧张、紧平衡或充裕生成基础分，再乘公司 HBM 暴露系数 |
| 下游需求 | DRAM、NAND、HBM、HDD 的行业增速按公司收入结构加权 | `+12 / +6 / +2 / -5` |
| 技术节点 | 公司 DRAM 与 NAND 节点位置 | `0–7` |

HBM 主要供应商、部分涉及公司和不涉及公司的暴露系数分别为 `1.0`、`0.6`、`0.3`。因此 MU 的 HBM 供需影响不会原样套用到 WDC 或 STX。

### 第二层：最终研究信号

最终报告将各维度转换为 `0–100` 附近的子分，并按当前实现计算：

```text
S = 0.10 × 短期技术
  + 0.25 × 存储周期
  + 0.12 × 分析师
  + 0.08 × HBM供需
  + 0.08 × 下游需求
  + 0.08 × 内部人
  + 0.08 × 股东变动
  + 0.04 × 技术节点
  + 0.05 × 行业对标
  + 财务质量修正

最终研究信号 = clamp(S, 10, 95)
```

前九项是评分系数，财务质量修正则根据净利率、毛利率、ROE、负债率、PB 和 Beta 直接加减分。它们不是一套归一化到 100% 的资产定价权重。按当前实现，HBM、下游需求和技术节点既参与第一层存储周期判断，也以公司差异化子分进入第二层；报告会分别展示两层拆解。

| 最终研究信号 | 解释 |
| --- | --- |
| `65–95` | 研究指标整体较强，仍需复核数据新鲜度和模型假设 |
| `50–64` | 指标处于中间区间，重点核验周期拐点和缺失数据 |
| `35–49` | 多项指标偏弱，需要继续核验基本面和数据时点 |
| `10–34` | 风险或数据质量信号较多，优先检查数据完整性 |

研究信号只是在当前数据、来源和假设下对证据的可解释汇总，不是买卖建议、目标价、上涨概率或收益承诺。

## 评估方面

| 方面 | 关注内容 | 主要来源或方法 |
| --- | --- | --- |
| 短期技术 | RSI(14)、MACD Histogram、量比、MA5 方向 | `panda_data` 日线数据与 `utils/indicators.py` |
| 财务与估值 | 营收、净利率、毛利率、ROE、负债率、PE、PB、Beta | `panda_data` 财务与估值接口 |
| 库存周期 | 库存天数的方向、历史均值与周期阶段 | 季度库存和 COGS |
| DRAM/NAND 价格 | 合约价方向及公司毛利率是否确认 | 可引用行业资料与公司财务数据 |
| HBM/GPU | GPU 规格、Compute 营收、出货与型号占比、单卡 HBM、供需缺口 | NVIDIA/SEC/存储厂商官方披露与显式模型 |
| 下游需求 | DRAM、NAND、HBM、HDD 的终端结构及公司加权暴露 | 行业资料、公司业务结构与模型加权 |
| CapEx 与技术节点 | 扩产节奏、DRAM/NAND 节点位置 | 公司财务、公司披露和行业路线图 |
| 市场参与者 | 分析师共识、内部人交易、股东持仓变化 | `panda_data` 相关接口及公开申报衍生数据 |
| 行业对标 | 当前 PE 与已配置同行均值的相对位置 | `panda_data` 估值数据 |
| 数据质量 | 来源、截止日期、本轮核验时间、缺失、冲突和旧快照授权 | 行业刷新门禁与报告新鲜度面板 |
| 历史样本诊断 | 简化评分与后续 3/6/12 个月收益的 IC、分层收益和胜率 | 历史行情、财务及行业输入 |

历史模块使用与正式研究信号不同的简化评分，只做相关性诊断。样本数量、回填数据、时点不一致、幸存者偏差、过拟合和未计交易成本都会影响结果，不能据此证明策略有效或推断未来表现。

## Skill 特色

- **分析前刷新门禁**：每次正式分析先核验 `gpu_specs`、`nvda_compute_revenue`、`gpu_shipments`、`gpu_mix`、`hbm_supply`；刷新失败时必须由用户明确决定是否使用完整旧快照。
- **事实与估算分层**：官方事实、第三方行业资料和模型估算分别展示；模型保留输入、公式、假设、置信度和局限。
- **公司差异化**：按收入结构、HBM 暴露和实际技术节点调整 MU、SNDK、WDC、STX 的影响，避免用单一内存厂商模板覆盖 HDD 公司。
- **行业与公司交叉验证**：DRAM/NAND 合约价作为行业信号，公司毛利率趋势用于确认或修正周期判断。
- **来源与时点可追溯**：报告展示来源链接、`published_at`、`as_of`、`verified_at`、数据新鲜度和本轮使用模式。
- **本机安全登录**：Windows 使用可见 PowerShell，macOS 使用 Terminal.app；密码字符隐藏，凭据不进入聊天、HTML、文件、命令历史或日志。
- **交互式研究报告**：HTML 汇总行情、财务、估值、存储周期、HBM、下游、技术节点、同业对标、评分拆解和历史样本诊断。

## 快速开始

### 1. 安装依赖

本 Skill 使用 `panda_data` 获取行情、财务和估值数据；首次使用需安装 Python 依赖。

Windows PowerShell：

```powershell
cd D:\PandaAi_skills\.claude\skills\stock-memory-analyzer
python -m pip install -r requirements.txt
python analyze.py --check-deps
```

macOS Terminal：

```bash
cd /path/to/stock-memory-analyzer
python3 -m pip install -r requirements.txt
python3 analyze.py --check-deps
```

如遇网络或权限问题，请确认 Python 可以访问包仓库和 `panda_data` API 后重试。

### 2. 在本机临时窗口登录 panda_data

需要可用的 `panda_data` 账号才能生成正式报告。请勿在聊天中发送账号或密码；先在对话中选择一只股票，例如“分析 MU”。

在打开登录窗口之前，Skill 会从 NVIDIA、SEC、Micron、SK hynix、Samsung 和 TSMC 的国内外官方入口重新核验 GPU 规格、NVIDIA Compute 营收，并重新计算 GPU 出货量、型号占比和 HBM 供给估算。报告分别展示事实、模型估算、`as_of` 和本轮 `verified_at`。某个区域入口不可达时会尝试同一发布方的其他官方入口。

刷新失败时，Skill 会列出失败模块和上一份有效快照的日期，并询问是否允许本次使用旧数据。只有用户明确同意且旧快照完整有效时才继续；拒绝、未回复或没有有效旧快照都会停止，不会静默回退。

Skill 会在启动登录窗口前提示：

```text
由程序在本机提示输入账号并隐藏密码字符。Windows 将打开 PowerShell，macOS 将打开 Terminal.app。请在弹出的窗口完成输入，完成后窗口会自动关闭，我会继续检查报告结果。
```

随后程序会根据操作系统打开可见的临时窗口：Windows 使用 PowerShell，macOS 使用 Terminal.app。账号由用户在本机输入，密码字符隐藏。凭据仅存在于该子进程，不写入聊天、文件、HTML 报告、命令历史或程序日志；分析结束后会清除凭据并自动关闭窗口。

也可以从项目目录手动启动同一流程。

Windows：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_with_prompt.ps1 -Ticker MU -Period 5y -IndustryRunManifest output/runtime/industry_run.json
```

macOS：

```bash
bash scripts/run_with_prompt.sh --ticker MU --period 5y --industry-run-manifest output/runtime/industry_run.json
```

### 3. 生成 HTML 研究报告

在弹出的窗口完成登录后，脚本会自动分析所选股票并生成报告，无需再次输入命令。默认使用 5 年历史窗口。

如需其他已支持标的，将 `MU` 替换为 `SNDK`、`WDC` 或 `STX`。可选的历史窗口包括 `1y`、`2y`、`5y`、`10y` 和 `max`：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_with_prompt.ps1 -Ticker SNDK -Period 2y -IndustryRunManifest output/runtime/industry_run.json
```

```bash
bash scripts/run_with_prompt.sh --ticker SNDK --period 2y --industry-run-manifest output/runtime/industry_run.json
```

### 4. 查看报告

成功运行后，终端会输出报告路径，文件保存至 `output/`：

```text
output/MU_analysis_YYYYMMDD_HHMMSS.html
```

使用浏览器打开该 HTML 文件即可查看行情与财务概览、库存与价格周期、HBM / 下游需求、技术节点、同业对标、数据新鲜度提示及研究信号拆解。GPU/HBM 来源面板会展示官方链接、发布日期、数据截止期、本轮核验时间、估算公式和假设；使用旧快照时报告顶部会显示警告。报告中的估算和历史诊断均有局限说明，不代表未来表现。

## 常见问题

**提示缺少依赖怎么办？**

Windows 执行 `python -m pip install -r requirements.txt`；macOS 执行 `python3 -m pip install -r requirements.txt`。随后重新启动对应的 `run_with_prompt` 脚本。

**可以不登录直接使用公开网页数据吗？**

不可以。正式报告依赖 `panda_data` 的行情和基本面数据；未登录、依赖缺失或网络不可用时，Skill 会停留在设置阶段，不会用网页数据补成报告。

**密码会出现在报告或运行日志中吗？**

不会。密码输入字符在临时 PowerShell 或 Terminal.app 窗口中隐藏；Skill 与脚本禁止在聊天、报告、文件或日志中回显账号、密码和 token。请勿将凭据写入代码、配置文件或提交到仓库。

**macOS 第一次弹窗时为什么出现权限提示？**

macOS 可能首次请求允许当前应用自动化控制 Terminal.app；这是打开可见登录窗口所需的系统权限。拒绝后不会弹出窗口，可在“系统设置 → 隐私与安全性 → 自动化”中重新授权。

## 来源与维护

- 上游组织：[QuantSkills](https://github.com/quantskills)
- 上游仓库：[skill-stock-memory-analyzer-usa](https://github.com/quantskills/skill-stock-memory-analyzer-usa)
- 维护者：repository contributors

请勿提交账号密码、API key、私有数据集或其他敏感信息。使用第三方数据、代码、论文或报告时，请保留归因并遵守许可证。

## 运行时入口

`SKILL.md` 是 Codex 和 Claude Code 的主入口；Cursor 使用 [agents/cursor-rule.mdc](agents/cursor-rule.mdc)，Hermes 与 OpenClaw 使用 [agents/portable-loader.md](agents/portable-loader.md)。这些适配文件只负责加载同一份主规范，避免多处维护产生偏差。
