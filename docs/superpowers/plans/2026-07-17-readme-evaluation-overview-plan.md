# README Evaluation Overview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在中文 `README.md` 中准确公开当前两层研究信号逻辑、评估维度、分数解释和 Skill 特色，并用契约测试防止文档回退。

**Architecture:** 不修改分析算法。先扩展 `tests/test_skill_contract.py`，让测试读取 `README.md` 并验证必须出现的结构和边界；确认测试因 README 尚未包含这些内容而失败后，再把与 `utils/memory_analyzer.py`、`utils/report_builder.py` 和 `utils/backtester.py` 对齐的说明插入“支持标的”和“快速开始”之间。

**Tech Stack:** Markdown、Python 3、标准库 `unittest`

## Global Constraints

- 只修改中文 `README.md` 和 `tests/test_skill_contract.py`；不修改评分算法、数据抓取逻辑、HTML 报告或 `README.en.md`。
- 使用“研究信号”，不使用“投资评级”“上涨概率”或交易指令。
- 区分百分比系数与直接加减分；不宣称最终公式的前九项归一化为 100%。
- 明确 HBM、下游需求和技术节点按当前实现同时出现在内层存储周期评分与外层最终研究信号中。
- 历史样本诊断只说明相关性检查，不表述为策略收益证明。
- 不写入账号、密码、token、私有数据或 `output/` 运行时内容。

---

### Task 1: 增加 README 评估逻辑契约并补全文档

**Files:**
- Modify: `tests/test_skill_contract.py`
- Modify: `README.md`（插入到“支持标的”之后、“快速开始”之前）

**Interfaces:**
- Consumes: `README.md` 的 UTF-8 Markdown 文本；`utils/memory_analyzer.py` 的存储周期评分公式；`utils/report_builder.py` 的最终研究信号公式；`utils/backtester.py` 的历史样本诊断输出。
- Produces: `SkillContractTests.test_readme_explains_evaluation_model`，以及 README 中可由该测试定位的评估说明章节。

- [ ] **Step 1: 写入会失败的 README 契约测试**

在 `setUpClass` 中同时读取 README：

```python
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")
```

在 `test_chat_never_requests_credentials` 之后添加：

```python
    def test_readme_explains_evaluation_model(self):
        required_sections = (
            "## 核心评估逻辑",
            "### 第一层：存储周期评分",
            "### 第二层：最终研究信号",
            "## 评估方面",
            "## Skill 特色",
        )
        for section in required_sections:
            self.assertIn(section, self.readme)

        for formula_term in (
            "0.10 × 短期技术",
            "0.25 × 存储周期",
            "0.12 × 分析师",
            "财务质量修正",
            "clamp(S, 10, 95)",
        ):
            self.assertIn(formula_term, self.readme)

        self.assertIn("不是买卖建议、目标价、上涨概率或收益承诺", self.readme)
        self.assertIn("相关性诊断", self.readme)
```

- [ ] **Step 2: 运行单个测试并确认 RED**

Run:

```powershell
python -m unittest tests.test_skill_contract.SkillContractTests.test_readme_explains_evaluation_model -v
```

Expected: `FAIL`，失败信息包含 `## 核心评估逻辑 not found`，证明测试能捕获 README 当前缺少评估说明的问题。

- [ ] **Step 3: 在 README 中写入最小完整说明**

在支持标的说明末尾、`## 快速开始` 之前插入以下 Markdown：

```markdown
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
```

- [ ] **Step 4: 运行单个测试并确认 GREEN**

Run:

```powershell
python -m unittest tests.test_skill_contract.SkillContractTests.test_readme_explains_evaluation_model -v
```

Expected: `Ran 1 test`，结果为 `OK`。

- [ ] **Step 5: 运行完整测试集与文档检查**

Run:

```powershell
python -m unittest discover -s tests -v
git diff --check
```

Expected: 全部测试为 `OK`；`git diff --check` 无空白错误。人工确认新增 Markdown 位于“支持标的”和“快速开始”之间，公式词项与代码一致，且 README 不含真实凭据或运行时数据。

- [ ] **Step 6: 提交实现**

```powershell
git add README.md tests/test_skill_contract.py
git commit -m "docs: 补充存储股评估逻辑与特色"
```
