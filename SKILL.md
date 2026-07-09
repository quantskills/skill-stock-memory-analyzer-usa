---
name: stock-memory-analyzer
description: 美股存储芯片板块深度分析，集成库存周期/NAND-DRAM价格/HBM供需量化/下游需求拆分/技术节点路线图/行业对标/10维度公司差异化综合评分，生成带侧边目录导航的交互式 HTML 可视化报告
triggers:
  - 分析存储芯片股票
  - 分析美光/MU/西部数据/WDC/希捷/STX/SanDisk/SNDK 股票
  - 涉及NAND/DRAM/HBM/存储周期分析
  - 分析内存/存储板块
  - 生成存储芯片报告
---

# 美股存储芯片深度分析 Skill

你是美股存储芯片板块的深度分析助手。整合 **panda_data 实时股票数据** + **WebSearch 动态行业数据**，覆盖 7 大分析模块 + 10 维度公司差异化评分，生成带左侧目录导航的交互式 HTML 报告。

---

## 项目结构

```
stock-memory-analyzer/
├── SKILL.md                  # 本文件
├── analyze.py                # 主入口：编排分析流程
├── config/
│   └── industry_data.json   # 行业基准数据 + 公司业务结构（WebSearch 动态更新）
├── utils/
│   ├── fetcher.py           # 数据获取：panda_data API 封装
│   ├── indicators.py        # 技术指标：RSI/MACD/布林带/OBV/ATR/VaR
│   ├── memory_analyzer.py   # 存储行业分析：库存/价格/HBM/下游/技术节点/公司差异化评分
│   ├── report_builder.py    # HTML 报告生成：Plotly 可视化 + CSS + 侧边目录导航
│   └── data_updater.py      # 数据更新工具：CLI 写入 industry_data.json
└── output/                   # 报告输出目录
```

---

## 执行流程

### Step 0: 获取最新行业数据（⚠️ 每次必须执行）

**所有行业数据均来自 WebSearch 动态获取。** 每次分析前：

#### 0.1 检查新鲜度
```bash
cd d:\PandaAi_skills\.claude\skills\stock-memory-analyzer
python utils/data_updater.py freshness
```
9 个数据模块：🟢新鲜(≤7天) / 🟡陈旧(≤30天) / 🔴过期(>30天) / ⚪未知。

#### 0.2 动态更新所有模块

| 数据模块 | 搜索关键词 | 更新命令 |
|----------|-----------|----------|
| DRAM 合约价 | `DRAM contract price QoQ TrendForce` | `python utils/data_updater.py dram-price --data '<JSON>'` |
| NAND 合约价 | `NAND contract price QoQ TrendForce` | `python utils/data_updater.py nand-price --data '<JSON>'` |
| HBM 市场 | `HBM market size forecast TrendForce` | `python utils/data_updater.py hbm-market --data '<JSON>'` |
| NVDA Compute 营收 | `NVIDIA quarterly data center compute revenue FY2027` | `python utils/data_updater.py nvda-revenue --data '<JSON>'` |
| GPU 型号占比 | `NVIDIA H100 H200 B200 B300 GPU shipment mix` | `python utils/data_updater.py gpu-mix --data '<JSON>'` |
| HBM 供给参数 | `HBM wafer capacity supply growth SK Hynix Samsung Micron` | `python utils/data_updater.py hbm-supply --data '<JSON>'` |
| 下游需求 | `DRAM demand by end market server PC smartphone` | `python utils/data_updater.py downstream --data '<JSON>'` |
| CapEx 指引 | `Micron capex guidance FY2026 billions earnings call` | `python utils/data_updater.py capex --ticker MU --data '<JSON>'` |
| 技术节点 | `DRAM 1c nm 1d nm NAND 400-layer technology node roadmap` | `python utils/data_updater.py tech-nodes --data '<JSON>'` |

**搜索优先级**：① TrendForce/DRAMeXchange → ② Seeking Alpha / Tom's Hardware → ③ 公司财报

**搜索不到则保留现有值并标注日期，WebSearch 获取不到 GPU 型号占比/HBM 供给参数时可基于行业常识估算。**

#### 0.3 AI 推算补充
- NVDA **Compute 营收** ÷ 加权 **ASP** → GPU 出货量
- 公司财报 **inventory/COGS** → 库存周转天数
- 行业趋势 → 下游需求增速

### Step 1: 确认分析目标

| 名称 | Ticker | 业务定位 |
|------|--------|----------|
| 美光 | MU | DRAM 70% + NAND 25% + HBM 5%，HBM 主要供应商(~15%份额) |
| 西部数据 | WDC | NAND 55% + HDD 45%，不涉及 DRAM/HBM |
| 希捷 | STX | HDD 95% + NAND 5%，存储芯片暴露极低 |
| SanDisk | SNDK | 纯 NAND 厂商(90%)，从 WDC 分拆，不涉及 DRAM/HBM |
| SK 海力士 | 000660.KS | 韩股，panda_data 支持有限 |

### Step 2: 确认 panda_data 账号

从对话上下文获取，或环境变量：
```bash
set PANDA_DATA_USERNAME=86138xxxxxxx
set PANDA_DATA_PASSWORD=your_password
```

### Step 3: 运行分析

```bash
python analyze.py --ticker MU --username 86xxx --password xxx
python analyze.py --ticker MU,WDC,STX --username 86xxx --password xxx
```

### Step 4: 查看报告

`output/` 目录下 HTML 文件，浏览器打开即可。左侧固定目录导航，点击可跳转到任意模块。

---

## 报告结构 & 分析维度

### 报告导航

```
📋 报告目录（左侧固定侧边栏）
├── 概览
│   ├── 📊 KPI 仪表盘（10 项核心指标）
│   └── 📏 52周价格位置
├── 📈 通用分析（Tab 面板）
│   ├── 📊 技术走势（K线+MA+布林带）
│   ├── 📉 技术指标（RSI+MACD）
│   ├── 💰 财务趋势（营收/毛利/净利/资产）
│   ├── 📐 估值分析（PE/PB/PS/ROE+目标价）
│   └── 🏦 机构动向（前十大+分析师共识）
├── 💾 存储行业专属（垂直堆叠）
│   ├── 📦 库存 & 价格周期
│   ├── 📊 定价能力分析（毛利率趋势）
│   ├── 🚀 HBM GPU 需求量化（🔧公司差异化）
│   ├── 🎯 下游需求终端拆分（🔧公司差异化）
│   ├── 🔬 技术节点路线图（🔧公司差异化）
│   ├── 🎯 行业对标（雷达图）
│   └── 📋 公司事件（财务/IR/内部人/股东/评级）
└── 📋 综合评估（10维度评分详情）
```

### 公司差异化面板（🔧 标注）

以下三个面板根据公司业务结构个性化展示：

| 面板 | MU（存储巨头） | WDC（NAND+HDD） | STX（HDD为主） | SNDK（纯NAND） |
|------|--------------|----------------|---------------|---------------|
| 🚀 HBM | ✅ 主要供应商 15%份额，营收~$75亿 | ⚠️ 不涉及，SSD间接受益 | ⚠️ 不涉及 | ⚠️ 不涉及 |
| 🎯 下游 | 公司加权 +19.1%（DRAM×70%+NAND×25%+HBM×5%） | +11.1%（NAND×55%+HDD×45%） | +5.6%（HDD×95%） | +14.5%（NAND×90%） |
| 🔬 技术 | DRAM 领先(1c)+NAND 领先(400L+) | NAND 主流(BiCS 300L+) | 少量 NAND | NAND 主流(BiCS 300L+) |

**公司业务结构数据存储在 `industry_data.json` → `company_profiles`，可通过 WebSearch 更新。**

---

## 综合评分体系

### 两层评分架构

```
┌─ 综合评分（10维度）─────────────────────────────┐
│ = 短期技术(10%) + 存储周期(25%) + 分析师(12%)    │
│ + HBM供需(8%) + 下游需求(8%) + 内部人(8%)       │
│ + 股东(8%) + 技术节点(4%) + 对标(5%) + 财务(±25) │
│                                                   │
│ ┌─ 存储周期内部评分（6模块, 公司差异化）──────┐  │
│ │ = 库存(20%) + 价格(25%) + CapEx(15%)         │  │
│ │ + HBM供需(20%) + 下游需求(15%) + 技术(5%)    │  │
│ │                                               │  │
│ │ 🔧 HBM: 行业短缺×公司因子                     │  │
│ │     MU ×1.0 | SNDK/WDC/STX ×0.3              │  │
│ │ 🔧 下游: 行业增速×公司营收结构加权             │  │
│ │     MU: 70%×17.2+25%×16.1+5%×60=+19.1%      │  │
│ │     WDC: 55%×16.1+45%×5=+11.1%               │  │
│ │ 🔧 技术: 公司实际量产节点判定                  │  │
│ │     DRAM领先(1c/1d) +3分, NAND领先(400L+) +3分 │  │
│ └──────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────┘
```

### 评级区间

| 分数 | 评级 |
|------|------|
| ≥70 | 🟢 强烈看好 |
| 55-69 | 🟡 中性偏多 |
| 45-54 | ⚪ 中性 |
| 30-44 | 🟠 中性偏空 |
| <30 | 🔴 谨慎 |

### 四家公司评分估算

| Ticker | HBM因子 | 公司加权增速 | 技术定位 | 存储周期≈ | 综合≈ |
|--------|---------|-------------|----------|----------|------|
| MU | ×1.0 直接受益 | +19.1% | DRAM+NAND双领先 | 100 | ~85 |
| SNDK | ×0.3 间接受益 | +14.5% | NAND主流 | 84 | ~70 |
| WDC | ×0.3 间接受益 | +11.1% | NAND主流 | 84 | ~65 |
| STX | ×0.3 间接受益 | +5.6% | 少量NAND | 78 | ~55 |

---

## 数据来源

### 完整来源清单

| 类别 | 数据 | 来源 | 更新机制 |
|------|------|------|----------|
| 🟢 实时 | 行情 OHLCV | panda_data `get_us_daily` | 自动 |
| 🟢 实时 | 季度财务（营收/毛利/库存/COGS/CapEx） | panda_data `get_fina_ex` | 自动 |
| 🟢 实时 | 估值（PE/PB/PS/PEG/市值/Beta） | panda_data `mktfin_metric` + `pv_metric` | 自动 |
| 🟢 实时 | 机构持仓/内部人/分析师/股东 | panda_data 多接口 | 自动 |
| 🟡 动态 | DRAM/NAND 合约价 | WebSearch → TrendForce/DRAMeXchange | 每次更新 |
| 🟡 动态 | HBM 市场规模/份额 | WebSearch → TrendForce/Micron | 每次更新 |
| 🟡 动态 | NVDA GPU Compute 营收 | NVDA 季报（公开审计数据） | 每季更新 |
| 🟡 动态 | GPU 型号占比 | WebSearch → 供应链推断 | 每次更新 |
| 🟡 动态 | HBM 供给参数 | WebSearch → 晶圆产能估算 | 每次更新 |
| 🟡 动态 | 下游需求终端拆分 | WebSearch → TrendForce/IDC | 每次更新 |
| 🟡 动态 | CapEx 指引 | WebSearch → 公司财报 | 每季更新 |
| 🟡 动态 | 技术节点路线图 | WebSearch → 行业报告 | 每次更新 |
| ⚪ 静态 | 公司业务结构（revenue_mix/节点/定位） | industry_data.json → company_profiles | 不定期 |
| ⚪ 静态 | 对标公司列表 | industry_data.json → memory_peers | 不定期 |
| 🧮 模型 | 技术指标(RSI/MACD等) | indicators.py 标准公式 | — |
| 🧮 模型 | 评分权重 | memory_analyzer.py | — |

### HBM 需求推导链路

```
NVDA 季报 Compute 营收 ($B)           ← 公开审计数据 ✅
  ÷ 加权 GPU ASP ($K)                 ← 行业估算 ⚠️
  → GPU 季度出货量 (K)
  × 每卡 HBM 容量 (GB)                ← NVIDIA 官方规格 ✅
  × GPU 型号出货占比                   ← 行业估算 ⚠️
  → NVIDIA HBM 需求 (M GB)
  × 非 NVIDIA 因子 (1.30)             ← 行业估算 ⚠️
  → 全行业 HBM 需求 (M GB)
  vs 晶圆产能供给 (M GB)              ← 行业估算 ⚠️
  → 供需缺口判定（正=短缺, 负=盈余）
```

---

## CLI 命令速查

```bash
python utils/data_updater.py freshness              # 检查所有模块新鲜度
python utils/data_updater.py dram-price --data '{}'  # DRAM 价格
python utils/data_updater.py nand-price --data '{}'  # NAND 价格
python utils/data_updater.py hbm-market --data '{}'  # HBM 市场
python utils/data_updater.py nvda-revenue --data '{}' # NVDA 营收
python utils/data_updater.py gpu-mix --data '{}'     # GPU 型号占比
python utils/data_updater.py hbm-supply --data '{}'  # HBM 供给参数
python utils/data_updater.py downstream --data '{}'  # 下游需求
python utils/data_updater.py capex --ticker MU --data '{}'  # CapEx
python utils/data_updater.py tech-nodes --data '{}'  # 技术节点

python analyze.py --ticker MU --username 86xxx --password xxx  # 运行分析
```

---

## 网络要求 & 兼容性

- **panda_data API**：国内网络直接访问（86手机号注册）
- **Plotly.js CDN**：报告内引用 `cdn.plot.ly`，国内/国外均可访问
- **WebSearch**：分析前由 Claude 执行，需 Claude 有网络访问权限
- **报告输出**：纯静态 HTML 文件，离线也可打开（Plotly.js 首次需 CDN 加载）
- **Python 依赖**：`panda_data pandas numpy plotly`
