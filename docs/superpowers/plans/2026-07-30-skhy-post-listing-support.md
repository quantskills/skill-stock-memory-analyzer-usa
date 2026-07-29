# SKHY 上市后历史分析 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 支持 SK hynix 的 Nasdaq ADR `SKHY`，并严格限制所有个股历史分析使用 2026-07-10 之后的美股交易记录。

**Architecture:** 新建小型标的历史策略模块，集中定义上市日期、代码关系和历史可用性；`analyze.py` 在取得行情后立即执行截断。报告和回测使用同一个历史上下文，以展示可用区间和不可用原因，而不是从韩国原股补数据。

**Tech Stack:** Python 3、pandas、unittest、Plotly、JSON 配置、panda_data。

## Global Constraints

- `SKHY` 的唯一价格历史来源是 Nasdaq ADR；禁止使用或拼接 `000660.KS`。
- 上市日为 `2026-07-10`，过滤条件为日期大于或等于该日。
- 未满足窗口的指标必须返回空值与原因；不得使用 panda_data 的 52 周字段替代。
- 账号与密码不得写入代码、测试、报告或日志。
- 保持 MU、WDC、STX、SNDK 的现有行为不变。

---

### Task 1: 建立 SKHY 历史策略并以失败测试定义边界

**Files:**
- Create: `utils/ticker_policy.py`
- Create: `tests/test_ticker_policy.py`

**Interfaces:**
- Produces: `get_ticker_policy(ticker: str) -> dict`
- Produces: `filter_price_history(ticker: str, price_df: pd.DataFrame) -> pd.DataFrame`
- Produces: `build_history_context(ticker: str, price_df: pd.DataFrame) -> dict`

- [ ] **Step 1: 写失败测试**

```python
class TickerPolicyTests(unittest.TestCase):
    def test_skhy_filters_all_rows_before_nasdaq_listing(self):
        rows = pd.DataFrame({"Close": [100, 101, 102]}, index=pd.to_datetime(["2026-07-09", "2026-07-10", "2026-07-13"]))
        actual = filter_price_history("SKHY", rows)
        self.assertEqual(list(actual.index.strftime("%Y-%m-%d")), ["2026-07-10", "2026-07-13"])

    def test_skhy_context_marks_52_week_data_unavailable_before_252_sessions(self):
        rows = pd.DataFrame({"Close": range(20)}, index=pd.bdate_range("2026-07-10", periods=20))
        context = build_history_context("SKHY", rows)
        self.assertFalse(context["has_52_week_history"])
        self.assertEqual(context["listing_date"], "2026-07-10")
        self.assertIn("上市后交易日不足", context["unavailable_reasons"]["52_week"])
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m unittest tests.test_ticker_policy -v`  
Expected: FAIL，提示无法导入 `utils.ticker_policy`。

- [ ] **Step 3: 写最小实现**

```python
TICKER_POLICIES = {"SKHY": {"listing_date": "2026-07-10", "history_policy": "post_listing_only", "underlying_ticker": "000660.KS", "underlying_market": "KRX"}}

def filter_price_history(ticker, price_df):
    policy = get_ticker_policy(ticker)
    if not policy or policy.get("history_policy") != "post_listing_only":
        return price_df.copy()
    result = price_df.copy()
    result.index = pd.to_datetime(result.index)
    return result.loc[result.index >= pd.Timestamp(policy["listing_date"])]

def build_history_context(ticker, price_df):
    policy = get_ticker_policy(ticker)
    sessions = len(price_df)
    limited = bool(policy and policy.get("history_policy") == "post_listing_only")
    reasons = {} if not limited or sessions >= 252 else {"52_week": f"SKHY 自 {policy['listing_date']} 在 Nasdaq 上市，上市后交易日不足 252 个"}
    return {"ticker": ticker.upper(), "listing_date": policy.get("listing_date") if policy else None, "trading_days": sessions, "has_52_week_history": not limited or sessions >= 252, "unavailable_reasons": reasons}
```

- [ ] **Step 4: 运行测试并确认通过**

Run: `python -m unittest tests.test_ticker_policy -v`  
Expected: PASS。

- [ ] **Step 5: 提交**

Run: `git add utils/ticker_policy.py tests/test_ticker_policy.py && git commit -m "feat: 限制 SKHY 使用上市后历史"`

### Task 2: 将历史策略接入分析主流程

**Files:**
- Modify: `analyze.py:39-63,129-142,195-210,352-388`
- Modify: `tests/test_analyze_industry_gate.py`

**Interfaces:**
- Consumes: `filter_price_history()` 和 `build_history_context()`。
- Produces: `build_report(..., history_context=history_context)`。

- [ ] **Step 1: 写失败测试**

```python
@patch("analyze.fetch_stock_data")
@patch("analyze.filter_price_history")
def test_analyze_uses_filtered_prices_before_technicals(filter_history, fetch_prices):
    raw = _price_frame("2026-07-09", 2)
    filtered = _price_frame("2026-07-10", 1)
    fetch_prices.return_value = raw
    filter_history.return_value = filtered
    # 使用现有依赖 mock 调用 analyze_single("SKHY", "1y", ...)
    calc_technicals.assert_called_once_with(filtered)
    build_report.assert_called_once()
    self.assertEqual(build_report.call_args.kwargs["history_context"]["listing_date"], "2026-07-10")
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m unittest tests.test_analyze_industry_gate.AnalyzeIndustryGateTests.test_analyze_uses_filtered_prices_before_technicals -v`  
Expected: FAIL，`analyze` 尚未导入或调用历史策略函数。

- [ ] **Step 3: 写最小实现**

在 `fetch_stock_data()` 后依次执行：

```python
price_df = filter_price_history(ticker, price_df)
if price_df.empty:
    raise RuntimeError(f"{ticker} 上市后行情不可用，无法生成正式报告")
history_context = build_history_context(ticker, price_df)
```

仅当 `history_context["has_52_week_history"]` 为真时，允许 `pv_metric` 覆盖 `fiftyTwoWeekHigh` 和 `fiftyTwoWeekLow`；否则将二者置为 `None`。用截断后的 `price_df` 调用技术指标和回测，并传入 `history_context`。

- [ ] **Step 4: 运行测试并确认通过**

Run: `python -m unittest tests.test_analyze_industry_gate tests.test_ticker_policy -v`  
Expected: PASS。

- [ ] **Step 5: 提交**

Run: `git add analyze.py tests/test_analyze_industry_gate.py && git commit -m "feat: 在分析流程应用上市后历史边界"`

### Task 3: 让回测返回结构化的历史不足结果

**Files:**
- Modify: `utils/backtester.py:266-405`
- Create: `tests/test_backtester.py`

**Interfaces:**
- Produces: 不可回测时的 `{"available": False, "reason": str, "ticker": str, "listing_date": str | None, "trading_days": int}`。

- [ ] **Step 1: 写失败测试**

```python
def test_skhy_backtest_reports_post_listing_history_shortage(self):
    result = run_backtest("SKHY", _price_frame("2026-07-10", 30), {}, {})
    self.assertFalse(result["available"])
    self.assertEqual(result["listing_date"], "2026-07-10")
    self.assertIn("上市后历史不足", result["reason"])
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m unittest tests.test_backtester.BacktesterTests.test_skhy_backtest_reports_post_listing_history_shortage -v`  
Expected: FAIL，当前结果没有 `available`、`listing_date` 和 `trading_days`。

- [ ] **Step 3: 写最小实现**

在 `run_backtest()` 开头取得 `history_context = build_history_context(ticker, price_df)`；若 `SKHY` 的交易日不足以形成至少四个带前瞻收益观察期的点，返回：

```python
return {"available": False, "ticker": ticker.upper(), "listing_date": history_context["listing_date"], "trading_days": history_context["trading_days"], "reason": "SKHY 上市后历史不足，暂不提供历史回测"}
```

成功路径补充 `"available": True`，保留既有统计字段。

- [ ] **Step 4: 运行测试并确认通过**

Run: `python -m unittest tests.test_backtester tests.test_ticker_policy -v`  
Expected: PASS。

- [ ] **Step 5: 提交**

Run: `git add utils/backtester.py tests/test_backtester.py && git commit -m "feat: 标记 SKHY 上市后回测数据不足"`

### Task 4: 在报告中呈现历史边界和不可用模块

**Files:**
- Modify: `utils/report_builder.py:47-116,453-476,2497-2631`
- Create: `tests/test_report_builder_history.py`

**Interfaces:**
- Consumes: `history_context` 和 `backtest_result["available"]`。
- Produces: HTML 中的上市日、有效交易日、52 周不适用提示及回测不可用说明。

- [ ] **Step 1: 写失败测试**

```python
def test_report_labels_skhy_history_limits(self):
    html = build_report(ticker="SKHY", company_name="SK hynix", report_date="2026-07-30", price_df=_price_frame("2026-07-10", 20), fundamentals=_fundamentals(), technicals=_technicals(), peers={}, inv_analysis={}, price_cycle={}, capex_analysis={}, memory_assessment={}, history_context={"listing_date": "2026-07-10", "trading_days": 20, "has_52_week_history": False, "unavailable_reasons": {"52_week": "上市后交易日不足 252 个"}}, backtest_result={"available": False, "reason": "SKHY 上市后历史不足，暂不提供历史回测"})
    self.assertIn("SKHY 自 2026-07-10 在 Nasdaq 上市", html)
    self.assertIn("上市后交易日不足 252 个", html)
    self.assertIn("暂不提供历史回测", html)
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m unittest tests.test_report_builder_history -v`  
Expected: FAIL，`build_report` 当前没有 `history_context` 参数。

- [ ] **Step 3: 写最小实现**

为 `build_report()` 新增默认 `None` 的 `history_context` 参数。在 KPI 前添加数据边界卡；`_position_bar()` 接收历史上下文，在 `has_52_week_history=False` 时输出提示卡而不渲染 52 周区间。回测区块在 `available is False` 时渲染原因卡，在 `available is True` 时调用 `_fig_backtest_results()`；旧格式 `error` 也渲染安全说明。

- [ ] **Step 4: 运行测试并确认通过**

Run: `python -m unittest tests.test_report_builder_history tests.test_backtester -v`  
Expected: PASS。

- [ ] **Step 5: 提交**

Run: `git add utils/report_builder.py tests/test_report_builder_history.py && git commit -m "feat: 在报告说明 SKHY 历史可用性"`

### Task 5: 接入 SKHY 行业画像、对标和刷新门禁

**Files:**
- Modify: `utils/industry_refresh.py:64,293-297,517-525`
- Modify: `config/industry_data.json:86-116,189-211,413-468`
- Modify: `tests/test_industry_gate.py`
- Create: `tests/test_industry_config.py`
- Modify: `README.md`
- Modify: `README.en.md`

**Interfaces:**
- Produces: `SUPPORTED_TICKERS` 包含 `SKHY`。
- Produces: `memory_peers.dram_focused` 使用 `SKHY` 作为可计算同行。

- [ ] **Step 1: 写失败测试**

```python
def test_skhy_can_claim_a_fresh_industry_manifest(self):
    with tempfile.TemporaryDirectory() as tmp:
        runtime = Path(tmp)
        promote_snapshot(valid_candidate(), runtime, ticker="SKHY", now=NOW)
        manifest = precheck_run_manifest(runtime / "industry_run.json", "SKHY", now=NOW)
        self.assertEqual(manifest["ticker"], "SKHY")

def test_skhy_profile_and_adr_peer_are_configured(self):
    data = json.loads(Path("config/industry_data.json").read_text(encoding="utf-8"))
    self.assertIn("SKHY", data["company_profiles"])
    self.assertIn("SKHY", data["capex_guidance"])
    self.assertIn("SKHY", [peer["ticker"] for peer in data["memory_peers"]["dram_focused"]])
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m unittest tests.test_industry_gate tests.test_industry_config -v`  
Expected: FAIL，`SKHY` 不在 `SUPPORTED_TICKERS` 和行业配置中。

- [ ] **Step 3: 写最小实现**

将白名单扩展为 `{"MU", "SNDK", "WDC", "STX", "SKHY"}`。在 `dram_focused` 中以 `SKHY` 作为可计算海力士条目，并添加 `underlying_ticker: "000660.KS"`、`underlying_market: "KRX"` 的说明字段。新增 `SKHY` 公司画像与 CapEx 指引并注明来源日期；更新中英文 README 的支持列表、ADR 历史边界和数据不足规则。

- [ ] **Step 4: 运行测试并确认通过**

Run: `python -m unittest tests.test_industry_gate tests.test_industry_config tests.test_skill_contract -v`  
Expected: PASS。

- [ ] **Step 5: 提交**

Run: `git add utils/industry_refresh.py config/industry_data.json tests/test_industry_gate.py tests/test_industry_config.py README.md README.en.md && git commit -m "feat: 接入 SKHY 行业画像与对标"`

### Task 6: 完整回归与实际数据覆盖验证

**Files:**
- Modify if needed: `README.md`, `README.en.md`
- Do not commit: `output/` 生成报告和运行日志。

- [ ] **Step 1: 运行完整自动化测试**

Run: `python -m unittest discover -s tests -v`  
Expected: PASS，且不存在凭据输出。

- [ ] **Step 2: 验证依赖和运行入口**

Run: `python analyze.py --check-deps`  
Expected: 依赖检查通过或只报告可操作的缺失依赖。

- [ ] **Step 3: 在可见临时终端运行 SKHY**

Run: `powershell -ExecutionPolicy Bypass -File scripts/run_with_prompt.ps1 -Ticker SKHY -IndustryRunManifest output/runtime/industry_run.json`  
Expected: 仅在本机窗口输入账号和隐藏密码；报告使用 `SKHY`，不写入凭据。

- [ ] **Step 4: 人工检查 HTML**

确认报告具备上市日边界卡、交易日数量、52 周不适用提示、回测数据不足卡、SKHY 画像和美股 ADR 对标；确认不存在 `000660.KS` 价格序列或伪造长期指标。

- [ ] **Step 5: 提交文档修正并汇报**

Run: `git add README.md README.en.md && git commit -m "docs: 说明 SKHY 上市后历史限制" && git status --short`

最终汇报应列出：通过的自动化测试、实际可覆盖与缺失的 panda_data 接口、报告文件路径，以及确认 `output/` 和凭据未提交。

## 自检

- 设计中的每项边界均在任务 1-5 有对应实现和测试。
- 不含任何未决或待补充的占位描述。
- 所有新接口名称、参数和返回字段在前序任务中已定义。
- 计划不要求修改未相关的 `.claude/` 未跟踪目录。
