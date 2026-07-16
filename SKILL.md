---
name: stock-memory-analyzer
description: 对 MU、SNDK、WDC、STX 等美股存储公司开展基于 panda_data 的可追溯研究分析，结合行情、财务、估值、DRAM/NAND/HBM 供需、库存、CapEx、技术节点和同业对标，生成交互式 HTML 研究报告。当用户提到存储芯片、内存、NAND、DRAM、HBM、存储周期，或要求研究这些美股公司时使用。首次响应列出可分析标的并要求用户明确选择一只；确认后先从国内外官方来源刷新 GPU/HBM 五个必需模块，通过校验或取得本轮旧数据授权后，才在 Windows 打开可见的临时 PowerShell，或在 macOS 打开可见的 Terminal.app，由程序在本机提示输入账号并隐藏密码字符。不默认选择标的，不把模型估算写成官方事实。本技能仅用于研究与教育，不提供买卖建议、收益承诺或个性化投资建议。
license: GPL-3.0-only
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-stock-memory-analyzer-usa
  repository_url: https://github.com/quantskills/skill-stock-memory-analyzer-usa
  project_type: skill
  collection: analysis
  license: GPL-3.0-only
  project_status: community_project_unreviewed
  maintainer: repository contributors
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "补充希望研究的存储周期、财务、估值、HBM、NAND、HDD 或同业对标问题"
  },
  "fields": [
    {
      "key": "symbol",
      "label": "美股代码",
      "type": "select",
      "required": true,
      "options": [
        { "value": "MU", "label": "MU｜Micron Technology" },
        { "value": "SNDK", "label": "SNDK｜Sandisk" },
        { "value": "WDC", "label": "WDC｜Western Digital" },
        { "value": "STX", "label": "STX｜Seagate Technology" }
      ]
    },
    {
      "key": "period",
      "label": "历史窗口",
      "type": "select",
      "default": "5y",
      "options": [
        { "value": "1y", "label": "近 1 年" },
        { "value": "3y", "label": "近 3 年" },
        { "value": "5y", "label": "近 5 年" },
        { "value": "10y", "label": "近 10 年" }
      ]
    },
    {
      "key": "focus",
      "label": "研究重点",
      "type": "text",
      "placeholder": "如：HBM 供需、NAND 价格周期、数据中心 HDD、CapEx"
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}请准备分析美股存储公司 {{symbol}}，历史窗口为 {{period}}。{{#focus}}研究重点：{{focus}}。{{/focus}}正式分析前必须完成 panda_data 环境预检与登录验证；不得记录、复述或写入任何凭据，登录失败时停止且不以网页数据替代。验证成功后区分 panda_data 事实、带日期来源的公开行业资料和明确标注的模型估算，披露数据新鲜度、缺失项、评分假设与回测局限，输出中文 HTML 研究报告。"
}
```

# 美股存储芯片研究分析

使用本技能研究美股存储产业链公司，输出可复核的行业与公司分析。它将可用数据分成三类：

- `panda_data`：行情、财务、估值及公开申报衍生数据；以接口实际返回时间为准。
- 已引用的公开行业资料：DRAM/NAND 合约价、HBM、下游需求、CapEx、技术节点等；每个关键结论须保留来源和日期。
- 模型推算：例如 GPU ASP、HBM 供给或收入暴露度；必须明确标为估算，说明输入、假设和局限，不可写成已验证事实。

项目状态：这是一个社区项目，尚未获得 QUANTSKILLS 官方认证、验证、背书或生产可用认定。

## 研究边界

- 仅生成研究信息，不给出“买入、卖出、建仓、减仓、止损、目标价”或保证收益等指令。
- 将评分解释为“当前数据下的研究信号”，而非投资评级、概率预测或交易信号。
- 不把模型估算、分析师观点或历史回测当作事实或未来表现保证。
- 不要求、也不接受用户在聊天中发送 `panda_data` 用户名或密码。凭据必须由用户在程序打开的本机临时终端窗口中输入：Windows 使用 PowerShell，macOS 使用 Terminal.app；密码输入字符隐藏。凭据仅存在于该子进程，分析结束后清除，且不得写入回复、评论、报告、文件、代码、命令历史、标准输出或错误日志。
- 数据缺失、冲突、过期或无法核验时，应明确写出限制；不得用行业常识补成精确数值。

## 支持范围

当前版本只分析下列已配置并需要通过 `panda_data` 获取行情与基本面数据的美股。不要臆测其他代码可用，也不要因为用户提到其他公司而跳过登录检查。

| 代码 | 公司 | 分类 | 分析侧重点 |
| --- | --- | --- | --- |
| `MU` | Micron Technology | DRAM / HBM / NAND | 内存价格周期、HBM、数据中心与资本开支 |
| `SNDK` | Sandisk | NAND / 闪存 | NAND、企业级 SSD、数据中心与价格周期 |
| `WDC` | Western Digital | HDD 存储基础设施 | 大容量 HDD、云与数据中心存储；不将 HBM 结论直接套用 |
| `STX` | Seagate Technology | HDD 存储基础设施 | 大容量 HDD、云与数据中心存储；不将 HBM 结论直接套用 |

若需要研究不在此表中的美股，先向用户说明当前 Skill 未配置该标的，不得假定 `panda_data` 支持它；只有维护者扩展配置和数据验证后，才可纳入。

输出为 `output/` 下的 HTML 研究报告。报告包含行情与财务概览、库存与价格周期、供需与技术节点、同业对标、数据质量提示、评分拆解与回测诊断（数据足够时）。

## 首轮交互：标的确认、行业刷新与本机弹窗登录

当用户第一次提出“分析美股存储芯片”“分析存储股”或没有明确给出单一代码的请求时，按以下顺序回应：

1. 明确说明正式分析依赖 `panda_data`，公开网页只用于刷新行业输入，不代替行情、财务和估值数据。
2. 展示上方四只可分析股票的代码、公司和分类，要求用户选择一只。即便用户说“分析整个行业”或未指定代码，也不能默认选择 `MU`。
3. 用户确认代码后，先告知“正在从国内外官方来源刷新 GPU/HBM 行业数据”，然后执行下文的五模块刷新；此阶段不读取或请求 `panda_data` 凭据。
4. 刷新成功时创建一次性行业运行清单；刷新失败时按“刷新失败与旧数据决策”处理，未获得明确授权前不得打开登录窗口。
5. 行业门禁通过后，在对话中告知用户：“由程序在本机提示输入账号并隐藏密码字符。Windows 将打开 PowerShell，macOS 将打开 Terminal.app。请在弹出的窗口完成输入，完成后窗口会自动关闭，我会继续检查报告结果。”
6. 识别当前操作系统并打开可见的临时终端窗口。窗口再次预检行业清单和 Python 依赖，之后才提示账号和隐藏密码。不得要求用户在聊天中发送凭据，也不得将凭据拼接进命令行。
7. 若窗口返回依赖缺失，向用户说明并取得安装授权；安装后需要重新刷新或重新授权行业清单，再启动窗口。若窗口完成分析，继续检查 `output/` 中的报告。

首轮回复使用以下结构，确保用户看见前置条件和可选范围：

```text
要开始正式分析，需要通过 panda_data 获取数据。账号和密码无需在聊天中发送；确认股票后，Windows 会打开 PowerShell，macOS 会打开 Terminal.app，供你在本机输入，密码字符会隐藏。

当前可分析的美股：
- MU — Micron Technology：DRAM / HBM / NAND
- SNDK — Sandisk：NAND / 闪存
- WDC — Western Digital：HDD 存储基础设施
- STX — Seagate Technology：HDD 存储基础设施

请从上方选择一只代码。确认后我会先刷新 GPU/HBM 一手行业数据；刷新通过后再根据操作系统打开本机登录窗口。
```

不要在首轮回复中追加市场观点、新闻摘要、行情、排名、研究评分或投资结论。这样可以避免将未验证的公开信息误当成 `panda_data` 的正式研究输入。

## 每次分析的一手行业数据刷新

每次正式分析都刷新以下五个必需模块：

| 模块 | 类型 | 规则 |
| --- | --- | --- |
| `gpu_specs` | 事实 | NVIDIA 官方型号、HBM 类型、容量、带宽和产品状态 |
| `nvda_compute_revenue` | 事实 | NVIDIA IR 最新报告期，并尽量用 SEC 交叉核验 |
| `gpu_shipments` | 模型估算 | 官方 Compute 营收为锚，ASP 为显式假设，输出范围和置信度 |
| `gpu_mix` | 模型估算 | 官方产品与量产状态为锚，型号占比总和必须为 1 |
| `hbm_supply` | 模型估算 | Micron、SK hynix、Samsung、TSMC 官方披露为锚，输出范围、公式和局限 |

优先使用以下国内外官方入口，并按 `as_of` 或财务报告期判断新旧，不按搜索排序或响应先后选择：

- NVIDIA：`nvidia.com`、`docs.nvidia.com`、`investor.nvidia.com`、`nvidia.cn`、`developer.nvidia.cn`；
- 监管：`sec.gov`；
- Micron：`investors.micron.com`、`micron.com`、`micron.cn`；
- SK hynix：`news.skhynix.com`、`skhynix.com.cn`；
- Samsung：`news.samsung.com`、`samsung.com/global/ir`；
- TSMC：`investor.tsmc.com`、`tsmc.com/schinese`。

某个国内入口不可达时尝试同一发布方的全球入口，反向亦然；不要求用户配置 VPN 或代理。只接受官方域名，重定向后的最终 URL 也必须校验。`published_at`、`as_of`、`accessed_at`、`verified_at` 分别记录，不得互相替代。稳定规格只要本轮重新核验，就更新 `verified_at`，不能仅因原发布时间较早提示“过时”。

联网读取后，将候选快照写到 `output/runtime/industry_candidate.json`。候选必须符合 `docs/superpowers/specs/2026-07-16-primary-source-industry-refresh-design.md` 的结构；每条来源还必须记录 `region`、`language`、`source_type`、`final_url`、`evidence` 和 `retrieved_this_run: true`。不要把网页正文、账号、密码或 token 写入候选或日志。

先验证，再提交：

```powershell
python utils/industry_refresh.py validate --candidate output/runtime/industry_candidate.json
python utils/industry_refresh.py commit --candidate output/runtime/industry_candidate.json --ticker MU
```

将 `MU` 替换为本轮已经确认的代码。验证或提交失败时，不得修改上一份有效快照，不得打开登录窗口。

### 刷新失败与旧数据决策

若任一模块的官方来源不可达、字段缺失、发生无法解释的冲突或估算契约不完整，在聊天中列出失败模块、错误类别、上一份有效快照的 `as_of`/`verified_at` 及影响，然后询问：

```text
本次未能完整刷新以下行业数据：[模块列表]。现有旧数据截至 [日期]，来源为 [来源摘要]。
是否允许本次使用旧数据继续分析？报告会明确标记旧数据及其影响。
```

- 用户明确同意且存在完整有效快照时，执行一次性授权：

```powershell
python utils/industry_refresh.py authorize-current --refresh-id <本次失败刷新ID> --ticker MU --failed-module gpu_specs
```

  多个失败模块重复添加 `--failed-module`。授权只绑定当前代码、失败刷新 ID 和一次分析。
- 用户拒绝、用户未回复或表达不明确：停止并等待，不默认继续。
- 没有完整有效快照：即使用户同意也停止，不能混合旧快照与本轮半成品。

## 环境预检与登录验证

手动检查依赖时可运行平台对应的命令。

Windows：

```powershell
cd D:\PandaAi_skills\.claude\skills\stock-memory-analyzer
python analyze.py --check-deps
```

macOS：

```bash
cd /path/to/stock-memory-analyzer
python3 analyze.py --check-deps
```

正常执行时无需在隐藏终端预检；两个 `run_with_prompt` 入口都会在可见窗口中先检查 `panda_data`、`pandas`、`numpy`、`plotly`，再请求凭据并验证网络。若依赖或网络未就绪，停止在设置阶段并告知具体缺失项；不得开始分析、不得回退到网页数据，也不得生成半成品报告。

缺少 Python 依赖时，先说明缺少项并取得用户同意，再安装：

```powershell
python -m pip install -r requirements.txt
```

```bash
python3 -m pip install -r requirements.txt
```

Windows 入口：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_with_prompt.ps1 -Ticker MU -Period 5y -IndustryRunManifest output/runtime/industry_run.json
```

macOS 入口：

```bash
bash scripts/run_with_prompt.sh --ticker MU --period 5y --industry-run-manifest output/runtime/industry_run.json
```

Windows 入口启动 `WindowStyle Normal` 的 PowerShell 子进程，并以 `SecureString` 读取密码。macOS 入口通过 `osascript` 打开 Terminal.app，并以 Bash `read -s` 隐藏密码；父脚本使用不含凭据的临时状态文件等待子窗口完成。两种入口都只在子进程内临时设置环境变量，结束时清除凭据并自动关闭窗口。父进程随后检查 `output/` 中最新报告并向用户交付结果。登录失败时仅报告“登录失败”或网络/权限类别，不能输出底层异常原文；网络或防火墙错误不能直接归因于密码错误。

启动脚本退出码用于父进程判断下一步：`0` 表示分析完成；`2` 表示账号或密码未输入；`3` 表示依赖缺失；`4` 表示未找到 Python 3；`5` 表示行业快照或一次性清单未通过；其他非零值表示登录、网络或分析运行失败。退出码不包含凭据。

## 工作流程

### 1. 确认单一标的与行业运行清单

只有同时满足以下两项时，才进入分析：

- 用户从支持清单中明确指定一只代码，例如 `MU`；
- 五个必需行业模块已刷新成功，或用户明确授权本轮使用上一份完整有效快照；
- 可见的本机临时终端窗口已通过行业门禁与依赖检查，并且用户已在该窗口完成 `panda_data` 登录。

如果用户一次给出多个代码，先请其选择本轮优先分析的一只；多标的横向对比只能在完成至少一只单标的分析后，并获得用户明确要求时进行。默认历史窗口为 `5y`，但这只是在上述条件满足后才适用，绝不是可跳过标的确认的默认选择。

### 2. 检查其余静态行业数据质量

```powershell
python utils/data_updater.py freshness
```

GPU/HBM 五模块的新鲜度来自本轮快照的 `verified_at` 和运行模式；该命令仅检查 DRAM、NAND、下游需求、CapEx、技术节点和对标公司等其余静态模块。任何陈旧、过期、缺失或未知的数据都必须在最终结论中可见；它不能支撑强结论或精确排名。

默认分析不会改写 `config/industry_data.json`。只有用户明确要求更新行业数据，并且已提供或允许获取可引用的公开来源时，才更新该文件。

### 3. 更新行业数据（仅在获授权时）

GPU/HBM 五个运行模块只使用公司或监管一手资料。DRAM/NAND 合约价、下游需求等其余静态行业模块可使用 TrendForce、DRAMeXchange、IDC、Gartner 等可复核资料；二手报道只能作为佐证，不能覆盖一手披露。

每次更新前记录以下信息，并在报告中呈现：

| 字段 | 要求 |
| --- | --- |
| 数据项 | 例如 DRAM 合约价 QoQ、HBM 市场规模或 CapEx 指引 |
| 来源 | 发布方、标题或文件名、可访问链接 |
| 日期 | 发布日期、数据截至日期、访问日期 |
| 类型 | 事实、管理层指引、第三方预测或模型估算 |
| 变换 | 单位、换算、加权或任何推导公式 |

若无法提供来源或日期，保留原值并标记“不足以更新”。模型估算必须保留输入和假设；不要把估算值与公司披露混合成单一事实。

常用更新入口：

```powershell
python utils/data_updater.py freshness
python utils/data_updater.py dram-price --data '{"2026-Q2": 0.0}' --source 'https://example.com/source' --as-of 2026-06-30
python utils/data_updater.py nand-price --data '{"2026-Q2": 0.0}' --source 'https://example.com/source' --as-of 2026-06-30
python utils/data_updater.py hbm-market --data '{}' --source 'https://example.com/source' --as-of 2026-06-30
python utils/data_updater.py capex --ticker MU --data '{}' --source 'https://example.com/source' --as-of 2026-06-30
python utils/data_updater.py tech-nodes --data '{"dram": [], "nand": []}' --source 'https://example.com/source' --as-of 2026-06-30
```

命令示例中的 URL、日期和数值都只是结构示例，绝不是建议写入的数据。`--source` 与 `--as-of` 是必填项；写入前用已核验资料替换，工具会把来源、截至日期和访问日期保存到对应配置段。

### 4. 运行分析

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File scripts/run_with_prompt.ps1 -Ticker MU -Period 5y -IndustryRunManifest output/runtime/industry_run.json
```

```bash
# macOS
bash scripts/run_with_prompt.sh --ticker MU --period 5y --industry-run-manifest output/runtime/industry_run.json
```

脚本会获取可用的价格、财务、估值、公开申报衍生数据和行业配置，并生成 HTML。若某个接口失败，保留该维度为空或“不可用”；不要用未经验证的替代数据填补。

### 5. 审阅并交付报告

交付报告链接时，同时简短说明：

1. 行情数据的最新日期和报告生成日期；
2. 有哪些行业模块陈旧、缺失或由模型估算；
3. 最重要的两到三个研究发现及其来源类别；
4. 本报告仅供研究与教育，不构成投资建议。

不要把运行日志中的内部变量当成对外结论。报告中的综合分数也只能作为模型的可解释汇总，必须连同数据新鲜度、权重和局限一起阅读。

## 报告与评分解释

报告按以下顺序组织：概览、KPI 与价格位置、技术与财务、库存与价格周期、HBM 与下游需求、技术节点、同业对标、公开事件、评分拆解与回测诊断。

评分使用 0–100 的研究信号刻度：

| 区间 | 表述 | 含义 |
| --- | --- | --- |
| 70–100 | 较强 | 多个已披露或已引用的指标偏正面，仍须核验估算和风险 |
| 55–69 | 偏强 | 正面与不确定因素并存 |
| 45–54 | 中性 | 证据不足以形成明确方向 |
| 30–44 | 偏弱 | 多个指标偏负面或数据质量较低 |
| 0–29 | 较弱 | 风险、缺失或负面信号占主导 |

评分权重、输入数据、公司差异化系数和缺失项处理应在报告中披露。不要根据分数生成交易动作、仓位或价格目标。

## 回测的正确使用

回测只用于检查历史样本中评分与后续收益的关系。报告必须显示样本区间、样本数、可用前瞻期、简化评分与实际报告评分的差异，以及数据可得性限制。

特别注意：该回测样本有限，行业数据存在回填和估算，可能有幸存者偏差、数据修订、时点不一致、过拟合以及未计交易成本/税费/滑点等问题。IC、IR、分层收益和模拟结果均不代表未来表现，也不能证明策略有效。

## 目录结构

```text
stock-memory-analyzer/
├── SKILL.md                 # 技能声明、流程、边界与元数据
├── README.md                # 项目简介与社区状态
├── README.en.md             # English project overview
├── LICENSE                  # GPL-3.0-only
├── analyze.py               # 分析入口
├── requirements.txt         # Python 依赖
├── config/industry_data.json # 行业基准、来源和更新日期
├── scripts/
│   ├── run_with_prompt.ps1   # Windows PowerShell 本机安全登录入口
│   └── run_with_prompt.sh    # macOS Terminal.app 本机安全登录入口
├── utils/
│   ├── preflight.py         # 依赖、凭据和网络预检
│   ├── industry_refresh.py  # 一手行业快照验证、门禁和一次性授权
│   ├── fetcher.py           # panda_data 接口封装
│   ├── data_updater.py      # 行业数据更新与新鲜度检查
│   ├── indicators.py        # 技术指标与风险统计
│   ├── memory_analyzer.py   # 存储行业分析与研究信号
│   ├── backtester.py        # 历史诊断回测
│   └── report_builder.py    # HTML 报告生成
├── agents/
│   ├── cursor-rule.mdc      # Cursor 运行时入口
│   └── portable-loader.md   # Hermes / OpenClaw 运行时入口
└── output/                  # 本地生成的报告，不应提交敏感数据
```

## 已知限制与维护

- `panda_data` 覆盖范围、字段含义和更新时间以实际接口返回为准。
- Windows 弹窗依赖 `powershell.exe`；macOS 弹窗依赖 Terminal.app、`osascript`、Bash 和 Python 3，并可能首次请求自动化控制 Terminal 的系统权限。
- 行业数据可能需要人工核验；付费报告的非公开内容不能作为可复现来源。
- 部分 HBM、GPU 出货和产能数据是模型估算，结论对假设敏感。
- 存储周期高度波动，历史关系可能失效；不要将本项目表述为已验证或生产可用。
- 修改第三方代码、数据、论文或报告时，须保留来源、许可证和改动说明。

维护者应定期检查来源链接、更新日期、过期数据提示和依赖兼容性。提交前确认仓库不含账号、密码、API key、私有数据集或其他敏感信息。
