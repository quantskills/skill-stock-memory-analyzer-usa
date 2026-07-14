---
name: stock-memory-analyzer
description: 对 MU、美光、WDC、STX、SNDK 等美股存储芯片公司开展可追溯的研究分析，结合 panda_data 行情与财务数据、DRAM/NAND/HBM 供需、库存、CapEx、技术节点和同业对标，生成交互式 HTML 研究报告。当用户提到存储芯片、内存、NAND、DRAM、HBM、存储周期，或要求研究上述公司时使用；即使用户只要求比较这些公司、核验行业数据或生成存储行业报告，也应使用。本技能仅用于研究与教育，不提供买卖建议、收益承诺或个性化投资建议。
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
- 不收集、不回显、不写入报告的密码、token、手机号或其他敏感信息。凭据只可通过环境变量在本地会话提供。
- 数据缺失、冲突、过期或无法核验时，应明确写出限制；不得用行业常识补成精确数值。

## 支持范围

默认覆盖 `MU`、`WDC`、`STX`、`SNDK`；其他代码只有在 `panda_data` 能返回足够的行情和财务数据时才分析。对非 DRAM/HBM 公司，应降低或标记 HBM 维度的重要性，不能把行业结论直接套用为公司结论。

输出为 `output/` 下的 HTML 研究报告。报告包含行情与财务概览、库存与价格周期、供需与技术节点、同业对标、数据质量提示、评分拆解与回测诊断（数据足够时）。

## 首次使用：环境预检

先运行：

```powershell
cd D:\PandaAi_skills\.claude\skills\stock-memory-analyzer
python analyze.py --check-env
```

预检检查 `panda_data`、`pandas`、`numpy`、`plotly`、本地凭据和网络要求。缺少 Python 依赖时，先说明缺少项并取得用户同意，再安装：

```powershell
python -m pip install -r requirements.txt
# 或在用户明确同意后：
python analyze.py --install-deps --check-env
```

使用环境变量提供凭据，避免把秘密放进命令历史、源代码或报告：

```powershell
$env:PANDA_DATA_USERNAME = 'your_username'
$env:PANDA_DATA_PASSWORD = 'your_password'
python analyze.py --ticker MU
```

只有用户明确同意将凭据传入命令行时，才可使用 `--username` 和 `--password`。网络或防火墙错误应报告为访问问题，不能直接归因于密码错误。

## 工作流程

### 1. 确认任务与输出

确认股票代码、比较对象、时间跨度，以及用户想回答的问题（例如库存拐点、HBM 暴露、估值对标或风险）。若用户没有指定，默认分析单一股票、使用 `5y` 历史窗口，并输出研究报告。

### 2. 先检查行业数据质量

```powershell
python utils/data_updater.py freshness
```

把每个行业模块标记为“新鲜、陈旧、过期、缺失或未知”。任何陈旧、过期、缺失或未知的数据都必须在最终结论中可见；它不能支撑强结论或精确排名。

默认分析不会改写 `config/industry_data.json`。只有用户明确要求更新行业数据，并且已提供或允许获取可引用的公开来源时，才更新该文件。

### 3. 更新行业数据（仅在获授权时）

优先使用一手资料：公司财报、IR 新闻稿、SEC 文件、产品规格和公开方法说明。行业数据可使用 TrendForce、DRAMeXchange、IDC、Gartner 等公开可访问资料；二手报道只能作为佐证。

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
python analyze.py --ticker MU
python analyze.py --ticker MU,WDC,STX --period 5y
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
├── utils/
│   ├── preflight.py         # 依赖、凭据和网络预检
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
- 行业数据可能需要人工核验；付费报告的非公开内容不能作为可复现来源。
- 部分 HBM、GPU 出货和产能数据是模型估算，结论对假设敏感。
- 存储周期高度波动，历史关系可能失效；不要将本项目表述为已验证或生产可用。
- 修改第三方代码、数据、论文或报告时，须保留来源、许可证和改动说明。

维护者应定期检查来源链接、更新日期、过期数据提示和依赖兼容性。提交前确认仓库不含账号、密码、API key、私有数据集或其他敏感信息。
