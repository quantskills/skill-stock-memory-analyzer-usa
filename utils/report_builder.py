"""
HTML 报告生成模块 - 基于 Plotly + 纯 CSS 生成交互式分析报告
"""
import json
import math
from datetime import datetime
from html import escape
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _sfmt(val, fmt_spec=".2f", default="--"):
    """安全格式化数值，处理 None/NaN"""
    if val is None:
        return default
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return default
        return format(v, fmt_spec)
    except (ValueError, TypeError):
        return default


def _sfmt_dollar(val, default="--"):
    """格式化美元金额"""
    v = _sfmt(val, ".2f", None)
    if v is None or v == "--":
        return default
    return f"${v}"


def _sfmt_pct(val, default="--"):
    """格式化百分比 - panda_data sector_median 返回的已是百分比值 (46.6 = 46.6%)"""
    v = _sfmt(val, ".2f", None)
    if v is None or v == "--":
        return default
    fv = float(v)
    return f"{fv:.1f}%"


def build_report(ticker: str, company_name: str, report_date: str,
                 price_df: pd.DataFrame, fundamentals: dict,
                 technicals: dict, peers: dict,
                 inv_analysis: dict, price_cycle: dict,
                 capex_analysis: dict, memory_assessment: dict,
                 institutional: dict = None,
                 fin_events: list = None,
                 ir_events: list = None,
                 insider_trades: list = None,
                 shareholder_reports: list = None,
                 recommendation: dict = None,
                 hbm_demand: dict = None,
                 end_market: dict = None,
                 tech_position: dict = None,
                 data_freshness: dict = None,
                 hbm_exposure: dict = None,
                 backtest_result: dict = None,
                 industry_data: dict = None) -> str:
    """
    生成完整 HTML 报告

    Returns:
        完整的 HTML 字符串
    """
    info = fundamentals.get("info", {})

    sections = []

    # 1. HTML 头部
    sections.append(_html_head(company_name, ticker, report_date))

    # 2. 报告标题
    sections.append(_report_header(company_name, ticker, report_date, info))

    # 2.5 数据新鲜度提示
    sections.append(_data_freshness_bar(data_freshness))
    sections.append(_industry_provenance_bar(industry_data))

    # 3. KPI 仪表盘
    sections.append('<div id="sec-kpi">' + _kpi_dashboard(info, technicals, price_df) + '</div>')

    # 4. 52周位置指示
    sections.append('<div id="sec-position">' + _position_bar(info) + '</div>')

    # 5. 通用分析 Tab 面板
    sections.append('<div id="sec-general">' + _general_analysis_tabs(price_df, fundamentals, technicals, info, institutional) + '</div>')

    # 6. 存储行业专属 Tab 面板
    sections.append('<div id="sec-memory">' + _memory_specific_tabs(price_df, fundamentals, inv_analysis, price_cycle,
                                          capex_analysis, peers,
                                          fin_events, ir_events, insider_trades, shareholder_reports,
                                          recommendation, hbm_demand, end_market, tech_position,
                                          hbm_exposure, ticker) + '</div>')

    # 7. 综合评估底部
    sections.append('<div id="sec-assessment">' + _assessment_footer(memory_assessment, inv_analysis, price_cycle,
                                       technicals, info, fundamentals, recommendation,
                                       insider_trades, shareholder_reports, peers, capex_analysis,
                                       hbm_demand, end_market, tech_position, ticker) + '</div>')

    # 8. 回测结果
    if backtest_result and "error" not in backtest_result:
        sections.append(_fig_backtest_results(backtest_result))

    # 9. HTML 尾部
    sections.append(_html_footer())

    return "\n".join(sections)


def _html_head(company_name: str, ticker: str, report_date: str) -> str:
    """HTML 头部：CSS + Plotly.js"""
    css = """
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html { scroll-behavior: smooth; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #0f1419; color: #e1e8ed; line-height: 1.6;
            max-width: 1400px; margin: 0 auto; padding: 20px; padding-left: 235px;
        }

        /* 侧边栏目录 */
        .toc-sidebar {
            position: fixed; top: 0; left: 0; width: 210px; height: 100vh;
            background: #111922; border-right: 1px solid #2a3a4a;
            overflow-y: auto; z-index: 100; padding: 12px 0;
        }
        .toc-sidebar h3 {
            color: #90caf9; font-size: 0.85rem; padding: 8px 14px;
            border-bottom: 1px solid #2a3a4a; margin-bottom: 6px;
        }
        .toc-sidebar a {
            display: block; padding: 5px 14px; font-size: 0.78rem;
            color: #8899aa; text-decoration: none; border-left: 2px solid transparent;
            transition: all 0.15s;
        }
        .toc-sidebar a:hover { color: #e1e8ed; background: rgba(255,255,255,0.04); }
        .toc-sidebar a.active { color: #90caf9; border-left-color: #90caf9; background: rgba(144,202,249,0.08); }
        .toc-sidebar .toc-group { color: #556677; font-size: 0.72rem; padding: 10px 14px 2px; text-transform: uppercase; letter-spacing: 0.5px; }
        @media (max-width: 900px) {
            .toc-sidebar { display: none; }
            body { padding-left: 20px; }
        }

        .report-header {
            text-align: center; padding: 30px 20px;
            margin-bottom: 24px;
        }
        .report-header h1 { font-size: 2rem; margin-bottom: 4px; color: #fff; }
        .report-header .subtitle { color: #90caf9; font-size: 0.9rem; }
        .report-header .disclaimer { color: #64b5f6; font-size: 0.75rem; margin-top: 8px; }

        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px; margin-bottom: 24px;
        }
        @media (max-width: 900px) {
            .kpi-grid { grid-template-columns: repeat(3, 1fr); }
        }
        @media (max-width: 500px) {
            .kpi-grid { grid-template-columns: repeat(2, 1fr); }
        }
        .kpi-card {
            background: #1a2332; border-radius: 12px; padding: 16px;
            border: 1px solid #2a3a4a; text-align: center;
        }
        .kpi-card .label { font-size: 0.75rem; color: #8899aa; margin-bottom: 4px; }
        .kpi-card .value { font-size: 1.3rem; font-weight: 700; color: #e1e8ed; }
        .kpi-card .change { font-size: 1.3rem; }
        .kpi-card .change.positive { color: #4caf50; }
        .kpi-card .change.negative { color: #f44336; }
        .kpi-card .change.neutral { color: #ff9800; }

        .position-bar-container {
            background: #1a2332; border-radius: 12px; padding: 20px;
            border: 1px solid #2a3a4a; margin-bottom: 24px;
        }
        .position-bar-container h3 { font-size: 0.85rem; color: #8899aa; margin-bottom: 10px; }
        .position-bar-outer {
            height: 8px; background: #2a3a4a; border-radius: 4px;
            position: relative; margin-bottom: 8px;
        }
        .position-bar-inner {
            height: 8px; border-radius: 4px;
            background: linear-gradient(90deg, #f44336 0%, #ff9800 30%, #4caf50 70%, #2196f3 100%);
            transition: width 0.5s ease;
        }
        .position-bar-labels {
            display: flex; justify-content: space-between; font-size: 0.7rem; color: #8899aa;
        }

        .section-title {
            font-size: 1.1rem; font-weight: 700; margin-bottom: 16px;
            color: #90caf9; border-bottom: 2px solid #1a237e; padding-bottom: 8px;
        }

        .tabs-container { margin-bottom: 24px; }
        .tab-buttons { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
        .tab-btn {
            padding: 8px 16px; border: 1px solid #2a3a4a; border-radius: 8px;
            background: #1a2332; color: #8899aa; cursor: pointer;
            font-size: 0.85rem; transition: all 0.2s;
        }
        .tab-btn:hover { background: #2a3a4a; color: #e1e8ed; }
        .tab-btn.active { background: #1a237e; color: #fff; border-color: #3949ab; }
        .tabs-container { position: relative; }
        .tab-panel {
            display: block !important;
            max-height: none; overflow: visible;
            transition: max-height 0.01s;
        }
        .tab-panel.hidden {
            max-height: 0; overflow: hidden;
        }

        .plot-container {
            background: #1a2332; border-radius: 12px; padding: 16px;
            border: 1px solid #2a3a4a; margin-bottom: 16px;
        }

        .two-col {
            display: grid; grid-template-columns: 1fr 1fr;
            gap: 24px;
        }
        @media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }

        .assessment-footer {
            background: #1a2332; border: 1px solid #2a3a4a;
            border-radius: 16px; padding: 28px; margin-top: 24px;
            font-size: 1.1rem; line-height: 1.7;
        }
        .assessment-footer h2 { color: #fff; font-size: 1.6rem; margin-bottom: 16px; }
        .assessment-footer h3 { color: #90caf9; font-size: 1.2rem; }
        .assessment-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
        }
        .assessment-item {
            background: rgba(255,255,255,0.08); border-radius: 10px;
            padding: 12px; color: #e1e8ed; font-size: 0.85rem;
        }
        .assessment-item .signal-tag {
            display: inline-block; padding: 2px 8px; border-radius: 4px;
            font-size: 0.75rem; margin-right: 4px;
        }
        .signal-bullish { background: #4caf50; color: #fff; }
        .signal-bearish { background: #f44336; color: #fff; }
        .signal-neutral { background: #ff9800; color: #fff; }

        .footer-disclaimer {
            text-align: center; padding: 20px; color: #556677; font-size: 0.75rem;
            border-top: 1px solid #2a3a4a; margin-top: 24px;
        }

        .highlight-table {
            width: 100%; border-collapse: collapse; font-size: 0.85rem;
        }
        .highlight-table th {
            text-align: left; color: #90caf9; border-bottom: 1px solid #2a3a4a;
            padding: 8px;
        }
        .highlight-table td {
            padding: 8px; border-bottom: 1px solid #1a2a3a;
        }
    </style>
    <!-- Plotly.js: 国际CDN + 国内CDN回退，确保国内外均可加载 -->
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"
        onerror="var s=document.createElement('script');s.src='https://cdn.bootcdn.net/ajax/libs/plotly.js/2.35.2/plotly.min.js';document.head.appendChild(s);">
    </script>
    """
    toc = f"""
    <nav class="toc-sidebar">
        <h3>📋 {ticker} 报告目录</h3>
        <div class="toc-group">概览</div>
        <a href="#sec-kpi">📊 KPI 仪表盘</a>
        <a href="#sec-position">📏 52周位置</a>
        <div class="toc-group">通用分析</div>
        <a href="#sec-general">📈 技术/财务/估值</a>
        <div class="toc-group">存储专属</div>
        <a href="#sec-memory">💾 行业专属分析</a>
        <a href="#sec-inventory">📦 库存 & 价格周期</a>
        <a href="#sec-margin">📊 定价能力分析</a>
        <a href="#sec-hbm">🚀 HBM GPU 需求量化</a>
        <a href="#sec-downstream">🎯 下游需求终端拆分</a>
        <a href="#sec-tech-node">🔬 技术节点路线图</a>
        <a href="#sec-peer">🎯 行业对标</a>
        <div class="toc-group">事件 & 评级</div>
        <a href="#sec-events">📋 财务事件/内部人/股东/评级</a>
        <div class="toc-group">评估</div>
        <a href="#sec-assessment">📋 综合评估</a>
        <a href="#sec-backtest">📈 历史回测</a>
    </nav>"""
    return f"<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n<title>{ticker} 存储芯片深度分析报告</title>\n{css}\n</head>\n<body>\n{toc}"


def _report_header(company_name: str, ticker: str, report_date: str, info: dict) -> str:
    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")
    return f"""
    <div class="report-header">
        <h1>💾 美股存储芯片深度分析报告</h1>
        <div class="subtitle">{company_name} ({ticker}) | {report_date} | {sector} / {industry}</div>
        <div class="disclaimer">🤖 本报告由 AI 自动生成，仅供研究与教育；模型评分、估算和回测不构成投资建议或收益承诺</div>
    </div>
    <div style="background:#1a2332; border:1px solid #2a3a4a; border-radius:10px; padding:14px 18px; margin-bottom:20px; font-size:0.78rem; color:#8899aa; line-height:1.8;">
        <div style="color:#90caf9; font-weight:700; margin-bottom:6px;">📡 数据来源声明</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:4px 20px;">
            <div>📊 <b style='color:#e1e8ed;'>行情/财务/估值</b> — panda_data API (实时)</div>
            <div>🏦 <b style='color:#e1e8ed;'>机构/内部人/分析师</b> — panda_data API (实时)</div>
            <div>💰 <b style='color:#e1e8ed;'>DRAM/NAND 合约价</b> — 配置中的公开来源与截至日期</div>
            <div>🚀 <b style='color:#e1e8ed;'>HBM 市场/份额</b> — 配置中的公开来源或估算</div>
            <div>🔧 <b style='color:#e1e8ed;'>NVDA GPU 营收</b> — 公开财报或配置记录</div>
            <div>📐 <b style='color:#e1e8ed;'>GPU 型号占比/ASP</b> — 行业估算，需结合假设阅读</div>
            <div>🏭 <b style='color:#e1e8ed;'>CapEx 指引</b> — 公司公开披露或配置记录</div>
            <div>🔬 <b style='color:#e1e8ed;'>技术节点路线图</b> — 公司披露/行业资料或配置记录</div>
            <div>📦 <b style='color:#e1e8ed;'>下游需求拆分</b> — 行业资料或配置记录</div>
            <div>📏 <b style='color:#e1e8ed;'>HBM 供给参数</b> — 模型估算，非公司披露</div>
            <div>🧮 <b style='color:#e1e8ed;'>技术指标/评分权重</b> — 模型内置算法</div>
            <div>🏷️ <b style='color:#e1e8ed;'>对标公司列表</b> — 静态维护</div>
        </div>
    </div>"""


def _data_freshness_bar(freshness: dict = None) -> str:
    """行业数据新鲜度提示条"""
    if not freshness:
        return ""

    stale_items = []
    for key, info in freshness.items():
        if info.get("status") in ("stale", "outdated", "missing", "unknown"):
            icon = {"stale": "🟡", "outdated": "🔴", "missing": "⚫", "unknown": "⚪"}.get(info["status"], "⚪")
            age = f"{info['age_days']}天前" if info.get("age_days") else "未知时间"
            stale_items.append(f"{icon} {info['label']} ({age})")

    if not stale_items:
        return ""

    items_html = " | ".join(stale_items)
    return f"""
    <div style="background:#332200; border:1px solid #ff9800; border-radius:8px; padding:10px 16px; margin-bottom:20px; font-size:0.8rem;">
        <span style="color:#ff9800; font-weight:700;">⚠️ 行业数据可能过时：</span>
        <span style="color:#e1e8ed;">{items_html}</span>
        <span style="color:#8899aa; margin-left:12px;">请先核验来源和截至日期，再据此解读结论</span>
    </div>"""


def _industry_provenance_bar(industry_data: dict = None) -> str:
    """展示行业输入的来源记录，避免把配置值误读为无条件的实时事实。"""
    if not industry_data:
        return ""

    gpu_specs = industry_data.get("gpu_hbm_specs", {})
    sections = [
        ("DRAM 合约价", industry_data.get("dram_contract_price_qoq", {})),
        ("NAND 合约价", industry_data.get("nand_contract_price_qoq", {})),
        ("HBM 市场", industry_data.get("hbm_market", {})),
        ("GPU 出货", gpu_specs.get("quarterly_gpu_shipments_k", {})),
        ("GPU 型号占比", gpu_specs.get("gpu_mix_ratios", {})),
        ("HBM 供给参数", gpu_specs.get("hbm_supply_params", {})),
        ("下游需求", industry_data.get("downstream_demand", {})),
        ("CapEx 指引", industry_data.get("capex_guidance", {})),
        ("技术节点", industry_data.get("technology_nodes", {})),
    ]

    rows = []
    for label, section in sections:
        if not isinstance(section, dict):
            section = {}
        source = section.get("_source") or "未记录来源"
        as_of = section.get("_as_of") or "未记录截至日期"
        source_html = escape(str(source), quote=True)
        if source_html.startswith(("https://", "http://")):
            source_html = f"<a href='{source_html}' target='_blank' rel='noopener noreferrer'>{source_html}</a>"
        rows.append(f"<div>• <b>{escape(label)}</b>：{source_html}（截至 {escape(str(as_of))}）</div>")

    return f"""
    <details style="background:#17202b; border:1px solid #2a3a4a; border-radius:8px; padding:10px 14px; margin:-8px 0 20px; font-size:0.75rem; color:#8899aa;">
        <summary style="color:#90caf9; cursor:pointer;">🔎 行业输入来源与截至日期（点击展开）</summary>
        <div style="display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:4px 16px; margin-top:8px;">{''.join(rows)}</div>
        <div style="margin-top:8px; color:#556677;">“未记录”表示该配置不能视为可复核的最新行业事实；模型估算应结合假设单独解读。</div>
    </details>"""


def _kpi_dashboard(info: dict, technicals: dict, price_df: pd.DataFrame) -> str:
    """KPI 仪表盘 - 5列 x 2行 = 10指标 (基于 get_fina_ex 真实财务数据)"""
    price = _sfmt(info.get("currentPrice") or info.get("regularMarketPrice"), ".2f", "--")
    price_str = f"${price}" if price != "--" else "--"

    gm = info.get("grossMargins");       gm_str = _sfmt_pct(gm)
    nm = info.get("profitMargins");      nm_str = _sfmt_pct(nm)
    roe = info.get("returnOnEquity");    roe_str = _sfmt_pct(roe)
    de = info.get("debtToEquity");       de_str = _sfmt(de, ".2f") if de else "--"
    rev = info.get("latestRevenue");     rev_str = f"${rev/1e9:.1f}B" if rev else "--"
    ni = info.get("latestNetIncome");    ni_str = f"${ni/1e9:.1f}B" if ni else "--"
    tp = info.get("targetMeanPrice");    tp_str = _sfmt_dollar(tp, "--")

    returns = technicals.get("returns_summary", {})
    def _chg_class(val):
        if val is None: return "neutral", "--"
        if val > 0: return "positive", f"+{val}%"
        if val < 0: return "negative", f"{val}%"
        return "neutral", "0%"
    c1m_cls, c1m_str = _chg_class(returns.get("1M"))
    c3m_cls, c3m_str = _chg_class(returns.get("3M"))

    # 市值
    mkt_cap = info.get("marketCap")
    mkt_str = f"${mkt_cap/1e12:.2f}T" if mkt_cap and mkt_cap > 1e12 else (f"${mkt_cap/1e9:.1f}B" if mkt_cap else "--")

    # PE / PB / Beta
    pe = info.get("trailingPE");        pe_str = _sfmt(pe, ".1f")
    pb = info.get("priceToBook");       pb_str = _sfmt(pb, ".2f")
    beta = info.get("beta");            beta_str = _sfmt(beta, ".2f")

    cards = [
        ("股价", price_str),
        ("市值", mkt_str),
        ("PE (TTM)", pe_str),
        ("PB", pb_str),
        ("Beta (5Y)", beta_str),
        ("毛利率", gm_str),
        ("净利率", nm_str),
        ("ROE", roe_str),
        ("1月涨跌", f'<span class="change {c1m_cls}">{c1m_str}</span>'),
        ("3月涨跌", f'<span class="change {c3m_cls}">{c3m_str}</span>'),
    ]

    rows = []
    for label, value in cards:
        rows.append(
            f'<div class="kpi-card">'
            f'<div class="label">{label}</div>'
            f'<div class="value">{value}</div>'
            f'</div>'
        )

    return f'<div class="kpi-grid">{"".join(rows)}</div>'


def _position_bar(info: dict) -> str:
    """52周位置指示条"""
    low = info.get("fiftyTwoWeekLow")
    high = info.get("fiftyTwoWeekHigh")
    price = info.get("currentPrice") or info.get("regularMarketPrice")

    if not all([low, high, price]) or not all(isinstance(x, (int, float)) for x in [low, high, price]):
        return ""

    pct = (price - low) / (high - low) * 100 if high != low else 50
    pct = max(0, min(100, pct))

    return f"""
    <div class="position-bar-container">
        <h3>📏 52周价格位置</h3>
        <div class="position-bar-outer">
            <div class="position-bar-inner" style="width:{pct:.0f}%"></div>
        </div>
        <div class="position-bar-labels">
            <span>52周低 ${low:.2f}</span>
            <span>当前位置 {pct:.0f}%</span>
            <span>52周高 ${high:.2f}</span>
        </div>
    </div>"""


def _general_analysis_tabs(price_df: pd.DataFrame, fundamentals: dict,
                           technicals: dict, info: dict,
                           institutional: dict = None) -> str:
    """通用分析 Tab 面板"""
    figs = _build_general_figures(price_df, fundamentals, technicals, info, institutional)

    tabs_html = ""
    for i, (title, fig_html) in enumerate(figs):
        tabs_html += f'<div class="tab-panel active" id="gen-tab-{i}" data-tab-group="gen" data-tab-index="{i}">{fig_html}</div>'

    buttons = ""
    for i, (title, _) in enumerate(figs):
        active = "active" if i == 0 else ""
        buttons += f'<button class="tab-btn {active}" onclick="switchTab(\'gen\', {i}, {len(figs)})">{title}</button>'

    return f"""
    <div class="section-title">📈 通用分析</div>
    <div class="tabs-container">
        <div class="tab-buttons">{buttons}</div>
        {tabs_html}
    </div>"""


def _build_general_figures(price_df, fundamentals, technicals, info, institutional=None):
    """构建通用分析的所有图表"""
    figs = []

    # Tab1: 技术走势 (K线 + MA)
    figs.append(("📊 技术走势", _fig_price_with_ma(price_df, technicals)))

    # Tab2: 技术指标 (RSI + MACD)
    figs.append(("📉 技术指标", _fig_rsi_macd(price_df, technicals)))

    # Tab3: 财务趋势
    figs.append(("💰 财务趋势", _fig_financial_trend(fundamentals)))

    # Tab4: 估值分位
    figs.append(("📐 估值分析", _fig_valuation(info, technicals)))

    # Tab5: 机构动向
    figs.append(("🏦 机构动向", _fig_institutional(info, institutional)))

    return figs


def _fig_price_with_ma(df: pd.DataFrame, technicals: dict) -> str:
    """K线 + 均线图"""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03, row_heights=[0.7, 0.3],
        subplot_titles=("股价 & 均线", "成交量")
    )

    # K线
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="K线", increasing_line_color="#4caf50", decreasing_line_color="#f44336"
    ), row=1, col=1)

    # 均线
    ma_colors = {"ma_5": "#ffeb3b", "ma_20": "#ff9800", "ma_50": "#2196f3", "ma_200": "#e91e63"}
    for ma_key, color in ma_colors.items():
        if ma_key in technicals:
            fig.add_trace(go.Scatter(
                x=df.index, y=technicals[ma_key],
                mode="lines", line=dict(width=1.5, color=color),
                name=f"MA{ma_key.split('_')[1]}"
            ), row=1, col=1)

    # 布林带
    if "bb_upper" in technicals:
        fig.add_trace(go.Scatter(
            x=df.index, y=technicals["bb_upper"],
            mode="lines", line=dict(width=0.5, color="#555", dash="dash"),
            name="BB上轨", showlegend=False
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=technicals["bb_lower"],
            mode="lines", line=dict(width=0.5, color="#555", dash="dash"),
            fill="tonexty", fillcolor="rgba(100,100,100,0.1)",
            name="BB下轨", showlegend=False
        ), row=1, col=1)

    # 成交量
    colors = ["#4caf50" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#f44336" for i in range(len(df))]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"],
        name="成交量", marker_color=colors,
        showlegend=False, opacity=0.6
    ), row=2, col=1)

    # rangeslider: 主图初始显示最近120天, slider覆盖全量, 避免拖动反弹
    total_len = len(df)
    view_start = df.index[max(0, total_len - 120)]
    view_end = df.index[total_len - 1]
    slider_start = df.index[0]
    slider_end = df.index[total_len - 1]

    fig.update_layout(
        template="plotly_dark", height=600,
        paper_bgcolor="#1a2332", plot_bgcolor="#1a2332",
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(
            range=[view_start, view_end],
            rangeslider=dict(visible=True, thickness=0.06,
                            range=[slider_start, slider_end],
                            bordercolor="#2a3a4a", borderwidth=1),
            type="date"
        ),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )

    fig.update_yaxes(title_text="价格 ($)", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)

    return fig.to_html(full_html=False, include_plotlyjs=False, config={'displaylogo': False, 'modeBarButtonsToRemove': ['zoom2d','pan2d','select2d','lasso2d','zoomIn2d','zoomOut2d','resetScale2d','hoverClosestCartesian','hoverCompareCartesian','toggleSpikelines'], 'displayModeBar': True})


def _fig_rsi_macd(df: pd.DataFrame, technicals: dict) -> str:
    """RSI + MACD 副图"""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.05, row_heights=[0.5, 0.5],
        subplot_titles=("RSI(14)", "MACD")
    )

    # RSI
    if "rsi_14" in technicals:
        rsi = technicals["rsi_14"]
        fig.add_trace(go.Scatter(
            x=df.index, y=rsi, mode="lines",
            line=dict(color="#ff9800", width=1.5), name="RSI(14)"
        ), row=1, col=1)
        # 超买超卖线
        fig.add_hline(y=70, line_dash="dash", line_color="#f44336", opacity=0.5, row=1, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#4caf50", opacity=0.5, row=1, col=1)
        fig.update_yaxes(range=[0, 100], row=1, col=1)

    # MACD
    if "macd_line" in technicals:
        fig.add_trace(go.Scatter(
            x=df.index, y=technicals["macd_line"], mode="lines",
            line=dict(color="#2196f3", width=1.5), name="MACD"
        ), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=technicals["macd_signal"], mode="lines",
            line=dict(color="#e91e63", width=1), name="Signal"
        ), row=2, col=1)
        # 柱状图
        hist = technicals["macd_hist"]
        colors_hist = ["#4caf50" if v >= 0 else "#f44336" for v in hist]
        fig.add_trace(go.Bar(
            x=df.index, y=hist, marker_color=colors_hist,
            name="Histogram", opacity=0.5, showlegend=False
        ), row=2, col=1)
        fig.add_hline(y=0, line_color="#555", line_width=0.5, row=2, col=1)

    fig.update_layout(
        template="plotly_dark", height=450,
        paper_bgcolor="#1a2332", plot_bgcolor="#1a2332",
        margin=dict(l=20, r=20, t=30, b=20),
        hovermode="x unified",
        autosize=True,
    )
    # Full-width display
    return fig.to_html(full_html=False, include_plotlyjs=False, config={'displaylogo': False, 'modeBarButtonsToRemove': ['zoom2d','pan2d','select2d','lasso2d','zoomIn2d','zoomOut2d','resetScale2d','hoverClosestCartesian','hoverCompareCartesian','toggleSpikelines'], 'displayModeBar': True})


def _fig_financial_trend(fundamentals: dict) -> str:
    """财务趋势图 - 基于 get_fina_ex 季度数据"""
    fin = fundamentals.get("financials", {})

    if not fin:
        return "<div class='plot-container'><p style='color:#8899aa;'>暂无财务数据</p></div>"

    # 按 fy_period 排序
    sorted_periods = sorted(fin.keys())
    labels = [p.replace("FY", "FY ") for p in sorted_periods]

    revenues = [fin[p].get("revenue") or 0 for p in sorted_periods]
    gross_profits = [fin[p].get("gross_profit") or 0 for p in sorted_periods]
    net_incomes = [fin[p].get("net_income") or 0 for p in sorted_periods]
    ebitdas = [fin[p].get("ebitda") or 0 for p in sorted_periods]

    # 转为 $B
    rev_b = [abs(r) / 1e9 for r in revenues]
    gp_b = [abs(g) / 1e9 for g in gross_profits]
    ni_b = [abs(n) / 1e9 for n in net_incomes]
    eb_b = [abs(e) / 1e9 for e in ebitdas]

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("营收 & 毛利 & 净利", "毛利率 & 净利率", "营收增速 (YoY Q对比)", "资产 & 权益"),
        vertical_spacing=0.15, horizontal_spacing=0.1
    )

    # 1. 营收 + 毛利 + 净利
    fig.add_trace(go.Bar(x=labels, y=rev_b, name="营收 ($B)", marker_color="#2196f3"), row=1, col=1)
    fig.add_trace(go.Scatter(x=labels, y=gp_b, mode="lines+markers",
                             name="毛利", line=dict(color="#4caf50", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=labels, y=ni_b, mode="lines+markers",
                             name="净利", line=dict(color="#ff9800", width=2)), row=1, col=1)

    # 2. 毛利率 & 净利率
    gm_pct = [g / r * 100 if r > 0 else 0 for g, r in zip(gross_profits, revenues)]
    nm_pct = [n / r * 100 if r > 0 else 0 for n, r in zip(net_incomes, revenues)]
    fig.add_trace(go.Scatter(x=labels, y=gm_pct, mode="lines+markers",
                             name="毛利率 %", line=dict(color="#4caf50", width=2)), row=1, col=2)
    fig.add_trace(go.Scatter(x=labels, y=nm_pct, mode="lines+markers",
                             name="净利率 %", line=dict(color="#ff9800", width=2)), row=1, col=2)
    fig.add_hline(y=0, line_color="#555", line_width=0.5, row=1, col=2)
    fig.update_yaxes(title_text="%", row=1, col=2)

    # 3. 营收增速 (同季度对比)
    yoy_labels = []
    yoy_growth = []
    for i in range(4, len(sorted_periods)):
        curr_rev = revenues[i]
        prev_rev = revenues[i - 4]  # 同季度去年
        if prev_rev and prev_rev != 0:
            yoy_labels.append(labels[i])
            yoy_growth.append((curr_rev - prev_rev) / abs(prev_rev) * 100)

    if yoy_growth:
        colors_yoy = ["#4caf50" if v >= 0 else "#f44336" for v in yoy_growth]
        fig.add_trace(go.Bar(x=yoy_labels, y=yoy_growth, name="营收增速 YoY%",
                             marker_color=colors_yoy), row=2, col=1)
        fig.add_hline(y=0, line_color="#555", line_width=0.5, row=2, col=1)
        fig.update_yaxes(title_text="%", row=2, col=1)

    # 4. 总资产 & 股东权益
    assets = [fin[p].get("total_assets") or 0 for p in sorted_periods]
    equities = [fin[p].get("shareholders_equity") or 0 for p in sorted_periods]
    liabs = [fin[p].get("total_liabilities") or 0 for p in sorted_periods]
    a_b = [abs(a) / 1e9 for a in assets]
    e_b = [abs(e) / 1e9 for e in equities]
    l_b = [abs(l) / 1e9 for l in liabs]

    fig.add_trace(go.Scatter(x=labels, y=a_b, mode="lines+markers",
                             name="总资产 ($B)", line=dict(color="#2196f3", width=2)), row=2, col=2)
    fig.add_trace(go.Scatter(x=labels, y=e_b, mode="lines+markers",
                             name="股东权益 ($B)", line=dict(color="#4caf50", width=2)), row=2, col=2)
    fig.add_trace(go.Scatter(x=labels, y=l_b, mode="lines+markers",
                             name="总负债 ($B)", line=dict(color="#f44336", width=1.5, dash="dot")), row=2, col=2)

    fig.update_layout(
        template="plotly_dark", height=600,
        paper_bgcolor="#1a2332", plot_bgcolor="#1a2332",
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.05),
        barmode="group"
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, config={'displaylogo': False, 'modeBarButtonsToRemove': ['zoom2d','pan2d','select2d','lasso2d','zoomIn2d','zoomOut2d','resetScale2d','hoverClosestCartesian','hoverCompareCartesian','toggleSpikelines'], 'displayModeBar': True})


def _fig_valuation(info: dict, technicals: dict) -> str:
    """财务指标总览 (来自 get_fina_ex)"""
    gm = info.get("grossMargins")
    nm = info.get("profitMargins")
    roe = info.get("returnOnEquity")
    de = info.get("debtToEquity")
    rev = info.get("latestRevenue")
    ni_q = info.get("latestNetIncome")
    ttm_rev = info.get("ttmRevenue")
    ttm_ni = info.get("ttmNetIncome")
    tp = info.get("targetMeanPrice")
    lt_info = info.get("lt_growth", {}) or {}
    lt_growth = lt_info.get("mean")
    current_price = info.get("currentPrice")

    cards = [
        ("毛利率", gm, _sfmt_pct(gm)),
        ("净利率", nm, _sfmt_pct(nm)),
        ("ROE (TTM)", roe, _sfmt_pct(roe)),
        ("负债/权益", de, _sfmt(de, ".2f") if de else "--"),
        ("单季营收", rev, f"${rev/1e9:.1f}B" if rev else "--"),
        ("单季净利", ni_q, f"${ni_q/1e9:.1f}B" if ni_q else "--"),
        ("TTM营收", ttm_rev, f"${ttm_rev/1e9:.1f}B" if ttm_rev else "--"),
        ("TTM净利", ttm_ni, f"${ttm_ni/1e9:.1f}B" if ttm_ni else "--"),
        ("分析师目标价", tp, _sfmt_dollar(tp)),
        ("长期增长预期", lt_growth, _sfmt_pct(lt_growth)),
    ]

    html_parts = []
    html_parts.append("<div style='display:flex; gap:12px; flex-wrap:wrap;'>")
    for label, val, display in cards:
        html_parts.append(
            f"<div style='background:#1a2332; border:1px solid #2a3a4a; border-radius:8px; "
            f"padding:12px 20px; text-align:center; min-width:100px;'>"
            f"<div style='color:#8899aa; font-size:0.75rem;'>{label}</div>"
            f"<div style='color:#e1e8ed; font-size:1.2rem; font-weight:700;'>{display}</div>"
            f"</div>"
        )
    html_parts.append("</div>")

    if tp and current_price:
        upside = (tp - current_price) / current_price * 100
        color = "#4caf50" if upside > 0 else "#f44336"
        direction = "上行空间" if upside > 0 else "下行风险"
        html_parts.append(
            f"<p style='color:#8899aa; font-size:0.85rem; margin-top:16px;'>"
            f"分析师目标价 <span style='color:{color}; font-weight:700;'>{direction} {abs(upside):.1f}%</span>"
            f" (当前 ${current_price:.2f} -> 目标 ${tp:.2f})"
            f"</p>"
        )

    return f"<div class='plot-container'>{''.join(html_parts)}</div>"


def _fig_institutional(info: dict, institutional: dict = None) -> str:
    """机构分析 - 前十大机构投资者 + 分析师目标价"""
    html_parts = []

    # 分析师目标价概览
    tp = info.get("targetMeanPrice")
    tp_high = info.get("targetHighPrice")
    tp_low = info.get("targetLowPrice")
    current_price = info.get("currentPrice")

    html_parts.append("<div style='display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px;'>")
    if tp and current_price:
        upside = (tp - current_price) / current_price * 100
        color = "#4caf50" if upside > 0 else "#f44336"
        html_parts.append(
            f"<div style='background:#1a2332; border:1px solid #2a3a4a; border-radius:8px; padding:12px 16px;'>"
            f"<div style='color:#8899aa; font-size:0.7rem;'>分析师目标价</div>"
            f"<div style='font-size:1.3rem; font-weight:700;'>${tp:.2f}</div>"
            f"<div style='font-size:0.8rem; color:{color};'>{'上行' if upside > 0 else '下行'} {abs(upside):.1f}%</div>"
            f"</div>"
        )
    lt_info = info.get("lt_growth", {}) or {}
    lt_val = lt_info.get("mean")
    if lt_val:
        html_parts.append(
            f"<div style='background:#1a2332; border:1px solid #2a3a4a; border-radius:8px; padding:12px 16px;'>"
            f"<div style='color:#8899aa; font-size:0.7rem;'>长期增长预期</div>"
            f"<div style='font-size:1.3rem; font-weight:700;'>{_sfmt_pct(lt_val)}</div>"
            f"</div>"
        )
    html_parts.append("</div>")

    # 前十大机构投资者
    investors = (institutional or {}).get("top10_investors", [])
    if investors:
        html_parts.append(
            "<table class='highlight-table'>"
            "<tr><th>#</th><th>机构名称</th><th>持股数</th><th>占比</th><th>变动</th><th>报告日期</th></tr>"
        )
        for inv in investors[:10]:
            rank = inv.get("rank", "")
            name = inv.get("name", "")
            shares = inv.get("shares")
            ratio = inv.get("outstanding_ratio")
            change = inv.get("change")
            info_date = str(inv.get("date", ""))
            # 格式化日期 20260331 -> 2026-03-31
            if len(info_date) == 8:
                info_date = f"{info_date[:4]}-{info_date[4:6]}-{info_date[6:8]}"

            shares_str = f"{shares/1e6:.1f}M" if shares else "--"
            ratio_str = f"{ratio*100:.2f}%" if ratio and ratio < 1 else f"{ratio:.2f}%" if ratio else "--"
            if change:
                chg_sign = "+" if change > 0 else ""
                chg_color = "#4caf50" if change > 0 else "#f44336"
                chg_str = f"<span style='color:{chg_color}'>{chg_sign}{change/1e6:.1f}M</span>"
            else:
                chg_str = "--"

            html_parts.append(
                f"<tr><td>{rank}</td><td style='max-width:200px;overflow:hidden;text-overflow:ellipsis;' title='{name}'>{name}</td>"
                f"<td>{shares_str}</td><td>{ratio_str}</td><td>{chg_str}</td><td style='font-size:0.75rem;color:#8899aa;'>{info_date}</td></tr>"
            )
        html_parts.append("</table>")
    else:
        html_parts.append("<p style='color:#8899aa;'>暂无机构持仓数据</p>")

    return f"<div class='plot-container'>{''.join(html_parts)}</div>"


# ============ 存储行业专属图表 ============

def _memory_specific_tabs(price_df, fundamentals, inv_analysis, price_cycle,
                          capex_analysis, peers,
                          fin_events=None, ir_events=None,
                          insider_trades=None, shareholder_reports=None,
                          recommendation=None,
                          hbm_demand=None, end_market=None,
                          tech_position=None, hbm_exposure=None,
                          ticker="MU") -> str:
    """存储行业专属分析 - 垂直堆叠展示"""
    figs = _build_memory_figures(price_df, fundamentals, inv_analysis, price_cycle,
                                 capex_analysis, peers,
                                 fin_events, ir_events, insider_trades, shareholder_reports,
                                 recommendation, hbm_demand, end_market, tech_position,
                                 hbm_exposure, ticker)

    # 子模块 ID 映射
    anchor_map = {
        "📦 库存 & 价格周期": "sec-inventory",
        "📊 定价能力分析": "sec-margin",
        "🚀 HBM GPU 需求量化": "sec-hbm",
        "🎯 下游需求终端拆分": "sec-downstream",
        "🔬 技术节点路线图": "sec-tech-node",
        "🎯 行业对标": "sec-peer",
        "📋 财务事件": "sec-events",
        "💼 内部人交易": "sec-events",
        "📄 股东报告": "sec-events",
        "⭐ 分析师评级": "sec-events",
    }
    sections = []
    for title, html in figs:
        aid = anchor_map.get(title, "")
        anchor = f' id="{aid}"' if aid else ""
        sections.append(f"""
        <div{anchor} style="margin-bottom:16px;">
            <div class="section-title" style="margin-top:24px;">{title}</div>
            {html}
        </div>""")

    return f"""
    <div class="section-title" style="margin-top:24px;">💾 存储行业专属分析</div>
    {"".join(sections)}"""


def _build_memory_figures(price_df, fundamentals, inv_analysis, price_cycle,
                          capex_analysis, peers,
                          fin_events=None, ir_events=None,
                          insider_trades=None, shareholder_reports=None,
                          recommendation=None,
                          hbm_demand=None, end_market=None,
                          tech_position=None, hbm_exposure=None,
                          ticker="MU"):
    """构建存储行业专属图表"""
    figs = []

    figs.append(("📦 库存 & 价格周期", _fig_inventory_price_cycle(fundamentals, inv_analysis, price_cycle)))
    figs.append(("📊 定价能力分析", _fig_gross_margin_pricing(fundamentals)))
    figs.append(("🚀 HBM GPU 需求量化", _fig_hbm_gpu_demand(hbm_demand, hbm_exposure)))
    figs.append(("🎯 下游需求终端拆分", _fig_end_market_demand(end_market, ticker)))
    figs.append(("🔬 技术节点路线图", _fig_technology_nodes(tech_position, ticker)))
    figs.append(("🎯 行业对标", _fig_peer_radar(peers, fundamentals)))
    figs.append(("📋 财务事件", _fig_financial_events(fin_events)))
    figs.append(("💼 内部人交易", _fig_insider_trades(insider_trades)))
    figs.append(("📄 股东报告", _fig_shareholder_reports(shareholder_reports)))
    figs.append(("⭐ 分析师评级", _fig_recommendation(recommendation)))

    return figs

    return figs


def _fig_inventory_price_cycle(fundamentals: dict, inv_analysis: dict, price_cycle: dict) -> str:
    """库存周期 & 价格周期 - 基于 get_fina_ex 真实数据"""
    fin = fundamentals.get("financials", {})

    html_parts = []

    # 价格周期判定卡片
    html_parts.append("<div style='display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px;'>")
    html_parts.append(
        f"<div style='flex:1; min-width:200px; background:#1a2332; border:1px solid #2a3a4a; border-radius:8px; padding:14px;'>"
        f"<div style='color:#90caf9; font-size:0.85rem; font-weight:700; margin-bottom:6px;'>NAND/DRAM 价格周期</div>"
        f"<div style='font-size:1.1rem; font-weight:700; margin-bottom:4px;'>{price_cycle.get('cycle_phase', 'N/A')}</div>"
        f"<div style='color:#8899aa; font-size:0.8rem;'>DRAM QoQ: {price_cycle.get('avg_dram_qoq', 0):+.1f}% | NAND QoQ: {price_cycle.get('avg_nand_qoq', 0):+.1f}%</div>"
        f"</div>"
    )

    # 库存状态卡片 (从财务数据计算)
    if fin:
        periods = sorted(fin.keys())
        latest = fin[periods[-1]]
        inv_val = latest.get("inventory") or 0
        cogs_val = latest.get("cogs") or 0
        if cogs_val and inv_val:
            inv_days = abs(inv_val) / abs(cogs_val) * 365
            html_parts.append(
                f"<div style='background:#1a2332; border:1px solid #2a3a4a; border-radius:8px; padding:14px;'>"
                f"<div style='color:#8899aa; font-size:0.75rem;'>最新季度库存周转</div>"
                f"<div style='font-size:1.3rem; font-weight:700;'>{inv_days:.0f} 天</div>"
                f"<div style='color:#8899aa; font-size:0.75rem;'>库存 ${abs(inv_val)/1e9:.1f}B / COGS ${abs(cogs_val)/1e9:.1f}B</div>"
                f"</div>"
            )
    html_parts.append("</div>")

    # 库存周转趋势图
    if fin:
        periods = sorted(fin.keys())
        labels = [p.replace("FY", "FY ") for p in periods]
        inv_days_list = []
        inv_vals_b = []
        for p in periods:
            q = fin[p]
            inv = q.get("inventory") or 0
            cogs = q.get("cogs") or 0
            days = abs(inv) / abs(cogs) * 365 if cogs else 0
            inv_days_list.append(days)
            inv_vals_b.append(abs(inv) / 1e9)

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            vertical_spacing=0.1, row_heights=[0.5, 0.5],
                            subplot_titles=("库存周转天数", "库存金额 & CapEx ($B)"))

        fig.add_trace(go.Scatter(x=labels, y=inv_days_list, mode="lines+markers",
                                 name="库存周转天数", line=dict(color="#ff9800", width=2),
                                 fill="tozeroy", fillcolor="rgba(255,152,0,0.1)"), row=1, col=1)
        # 添加均值线
        avg_days = sum(inv_days_list) / len(inv_days_list)
        fig.add_hline(y=avg_days, line_dash="dash", line_color="#888", opacity=0.5,
                      annotation_text=f"均值 {avg_days:.0f}天", row=1, col=1)
        fig.add_hline(y=180, line_dash="dot", line_color="#4caf50", opacity=0.3, row=1, col=1)

        capex_b = [abs(fin[p].get("capex") or 0) / 1e9 for p in periods]
        fig.add_trace(go.Bar(x=labels, y=inv_vals_b, name="库存 ($B)", marker_color="#ff9800", opacity=0.7), row=2, col=1)
        fig.add_trace(go.Scatter(x=labels, y=capex_b, mode="lines+markers",
                                 name="CapEx ($B)", line=dict(color="#2196f3", width=2)), row=2, col=1)

        fig.update_yaxes(tickformat=".0f", title_text="天", row=1, col=1)
        fig.update_yaxes(tickformat=".1f", title_text="$B", row=2, col=1)
        fig.update_layout(template="plotly_dark", height=450,
                          paper_bgcolor="#1a2332", plot_bgcolor="#1a2332",
                          margin=dict(l=20, r=20, t=30, b=20),
                          hovermode="x unified")
        html_parts.append(fig.to_html(full_html=False, include_plotlyjs=False, config={'displaylogo': False, 'modeBarButtonsToRemove': ['zoom2d','pan2d','select2d','lasso2d','zoomIn2d','zoomOut2d','resetScale2d','hoverClosestCartesian','hoverCompareCartesian','toggleSpikelines'], 'displayModeBar': True}))

    return f"<div class='plot-container'>{''.join(html_parts)}</div>"


def _fig_gross_margin_pricing(fundamentals: dict) -> str:
    """毛利率 & 净利率趋势 (定价能力代理，基于 get_fina_ex)"""
    fin = fundamentals.get("financials", {})

    if not fin:
        return "<div class='plot-container'><p style='color:#8899aa;'>暂无财务数据</p></div>"

    sorted_periods = sorted(fin.keys())
    labels = [p.replace("FY", "FY ") for p in sorted_periods]

    revenues = [fin[p].get("revenue") or 0 for p in sorted_periods]
    gross_profits = [fin[p].get("gross_profit") or 0 for p in sorted_periods]
    net_incomes = [fin[p].get("net_income") or 0 for p in sorted_periods]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.1, row_heights=[0.5, 0.5],
                        subplot_titles=("毛利率 & 净利率趋势 (定价能力代理)", "单季营收 & 净利 ($B)"))

    gm = [g / r * 100 if r > 0 else 0 for g, r in zip(gross_profits, revenues)]
    nm = [n / r * 100 if r > 0 else 0 for n, r in zip(net_incomes, revenues)]

    fig.add_trace(go.Scatter(x=labels, y=gm, mode="lines+markers",
                             name="毛利率 %", line=dict(color="#4caf50", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=labels, y=nm, mode="lines+markers",
                             name="净利率 %", line=dict(color="#ff9800", width=2)), row=1, col=1)
    fig.add_hline(y=0, line_color="#555", line_width=0.5, row=1, col=1)

    rev_b = [abs(r) / 1e9 for r in revenues]
    ni_b = [abs(n) / 1e9 for n in net_incomes]
    fig.add_trace(go.Bar(x=labels, y=rev_b, name="营收 ($B)", marker_color="#2196f3"), row=2, col=1)
    fig.add_trace(go.Scatter(x=labels, y=ni_b, mode="lines+markers",
                             name="净利 ($B)", line=dict(color="#ff9800", width=2)), row=2, col=1)

    # 添加均值参考线
    if gm:
        avg_gm = sum(gm) / len(gm)
        fig.add_hline(y=avg_gm, line_dash="dash", line_color="#4caf50", opacity=0.3,
                      annotation_text=f"均值 {avg_gm:.1f}%", row=1, col=1)

    fig.update_layout(
        template="plotly_dark", height=450,
        paper_bgcolor="#1a2332", plot_bgcolor="#1a2332",
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified"
    )
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="%", row=2, col=1)

    return fig.to_html(full_html=False, include_plotlyjs=False)


def _fig_peer_radar(peers: dict, fundamentals: dict) -> str:
    """行业对标雷达图 (基于 pv_metric + mktfin_metric)"""
    if not peers:
        return "<div class='plot-container'><p style='color:#8899aa;'>暂无同行数据</p></div>"

    info = fundamentals.get("info", {})
    company_name = info.get("shortName") or info.get("longName") or info.get("symbol", "MU")

    # PE 反向（越低越好），其他正向或自有刻度
    dimensions = ["PE (TTM)↓", "PB", "PS", "PEG", "Beta", "市值"]
    # 归一化参考值
    dim_scale = [200, 30, 30, 1, 3, 2000e9]  # PE最高200, PB最高30, PS最高30, PEG最高1, Beta最高3, 市值最高2T

    fig = go.Figure()

    # 当前公司
    pe = info.get("trailingPE") or 1
    pb = info.get("priceToBook") or 1
    ps = info.get("priceToSales") or 1
    peg = info.get("pegRatio") or 1
    beta = info.get("beta") or 1
    mcap = info.get("marketCap") or 1

    # PE 反向归一化（越低越好→归一化值越高）
    pe_norm = max(0, min(100, (1 - pe / 200) * 100))
    current_norm = [
        pe_norm,
        min(pb / 30 * 100, 100),
        min(ps / 30 * 100, 100),
        min(peg / 1 * 100, 100) if peg else 50,
        min(beta / 3 * 100, 100),
        min(mcap / 2e12 * 100, 100) if mcap else 50,
    ]

    fig.add_trace(go.Scatterpolar(
        r=current_norm + [current_norm[0]],
        theta=dimensions + [dimensions[0]],
        fill="toself",
        name=company_name,
        line=dict(color="#2196f3", width=2.5),
        fillcolor="rgba(33, 150, 243, 0.25)"
    ))

    # 对标公司
    colors = ["#ff9800", "#4caf50", "#e91e63", "#9c27b0"]
    colors_rgba = ["rgba(255,152,0,0.2)", "rgba(76,175,80,0.2)",
                   "rgba(233,30,99,0.2)", "rgba(156,39,176,0.2)"]
    color_idx = 0
    for ticker, data in peers.items():
        if "error" in data:
            continue
        if ticker == info.get("symbol", "").upper():
            continue  # Skip self

        name = data.get("name", ticker)
        p_pe = data.get("pe_ttm") or 1
        p_pb = data.get("pb") or 1
        p_ps = data.get("ps") or 1
        p_peg = data.get("peg") or 1
        p_beta = data.get("beta") or 1
        p_mcap = data.get("market_cap") or 1

        peer_norm = [
            max(0, min(100, (1 - p_pe / 200) * 100)),
            min(p_pb / 30 * 100, 100),
            min(p_ps / 30 * 100, 100),
            min(p_peg / 1 * 100, 100) if p_peg else 50,
            min(p_beta / 3 * 100, 100),
            min(p_mcap / 2e12 * 100, 100) if p_mcap else 50,
        ]

        visible = True  # Show all peers
        fig.add_trace(go.Scatterpolar(
            r=peer_norm + [peer_norm[0]],
            theta=dimensions + [dimensions[0]],
            fill="toself",
            name=name,
            line=dict(color=colors[color_idx % len(colors)], width=1.5),
            fillcolor=colors_rgba[color_idx % len(colors_rgba)],
            visible=True
        ))
        color_idx += 1

    if color_idx == 0:
        return "<div class='plot-container'><p style='color:#8899aa;'>暂无有效对标数据</p></div>"

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False),
            bgcolor="#1a2332"
        ),
        template="plotly_dark", height=500,
        paper_bgcolor="#1a2332", plot_bgcolor="#1a2332",
        margin=dict(l=40, r=40, t=30, b=30),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.05)
    )

    return fig.to_html(full_html=False, include_plotlyjs=False, config={'displaylogo': False, 'modeBarButtonsToRemove': ['zoom2d','pan2d','select2d','lasso2d','zoomIn2d','zoomOut2d','resetScale2d','hoverClosestCartesian','hoverCompareCartesian','toggleSpikelines'], 'displayModeBar': True})


def _fig_capex_ai(capex_analysis: dict, price_df: pd.DataFrame, fundamentals: dict = None) -> str:
    """Capex & AI 联动 - 基于 get_fina_ex 真实数据"""
    fin = (fundamentals or {}).get("financials", {})
    html_parts = []

    if fin:
        periods = sorted(fin.keys())
        labels = [p.replace("FY", "FY ") for p in periods]
        revenues_b = [abs(fin[p].get("revenue") or 0) / 1e9 for p in periods]
        capex_b = [abs(fin[p].get("capex") or 0) / 1e9 for p in periods]

        # 汇总卡片
        latest_capex = capex_b[-1] if capex_b else 0
        latest_rev = revenues_b[-1] if revenues_b else 0
        capex_ratio = latest_capex / latest_rev * 100 if latest_rev > 0 else 0
        total_capex_4q = sum(capex_b[-4:]) if len(capex_b) >= 4 else sum(capex_b)

        html_parts.append("<div style='display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px;'>")
        html_parts.append(
            f"<div style='background:#1a2332; border:1px solid #2a3a4a; border-radius:8px; padding:12px 16px;'>"
            f"<div style='color:#8899aa; font-size:0.7rem;'>最新季度 CapEx</div>"
            f"<div style='font-size:1.3rem; font-weight:700;'>${latest_capex:.1f}B</div>"
            f"</div>"
        )
        html_parts.append(
            f"<div style='background:#1a2332; border:1px solid #2a3a4a; border-radius:8px; padding:12px 16px;'>"
            f"<div style='color:#8899aa; font-size:0.7rem;'>CapEx / 营收</div>"
            f"<div style='font-size:1.3rem; font-weight:700;'>{capex_ratio:.1f}%</div>"
            f"</div>"
        )
        html_parts.append(
            f"<div style='background:#1a2332; border:1px solid #2a3a4a; border-radius:8px; padding:12px 16px;'>"
            f"<div style='color:#8899aa; font-size:0.7rem;'>TTM CapEx (4Q)</div>"
            f"<div style='font-size:1.3rem; font-weight:700;'>${total_capex_4q:.1f}B</div>"
            f"</div>"
        )
        html_parts.append("</div>")

        # CapEx + 营收趋势图
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            vertical_spacing=0.1, row_heights=[0.55, 0.45],
                            subplot_titles=("CapEx vs 营收 季度趋势", "CapEx / 营收 比率 (%)"))

        fig.add_trace(go.Bar(x=labels, y=capex_b, name="CapEx ($B)", marker_color="#ff9800"), row=1, col=1)
        fig.add_trace(go.Scatter(x=labels, y=revenues_b, mode="lines+markers",
                                 name="营收 ($B)", line=dict(color="#2196f3", width=2),
                                 yaxis="y2"), row=1, col=1)

        capex_pct = [c / r * 100 if r > 0 else 0 for c, r in zip(capex_b, revenues_b)]
        fig.add_trace(go.Bar(x=labels, y=capex_pct, name="CapEx/营收 %",
                             marker_color=["#4caf50" if v < 30 else "#ff9800" if v < 50 else "#f44336" for v in capex_pct]),
                      row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#4caf50", opacity=0.3,
                      annotation_text="健康线 30%", row=2, col=1)

        fig.update_layout(
            template="plotly_dark", height=450,
            paper_bgcolor="#1a2332", plot_bgcolor="#1a2332",
            margin=dict(l=20, r=20, t=30, b=20),
            yaxis2=dict(overlaying="y", side="right", title="营收 ($B)"),
            hovermode="x unified",
            showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.05)
        )
        html_parts.append(fig.to_html(full_html=False, include_plotlyjs=False, config={'displaylogo': False, 'modeBarButtonsToRemove': ['zoom2d','pan2d','select2d','lasso2d','zoomIn2d','zoomOut2d','resetScale2d','hoverClosestCartesian','hoverCompareCartesian','toggleSpikelines'], 'displayModeBar': True}))

    html_parts.append(
        "<p style='color:#8899aa; font-size:0.8rem; margin-top:12px;'>"
        "AI 数据中心建设推动存储 CapEx 大幅扩张。CapEx/营收 >30% 代表激进扩产，20-30% 温和扩张，<20% 维持性投入。"
        "</p>"
    )

    return f"<div class='plot-container'>{''.join(html_parts)}</div>"


def _assessment_footer(memory_assessment: dict, inv_analysis: dict, price_cycle: dict,
                       technicals: dict, info: dict, fundamentals: dict,
                       recommendation: dict = None,
                       insider_trades: list = None,
                       shareholder_reports: list = None,
                       peers: dict = None,
                       capex_analysis: dict = None,
                       hbm_demand: dict = None,
                       end_market: dict = None,
                       tech_position: dict = None,
                       ticker: str = "MU") -> str:
    """综合评估 - 10维度(公司差异化): 短期技术(10%)+存储周期(25%)+分析师(12%)+HBM(8%)+下游(8%)+内部人(8%)+股东(8%)+技术(4%)+对标(5%)+财务(±25)"""
    score = memory_assessment.get("composite_score", 50)
    rating = memory_assessment.get("rating", "N/A")

    # === 短期技术面分析 ===
    rsi = 50.0
    if "rsi_14" in technicals:
        rsi = float(technicals["rsi_14"].iloc[-1]) if hasattr(technicals["rsi_14"], 'iloc') else 50.0

    macd_hist = 0
    if "macd_hist" in technicals:
        hist_series = technicals["macd_hist"]
        macd_hist = float(hist_series.iloc[-1]) if hasattr(hist_series, 'iloc') else 0

    vol_ratio = technicals.get("volume_ratio", 1.0)

    # 短期信号
    st_signals = []
    if rsi > 70:
        st_signals.append(("超买", "bearish", f"RSI={rsi:.0f}"))
    elif rsi < 30:
        st_signals.append(("超卖", "bullish", f"RSI={rsi:.0f}"))
    else:
        st_signals.append(("中性", "neutral", f"RSI={rsi:.0f}"))

    if macd_hist > 0:
        st_signals.append(("MACD金叉", "bullish", f"+{macd_hist:.3f}"))
    else:
        st_signals.append(("MACD死叉", "bearish", f"{macd_hist:.3f}"))

    if vol_ratio and vol_ratio > 1.5:
        st_signals.append(("放量", "bearish" if rsi < 50 else "bullish", f"{vol_ratio:.1f}x"))

    # 短期判定
    bull_count = sum(1 for _, s, _ in st_signals if s == "bullish")
    bear_count = sum(1 for _, s, _ in st_signals if s == "bearish")
    if bull_count > bear_count:
        short_term = "偏多"
        st_color = "#4caf50"
    elif bear_count > bull_count:
        short_term = "偏空"
        st_color = "#f44336"
    else:
        short_term = "震荡"
        st_color = "#ff9800"

    # 1-5日趋势
    closes = technicals.get("ma_5")
    if closes is not None and hasattr(closes, 'iloc') and len(closes) >= 5:
        ma5_now = float(closes.iloc[-1]) if hasattr(closes, 'iloc') else 0
        ma5_3d = float(closes.iloc[-4]) if len(closes) >= 4 else ma5_now
        trend_short = "上升" if ma5_now > ma5_3d else "下降"
    else:
        trend_short = "不明"

    # === 长期基本面分析 ===
    fin = fundamentals.get("financials", {})
    periods = sorted(fin.keys())
    lt_signals = []
    if len(periods) >= 4:
        recent_rev = fin[periods[-1]].get("revenue") or 0
        prev_rev = fin[periods[-5]].get("revenue") if len(periods) >= 5 else fin[periods[-4]].get("revenue") or 0
        if prev_rev and prev_rev > 0:
            yoy_growth = (recent_rev - prev_rev) / abs(prev_rev) * 100
            lt_signals.append(f"营收 YoY: {yoy_growth:+.0f}%")

        recent_ni = fin[periods[-1]].get("net_income") or 0
        if recent_rev and recent_rev > 0:
            nm = recent_ni / recent_rev * 100
            lt_signals.append(f"净利率 (单季): {nm:.1f}%")

    # 分析师信号
    rec_signal = ""
    if recommendation:
        rec_mean = recommendation.get("mean", 0)
        if rec_mean and rec_mean <= 2.0:
            rec_signal = "分析师共识: 买入"
        elif rec_mean and rec_mean <= 3.0:
            rec_signal = "分析师共识: 持有"
        else:
            rec_signal = "分析师共识: 卖出"

    # 价格周期
    pc_phase = price_cycle.get("cycle_phase", "N/A")

    # 长期判定
    if score >= 60:
        long_term = "看多"
        lt_color = "#4caf50"
    elif score >= 45:
        long_term = "中性偏多"
        lt_color = "#ff9800"
    elif score >= 30:
        long_term = "中性偏空"
        lt_color = "#ff9800"
    else:
        long_term = "谨慎"
        lt_color = "#f44336"

    def _sig_color(sig):
        return {"bullish": "#4caf50", "bearish": "#f44336"}.get(sig, "#ff9800")

    st_signals_html = "".join([
        f"<div style='background:#1a2a3a; border-radius:6px; padding:6px 10px; font-size:0.8rem;'>"
        f"{name}: <span style='color:{_sig_color(sig)}'>{detail}</span>"
        f"</div>"
        for name, sig, detail in st_signals
    ])

    lt_signals_html = "".join([
        f"<div style='padding:3px 0; font-size:0.82rem;'>{s}</div>" for s in lt_signals
    ])

    # 计算评估逻辑中的当前值
    periods_fin = sorted(fin.keys())
    last_rev = 0; last_ni = 0; last_gp = 0
    if periods_fin:
        q = fin[periods_fin[-1]]
        last_rev = q.get("revenue") or 0
        last_ni = q.get("net_income") or 0
        last_gp = q.get("gross_profit") or 0
    nm_latest = last_ni / last_rev * 100 if last_rev > 0 else 0
    gm_latest = last_gp / last_rev * 100 if last_rev > 0 else 0

    # TTM 数据
    ttm_rev = 0; ttm_ni = 0
    for p in periods_fin[-4:]:
        q = fin[p]
        ttm_rev += abs(q.get("revenue") or 0)
        ttm_ni += abs(q.get("net_income") or 0)
    ttm_nm = ttm_ni / ttm_rev * 100 if ttm_rev > 0 else 0

    rec_mean_val = recommendation.get("mean", 0) if recommendation else 0
    rec_total = int(recommendation.get("total", 0)) if recommendation else 0
    pe_val = info.get("trailingPE") or 0

    # 时效性过滤: 取最近7天数据，无则取最新3条
    from datetime import datetime as dt, timedelta
    today_str = dt.now().strftime("%Y%m%d")
    seven_days_ago = (dt.now() - timedelta(days=7)).strftime("%Y%m%d")

    def _filter_recent(data_list, date_key="last_date"):
        """过滤最近7天数据，无则取最新3条"""
        if not data_list:
            return []
        recent = [d for d in data_list if str(d.get(date_key, "") or "") >= seven_days_ago]
        if recent:
            return recent
        # 无最近7天数据，取最新3条
        sorted_data = sorted(data_list, key=lambda d: str(d.get(date_key, "") or ""), reverse=True)
        return sorted_data[:3]

    insider_filtered = _filter_recent(insider_trades or [], "last_date")
    shareholder_filtered = _filter_recent(shareholder_reports or [], "date")

    # 内部人信号
    insider_total_sell = sum(t.get("total_sell_value", 0) or 0 for t in insider_filtered)
    insider_total_buy = sum(t.get("total_buy_value", 0) or 0 for t in insider_filtered)
    if insider_total_sell > insider_total_buy * 3:
        insider_signal = f"净卖出 ${insider_total_sell/1e6:.0f}M ({len(insider_filtered)}人)"
        insider_color = "#f44336"
    elif insider_total_buy > insider_total_sell * 1.5:
        insider_signal = f"净买入 ${insider_total_buy/1e6:.0f}M ({len(insider_filtered)}人)"
        insider_color = "#4caf50"
    else:
        insider_signal = f"买卖均衡 ({len(insider_filtered)}人)" if insider_filtered else "买卖均衡"
        insider_color = "#ff9800"

    # 股东报告信号 - 逐条统计方向 (使用时效性过滤后的数据)
    shr_total = len(shareholder_filtered)
    shr_inc = 0; shr_dec = 0; shr_total_change = 0
    for r in shareholder_filtered:
        c = r.get("change")
        if c and c > 0:
            shr_inc += 1
            shr_total_change += c
        elif c and c < 0:
            shr_dec += 1
            shr_total_change += c
    if shr_total == 0:
        shareholder_signal = "暂无"
    elif shr_inc > shr_dec * 2:
        shareholder_signal = f"多数增持({shr_inc}增/{shr_dec}减)"
    elif shr_dec > shr_inc * 2:
        shareholder_signal = f"多数减持({shr_dec}减/{shr_inc}增)"
    elif shr_inc > shr_dec:
        shareholder_signal = f"增持略多({shr_inc}增/{shr_dec}减)"
    elif shr_dec > shr_inc:
        shareholder_signal = f"减持略多({shr_dec}减/{shr_inc}增)"
    else:
        shareholder_signal = f"增减均衡({shr_inc}增/{shr_dec}减)"

    # === 行业对标评分 ===
    peer_pe_avg = None
    if peers:
        pe_vals = [p.get("pe_ttm") for p in peers.values() if p.get("pe_ttm") and p.get("pe_ttm") > 0]
        if pe_vals:
            peer_pe_avg = sum(pe_vals) / len(pe_vals)
    # 相比同行PE: 偏低=有吸引力, 偏高=高估
    if peer_pe_avg and pe_val and pe_val > 0:
        pe_ratio = pe_val / peer_pe_avg
        if pe_ratio < 0.7:
            peer_score = 65; peer_signal = f"PE显著低于同行(PE={pe_val:.1f} vs 均值{peer_pe_avg:.1f})"
        elif pe_ratio < 0.9:
            peer_score = 55; peer_signal = f"PE略低于同行(PE={pe_val:.1f} vs 均值{peer_pe_avg:.1f})"
        elif pe_ratio < 1.1:
            peer_score = 50; peer_signal = f"PE与同行持平(PE={pe_val:.1f} vs 均值{peer_pe_avg:.1f})"
        elif pe_ratio < 1.5:
            peer_score = 40; peer_signal = f"PE略高于同行(PE={pe_val:.1f} vs 均值{peer_pe_avg:.1f})"
        else:
            peer_score = 30; peer_signal = f"PE显著高于同行(PE={pe_val:.1f} vs 均值{peer_pe_avg:.1f})"
    else:
        peer_score = 50; peer_signal = "无可比同行数据"

    # === 股东变动评分 ===
    if shr_total == 0:
        shareholder_score = 50
    elif shr_inc > shr_dec * 2:
        shareholder_score = 65
    elif shr_dec > shr_inc * 2:
        shareholder_score = 35
    elif shr_inc > shr_dec:
        shareholder_score = 55
    elif shr_dec > shr_inc:
        shareholder_score = 40
    else:
        shareholder_score = 50

    # === 财务质量修正 ===
    # 从 info 字典获取更多财务指标
    gross_margin = info.get("grossMargins") or 0
    roe_val = info.get("returnOnEquity") or 0
    debt_eq = info.get("debtToEquity") or 0
    pb_val = info.get("priceToBook") or 0
    beta_val = info.get("beta") or 0

    finance_mod = 0
    # 净利率 (单季)
    if nm_latest > 30: finance_mod += 8
    elif nm_latest > 15: finance_mod += 5
    elif nm_latest > 5: finance_mod += 0
    elif nm_latest > 0: finance_mod -= 5
    else: finance_mod -= 12
    # 毛利率
    if gross_margin > 50: finance_mod += 6
    elif gross_margin > 35: finance_mod += 3
    elif gross_margin > 20: finance_mod += 0
    else: finance_mod -= 6
    # ROE
    if roe_val > 30: finance_mod += 6
    elif roe_val > 15: finance_mod += 3
    elif roe_val > 5: finance_mod += 0
    else: finance_mod -= 5
    # 负债率 (D/E, 越低越好)
    if debt_eq and debt_eq > 0:
        if debt_eq < 0.3: finance_mod += 5
        elif debt_eq < 1.0: finance_mod += 2
        elif debt_eq > 3: finance_mod -= 6
    # PB (越低越有安全垫)
    if pb_val and pb_val > 0:
        if pb_val < 1.5: finance_mod += 3
        elif pb_val > 10: finance_mod -= 3
    # Beta (风险指标, 适中最好)
    if beta_val and beta_val > 0:
        if beta_val < 0.8: finance_mod += 2
        elif beta_val > 2.0: finance_mod -= 3

    # === 研究信号公式（所有维度、公司差异化） ===
    st_score = 60 if short_term == "偏多" else 40 if short_term == "偏空" else 50
    lt_score = score  # 存储周期评分 (0-100)

    # 🔧 读取公司业务结构用于差异化
    try:
        import json as _json, os as _os
        _cfg = _json.load(open(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                            "config", "industry_data.json"), 'r', encoding='utf-8'))
        comp_prof = _cfg.get("company_profiles", {}).get(ticker, {})
    except Exception:
        comp_prof = {}
    comp_mix = comp_prof.get("revenue_mix", {})
    comp_hbm = comp_prof.get("hbm_tier", "")
    comp_dram_node = comp_prof.get("dram_node", "")
    comp_nand_node = comp_prof.get("nand_node", "")

    analyst_score = 60 if rec_mean_val and rec_mean_val <= 1.5 else (55 if rec_mean_val and rec_mean_val <= 2.0 else (45 if rec_mean_val and rec_mean_val <= 3.0 else 35))
    insider_score = 60 if insider_signal.startswith("净买入") else (45 if insider_signal == "买卖均衡" else 35)

    # 🔧 HBM需求评分 — 公司差异化: HBM供应商全权重, 非HBM降权
    hbm_detail = memory_assessment.get("detail", {}).get("HBM供需", "")
    hbm_score_base = 65 if "供给紧张" in hbm_detail else (55 if "紧平衡" in hbm_detail else 40)
    if comp_hbm == "主要供应商":
        hbm_factor = 1.0    # MU: 充分受益
        hbm_tag = "直接受益"
    elif comp_hbm == "不涉及":
        hbm_factor = 0.3    # WDC/STX: 间接受益
        hbm_tag = "间接受益"
    else:
        hbm_factor = 0.6
        hbm_tag = "部分受益"
    hbm_score = int(hbm_score_base * hbm_factor)

    # 🔧 下游需求评分 — 公司差异化: 按营收结构加权
    demand_detail_raw = memory_assessment.get("detail", {}).get("下游需求", "")
    if end_market and end_market.get("available") and comp_mix:
        dram_g = end_market.get("dram", {}).get("weighted_growth_pct", 0)
        nand_g = end_market.get("nand", {}).get("weighted_growth_pct", 0)
        hbm_g = end_market.get("hbm", {}).get("weighted_growth_pct", 0)
        hdd_g = 5  # HDD 行业增速假设 ~5%
        # 公司加权增速 = Σ(业务占比 × 对应行业增速)
        w_dram = comp_mix.get("dram", 0) * dram_g
        w_nand = comp_mix.get("nand", 0) * nand_g
        w_hbm  = comp_mix.get("hbm", 0) * hbm_g
        w_hdd  = comp_mix.get("hdd", 0) * hdd_g
        company_weighted_growth = w_dram + w_nand + w_hbm + w_hdd
        demand_score = 65 if company_weighted_growth > 15 else (55 if company_weighted_growth > 8 else (45 if company_weighted_growth > 0 else 35))
        demand_detail = f"公司加权 {company_weighted_growth:+.1f}% (DRAM{w_dram:+.0f} NAND{w_nand:+.0f} HBM{w_hbm:+.0f} HDD{w_hdd:+.0f}) | 得分{demand_score}"
    else:
        demand_score = 50
        demand_detail = demand_detail_raw

    # 🔧 技术节点评分 — 公司差异化: 按公司实际节点判定
    if comp_dram_node and comp_nand_node:
        # DRAM: 1c/1d nm = 领先, 1a/1b = 主流, 不涉及 = 0
        dram_score = 3 if any(x in comp_dram_node for x in ["1c", "1d"]) else (1 if any(x in comp_dram_node for x in ["1a", "1b"]) else 0)
        # NAND: 400L+/500L+ = 领先, 276-321L = 主流, 不涉及 = 0
        nand_score = 3 if any(x in comp_nand_node for x in ["400", "500", "1000"]) else (1 if any(x in comp_nand_node for x in ["276", "300", "321"]) else 0)
        tech_score = 50 + (dram_score + nand_score) * 5  # 50 + 0~30
        tech_detail = f"DRAM: {comp_dram_node} | NAND: {comp_nand_node} | 得分{tech_score}"
    else:
        tech_score = 50
        tech_detail = memory_assessment.get("detail", {}).get("技术节点", "")

    final_score = (
        st_score * 0.10
        + lt_score * 0.25
        + analyst_score * 0.12
        + hbm_score * 0.08       # 🔧 公司差异化权重
        + demand_score * 0.08    # 🔧 公司加权增速
        + insider_score * 0.08
        + shareholder_score * 0.08
        + tech_score * 0.04      # 🔧 公司实际节点
        + peer_score * 0.05
        + finance_mod
    )
    final_score = max(10, min(95, int(round(final_score))))

    # 结论文本
    if final_score >= 65:
        summary = f"研究信号 {final_score} 分，研究指标整体较强：存储周期为{pc_phase}，单季净利率{nm_latest:.1f}%、ROE{roe_val:.1f}%，分析师共识为{rec_total}位。请结合数据新鲜度、来源和模型假设独立复核。"
        summary_color = "#4caf50"
    elif final_score >= 50:
        summary = f"研究信号 {final_score} 分，研究指标处于中间区间。短期技术面{short_term}，净利率{nm_latest:.1f}%，{rec_signal}；重点复核 DRAM/NAND 价格拐点、库存变化与缺失数据。"
        summary_color = "#ff9800"
    elif final_score >= 35:
        summary = f"研究信号 {final_score} 分，多项研究指标偏弱。短期{short_term}，{rec_signal}；应继续核验基本面、技术面和行业数据的时点一致性。"
        summary_color = "#ff9800"
    else:
        summary = f"研究信号 {final_score} 分，风险或数据质量信号较多。毛利率{gross_margin:.1f}%；请优先核验数据完整性、周期假设和后续公开披露。"
        summary_color = "#f44336"

    st_detail = " | ".join([f"{n}={d}" for n, s, d in st_signals])

    # 数据来源汇总
    data_sources = (
        "技术指标(RSI/MACD/量比) → indicators.py | "
        "行情/财务/估值 → panda_data(get_us_daily/get_fina_ex/mktfin_metric/pv_metric) | "
        "机构/内部人/分析师/股东 → panda_data 多接口 | "
        "DRAM/NAND价格 → WebSearch→TrendForce | "
        "HBM市场/GPU出货 → WebSearch→NVDA季报 | "
        "下游需求拆分 → WebSearch→TrendForce/IDC | "
        "CapEx指引/技术节点 → WebSearch→公司财报/行业报告 | "
        "HBM供给/GPU占比 → industry_data.json(WebSearch更新)"
    )

    return f"""
    <div class="assessment-footer">
        <h2>📋 综合评估</h2>

        <!-- 合并结论卡片: 评分 + 结论 + 周期打分 -->
        <div style="background:linear-gradient(135deg, rgba(76,175,80,0.08) 0%, rgba(255,255,255,0.03) 100%); border:1px solid {summary_color}; border-radius:14px; padding:24px; margin-bottom:20px;">
            <div style="display:flex; align-items:stretch; gap:24px; flex-wrap:wrap;">
                <!-- 左侧: 研究信号大数字 -->
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; min-width:110px; padding:12px 16px; background:rgba(0,0,0,0.3); border-radius:10px;">
                    <div style="color:#8899aa; font-size:0.8rem; font-weight:600; margin-bottom:4px;">研究信号</div>
                    <div style="font-size:3.2rem; font-weight:900; color:{summary_color}; line-height:1;">{final_score}</div>
                    <div style="font-size:0.75rem; color:#8899aa; margin-top:4px;">满分 100</div>
                </div>
                <!-- 中间: 结论文本 -->
                <div style="flex:1; min-width:250px; display:flex; flex-direction:column; justify-content:center;">
                    <div style="color:#fff; font-size:1.05rem; font-weight:700; margin-bottom:8px;">📊 研究摘要</div>
                    <div style="color:#d0d8e0; font-size:0.95rem; line-height:1.7;">{summary}</div>
                    <div style="margin-top:12px; display:flex; gap:16px; flex-wrap:wrap; font-size:0.8rem; color:#8899aa;">
                        <span>📉 短期: <b style="color:{st_color};">{short_term}</b></span>
                        <span>📈 长期: <b style="color:{lt_color};">{long_term}</b></span>
                        <span>💾 周期: <b style="color:#90caf9;">{pc_phase}</b> ({score}/100)</span>
                        <span>📊 评级: <b style="color:#4caf50;">{rec_signal}</b></span>
                        <span>{shareholder_signal}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 关键财务指标 -->
        <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:20px;">
            <div style="background:rgba(255,255,255,0.03); border-radius:8px; padding:12px; text-align:center;">
                <div style="color:#8899aa; font-size:0.75rem;">单季营收</div>
                <div style="color:#e1e8ed; font-size:1.1rem; font-weight:700;">${last_rev/1e9:.1f}B</div>
            </div>
            <div style="background:rgba(255,255,255,0.03); border-radius:8px; padding:12px; text-align:center;">
                <div style="color:#8899aa; font-size:0.75rem;">单季净利率</div>
                <div style="color:{'#4caf50' if nm_latest > 20 else '#ff9800'}; font-size:1.1rem; font-weight:700;">{nm_latest:.1f}%</div>
            </div>
            <div style="background:rgba(255,255,255,0.03); border-radius:8px; padding:12px; text-align:center;">
                <div style="color:#8899aa; font-size:0.75rem;">毛利率 / ROE</div>
                <div style="color:#e1e8ed; font-size:1.1rem; font-weight:700;">{gross_margin:.1f}% / {roe_val:.1f}%</div>
            </div>
            <div style="background:rgba(255,255,255,0.03); border-radius:8px; padding:12px; text-align:center;">
                <div style="color:#8899aa; font-size:0.75rem;">PE / PB / Beta</div>
                <div style="color:#e1e8ed; font-size:1.1rem; font-weight:700;">{pe_val:.1f} / {pb_val:.1f} / {beta_val:.1f}</div>
            </div>
        </div>

        <!-- 短期 + 长期 两栏 -->
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px;">
            <div style="background:rgba(255,255,255,0.04); border-radius:10px; padding:16px;">
                <div style="color:{st_color}; font-size:1.15rem; font-weight:700; margin-bottom:10px;">📉 短期 (1-5日): {short_term}</div>
                <div style="margin-bottom:8px; font-size:0.85rem;">{st_signals_html}</div>
                <div style="color:#8899aa; font-size:0.82rem;">MA5趋势: {trend_short} | 研究重点: {'核验价格与成交量是否继续走弱' if short_term == '偏空' else '核验趋势能否得到成交量确认' if short_term == '偏多' else '等待更多数据确认方向'}</div>
            </div>
            <div style="background:rgba(255,255,255,0.04); border-radius:10px; padding:16px;">
                <div style="color:{lt_color}; font-size:1.15rem; font-weight:700; margin-bottom:10px;">📈 长期 (3-12月): {long_term}</div>
                <div style="margin-bottom:8px; font-size:0.85rem;">{lt_signals_html}</div>
                <div style="color:#8899aa; font-size:0.82rem;">存储周期: {pc_phase} | {rec_signal}</div>
                <div style="color:#8899aa; font-size:0.82rem;">研究重点: {'复核 AI/HBM 假设与公司实际暴露度' if score >= 55 else '复核 NAND/DRAM 价格与库存的时点' if score >= 45 else '复核周期拐点和财务数据完整性'}</div>
            </div>
        </div>

        <!-- 评估逻辑 & 权重说明 (含评分公式) -->
        <div style="background:rgba(255,255,255,0.03); border-radius:10px; padding:18px;">
            <div style="color:#90caf9; font-size:1.05rem; font-weight:700; margin-bottom:12px;">📐 评估逻辑 & 权重说明</div>
            <div style="font-size:0.85rem; color:#8899aa; line-height:2.0;">

                <!-- 研究信号公式 -->
                <div style="background:rgba(144,202,249,0.06); border:1px solid rgba(144,202,249,0.15); border-radius:8px; padding:14px; margin-bottom:16px;">
                    <div style="color:#e1e8ed; font-weight:700; margin-bottom:8px;">📏 研究信号计算</div>
                    <div style="font-family:'Consolas','Courier New',monospace; font-size:0.9rem; color:#90caf9; margin-bottom:8px;">
                        研究信号 = 短期技术(10%) + 存储周期(25%) + 分析师(12%) + HBM供需(8%) + 下游需求(8%) + 内部人(8%) + 股东(8%) + 技术节点(4%) + 行业对标(5%) + 财务修正(±25)
                    </div>
                    <div style="font-size:0.8rem; color:#556677;">
                        数据来源: {data_sources}
                    </div>
                </div>

                <div style="color:#e1e8ed; font-weight:700; margin:14px 0 8px;">一、短期技术面 (15%) — 信号规则</div>
                <table style="width:100%; border-collapse:collapse; font-size:0.85rem;">
                    <tr style="color:#8899aa;"><th style="text-align:left; padding:6px 10px;">指标</th><th style="text-align:left; padding:6px 10px;">权重</th><th style="text-align:left; padding:6px 10px;">信号规则</th><th style="text-align:left; padding:6px 10px;">当前值</th></tr>
                    <tr><td style="padding:6px 10px;">RSI(14)</td><td style="padding:6px 10px;">40%</td><td style="padding:6px 10px;">&gt;70超买偏空 / &lt;30超卖偏多</td><td style="padding:6px 10px; color:#ff9800;">{rsi:.1f}</td></tr>
                    <tr style="background:rgba(255,255,255,0.02);"><td style="padding:6px 10px;">MACD Hist</td><td style="padding:6px 10px;">40%</td><td style="padding:6px 10px;">&gt;0金叉偏多 / &lt;0死叉偏空</td><td style="padding:6px 10px; color:{'#4caf50' if macd_hist > 0 else '#f44336'};">{macd_hist:+.4f}</td></tr>
                    <tr><td style="padding:6px 10px;">量比</td><td style="padding:6px 10px;">20%</td><td style="padding:6px 10px;">&gt;1.5x放量, 结合RSI判断方向</td><td style="padding:6px 10px; color:#8899aa;">{vol_ratio:.1f}x</td></tr>
                </table>

                <div style="color:#e1e8ed; font-weight:700; margin:16px 0 8px;">二、中长期趋势 (90%) — 多维综合</div>
                <table style="width:100%; border-collapse:collapse; font-size:0.85rem;">
                    <tr style="color:#8899aa;"><th style="text-align:left; padding:6px 10px;">维度</th><th style="text-align:left; padding:6px 10px;">权重</th><th style="text-align:left; padding:6px 10px;">数据来源</th><th style="text-align:left; padding:6px 10px;">信号 / 当前值</th></tr>
                    <tr><td style="padding:6px 10px;">📦 存储周期</td><td style="padding:6px 10px;">25%</td><td style="padding:6px 10px;">库存/DRAM/NAND/CapEx/HBM/下游需求/技术节点</td><td style="padding:6px 10px; color:#90caf9;">{score}/100 ({rating})</td></tr>
                    <tr style="background:rgba(255,255,255,0.02);"><td style="padding:6px 10px;">📊 分析师共识</td><td style="padding:6px 10px;">12%</td><td style="padding:6px 10px;">get_stock_recommendation_estimate</td><td style="padding:6px 10px; color:#4caf50;">{rec_total}位分析师, 均值{rec_mean_val:.2f} ({'买入' if rec_mean_val <= 2 else '持有' if rec_mean_val <= 3 else '卖出'})</td></tr>
                    <tr><td style="padding:6px 10px;">🚀 HBM 供需</td><td style="padding:6px 10px;">8%</td><td style="padding:6px 10px;">NVDA季报→HBM需求 vs 产能 | 🔧公司: {hbm_tag}</td><td style="padding:6px 10px; color:#ff9800;">得分{hbm_score} ({hbm_tag})</td></tr>
                    <tr style="background:rgba(255,255,255,0.02);"><td style="padding:6px 10px;">🎯 下游需求</td><td style="padding:6px 10px;">8%</td><td style="padding:6px 10px;">WebSearch→TrendForce/IDC | 🔧公司营收加权</td><td style="padding:6px 10px; color:#8899aa;">{demand_detail}</td></tr>
                    <tr><td style="padding:6px 10px;">🔍 内部人交易</td><td style="padding:6px 10px;">8%</td><td style="padding:6px 10px;">get_stock_insider_transaction → SEC Form 4</td><td style="padding:6px 10px; color:{insider_color};">{insider_signal}</td></tr>
                    <tr style="background:rgba(255,255,255,0.02);"><td style="padding:6px 10px;">📄 股东变动</td><td style="padding:6px 10px;">8%</td><td style="padding:6px 10px;">get_stock_shareholder_report → 13F/13D/13G</td><td style="padding:6px 10px; color:#8899aa;">{shareholder_signal}</td></tr>
                    <tr><td style="padding:6px 10px;">🔬 技术节点</td><td style="padding:6px 10px;">4%</td><td style="padding:6px 10px;">WebSearch→行业报告 | 🔧公司实际节点</td><td style="padding:6px 10px; color:#8899aa;">{tech_detail}</td></tr>
                    <tr style="background:rgba(255,255,255,0.02);"><td style="padding:6px 10px;">🏷️ 行业对标</td><td style="padding:6px 10px;">5%</td><td style="padding:6px 10px;">mktfin_metric → PE vs 同行(WDC/SNDK/STX)</td><td style="padding:6px 10px; color:#8899aa;">{peer_signal}</td></tr>
                    <tr><td style="padding:6px 10px;">💰 财务质量修正</td><td style="padding:6px 10px;">±25</td><td style="padding:6px 10px;">净利率/毛利率/ROE/负债率/PB/Beta → get_fina_ex + mktfin_metric + pv_metric</td><td style="padding:6px 10px; color:{'#4caf50' if finance_mod >= 0 else '#f44336'};">{finance_mod:+d}</td></tr>
                </table>

                <div style="color:#e1e8ed; font-weight:700; margin:16px 0 8px;">三、存储周期评分构成 (内部6模块)</div>
                <table style="width:100%; border-collapse:collapse; font-size:0.85rem;">
                    <tr style="color:#8899aa;"><th style="text-align:left; padding:6px 10px;">模块</th><th style="text-align:left; padding:6px 10px;">权重</th><th style="text-align:left; padding:6px 10px;">数据来源</th><th style="text-align:left; padding:6px 10px;">信号</th></tr>
                    <tr><td style="padding:6px 10px;">库存周期</td><td style="padding:6px 10px;">20%</td><td style="padding:6px 10px;">🟢 get_fina_ex → inventory/COGS (实时)</td><td style="padding:6px 10px;">{inv_analysis.get('cycle_phase', 'N/A')}</td></tr>
                    <tr style="background:rgba(255,255,255,0.02);"><td style="padding:6px 10px;">价格周期</td><td style="padding:6px 10px;">25%</td><td style="padding:6px 10px;">WebSearch → TrendForce DRAM/NAND合约价</td><td style="padding:6px 10px;">{price_cycle.get('cycle_phase', 'N/A')}</td></tr>
                    <tr><td style="padding:6px 10px;">CapEx趋势</td><td style="padding:6px 10px;">15%</td><td style="padding:6px 10px;">🟢 get_fina_ex → cfs_capex_total (实时)</td><td style="padding:6px 10px;">{capex_analysis.get('expansion_phase', 'N/A') if capex_analysis else 'N/A'}</td></tr>
                    <tr style="background:rgba(255,255,255,0.02);"><td style="padding:6px 10px;">🚀 HBM 供需</td><td style="padding:6px 10px;">20%</td><td style="padding:6px 10px;">WebSearch → NVDA季报 + 晶圆产能估算</td><td style="padding:6px 10px;">{memory_assessment.get('detail',{}).get('HBM供需','N/A')}</td></tr>
                    <tr><td style="padding:6px 10px;">🎯 下游需求</td><td style="padding:6px 10px;">15%</td><td style="padding:6px 10px;">WebSearch → TrendForce/IDC 终端拆分</td><td style="padding:6px 10px;">{memory_assessment.get('detail',{}).get('下游需求','N/A')}</td></tr>
                    <tr style="background:rgba(255,255,255,0.02);"><td style="padding:6px 10px;">🔬 技术节点</td><td style="padding:6px 10px;">5%</td><td style="padding:6px 10px;">WebSearch → 行业路线图</td><td style="padding:6px 10px;">{memory_assessment.get('detail',{}).get('技术节点','N/A')}</td></tr>
                </table>

                <div style="color:#e1e8ed; font-weight:700; margin:16px 0 8px;">四、财务质量修正明细 ({finance_mod:+d} 分)</div>
                <table style="width:100%; border-collapse:collapse; font-size:0.85rem;">
                    <tr style="color:#8899aa;"><th style="text-align:left; padding:6px 10px;">指标</th><th style="text-align:left; padding:6px 10px;">当前值</th><th style="text-align:left; padding:6px 10px;">修正规则</th></tr>
                    <tr><td style="padding:6px 10px;">单季净利率</td><td style="padding:6px 10px;">{nm_latest:.1f}%</td><td style="padding:6px 10px;">&gt;30%:+8, &gt;15%:+5, &lt;5%:-5, &lt;0:-12</td></tr>
                    <tr style="background:rgba(255,255,255,0.02);"><td style="padding:6px 10px;">毛利率</td><td style="padding:6px 10px;">{gross_margin:.1f}%</td><td style="padding:6px 10px;">&gt;50%:+6, &gt;35%:+3, &lt;20%:-6</td></tr>
                    <tr><td style="padding:6px 10px;">ROE</td><td style="padding:6px 10px;">{roe_val:.1f}%</td><td style="padding:6px 10px;">&gt;30%:+6, &gt;15%:+3, &lt;5%:-5</td></tr>
                    <tr style="background:rgba(255,255,255,0.02);"><td style="padding:6px 10px;">负债率(D/E)</td><td style="padding:6px 10px;">{debt_eq:.2f}</td><td style="padding:6px 10px;">&lt;0.3:+5, &lt;1.0:+2, &gt;3.0:-6</td></tr>
                    <tr><td style="padding:6px 10px;">PB</td><td style="padding:6px 10px;">{pb_val:.1f}</td><td style="padding:6px 10px;">&lt;1.5:+3, &gt;10:-3</td></tr>
                    <tr style="background:rgba(255,255,255,0.02);"><td style="padding:6px 10px;">Beta</td><td style="padding:6px 10px;">{beta_val:.1f}</td><td style="padding:6px 10px;">&lt;0.8:+2, &gt;2.0:-3</td></tr>
                </table>
            </div>
        </div>
    </div>"""


def _fig_financial_events(events: list) -> str:
    """财务披露事件时间线"""
    if not events:
        return "<div class='plot-container'><p style='color:#8899aa;'>暂无财务事件数据</p></div>"

    # 按日期倒序，取最近20条
    sorted_events = sorted(events, key=lambda x: x.get("date", ""), reverse=True)[:20]

    type_labels = {
        "EarningsReleases": "财报发布",
        "EarningsCallsAndPresentations": "电话会议/演示",
        "GuidanceCallsAndPresentations": "业绩指引",
        "EarningsPresentation": "财报演示",
        "GuidancePresentation": "指引演示",
        "EarningsPressConference": "新闻发布会",
        "InterimManagementStatementRelease": "中期声明",
    }

    # 按季度分组 (跳过无季度的事件)
    from collections import defaultdict
    by_quarter = defaultdict(list)
    for e in sorted_events:
        q = e.get("fiscal_quarter", "") or ""
        if not q or q == "nan":
            continue
        by_quarter[q].append(e)

    html_parts = []
    for q in sorted(by_quarter.keys(), reverse=True):
        q_events = by_quarter[q]
        q_display = q.upper()
        html_parts.append(
            f"<div style='margin-bottom:12px;'>"
            f"<div style='color:#90caf9; font-size:0.85rem; font-weight:700; margin-bottom:6px;'>{q_display}</div>"
        )
        for e in q_events:
            d = e.get("date", "")
            if len(d) == 8:
                d = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            etype = e.get("event_type", "")
            label = type_labels.get(etype, etype)
            desc = e.get("event", "")
            html_parts.append(
                f"<div style='display:flex; gap:12px; padding:4px 0; font-size:0.82rem;'>"
                f"<span style='color:#8899aa; min-width:85px;'>{d}</span>"
                f"<span style='color:#4caf50; min-width:80px; font-size:0.75rem;'>{label}</span>"
                f"<span style='color:#e1e8ed;'>{desc}</span>"
                f"</div>"
            )
        html_parts.append("</div>")

    return f"<div class='plot-container'>{''.join(html_parts)}</div>"


def _fig_ir_events(events: list) -> str:
    """投资者关系活动"""
    if not events:
        return "<div class='plot-container'><p style='color:#8899aa;'>暂无投资者关系活动数据</p></div>"

    sorted_events = sorted(events, key=lambda x: x.get("date", ""), reverse=True)[:15]

    type_labels = {
        "ConferencePresentations": "会议演讲",
        "Roadshow": "路演",
        "InvestorDay": "投资者日",
        "ShareholderMeeting": "股东大会",
        "AnalystMeeting": "分析师会议",
    }

    html_parts = []
    html_parts.append(
        "<div style='color:#90caf9; font-size:0.85rem; font-weight:700; margin-bottom:12px;'>"
        "投资者关系活动 (近2年)</div>"
    )
    for e in sorted_events:
        d = e.get("date", "")
        if len(d) == 8:
            d = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        etype = e.get("event_type", "")
        label = type_labels.get(etype, etype)
        desc = e.get("event", "")
        html_parts.append(
            f"<div style='display:flex; gap:12px; padding:4px 0; font-size:0.82rem; border-bottom:1px solid #1a2a3a;'>"
            f"<span style='color:#8899aa; min-width:85px;'>{d}</span>"
            f"<span style='color:#ff9800; min-width:70px; font-size:0.75rem;'>{label}</span>"
            f"<span style='color:#e1e8ed; flex:1;'>{desc}</span>"
            f"</div>"
        )

    return f"<div class='plot-container'>{''.join(html_parts)}</div>"


def _fig_insider_trades(trades: list) -> str:
    """内部人交易汇总 (近2年，聚合去重)"""
    if not trades:
        return "<div class='plot-container'><p style='color:#8899aa;'>暂无内部人交易数据</p></div>"

    html_parts = []
    # 按最近交易日排序
    trades_sorted = sorted(trades, key=lambda x: x.get("last_date", ""), reverse=True)

    html_parts.append(
        "<table class='highlight-table'>"
        "<tr><th>交易日期</th><th>内部人</th><th>买入股数</th><th>买入金额</th><th>卖出股数</th><th>卖出金额</th></tr>"
    )
    for t in trades_sorted[:15]:
        name = t.get("name", "")
        last = t.get("last_date", "")
        if len(last) == 8:
            last = f"{last[:4]}-{last[4:6]}-{last[6:8]}"

        def _fmt_shares(n):
            if not n: return "--"
            if n >= 1e6: return f"{n/1e6:.1f}M"
            if n >= 1e3: return f"{n/1e3:.0f}K"
            return str(int(n))

        def _fmt_value(n):
            if not n: return "--"
            return f"${abs(n)/1e6:.1f}M"

        buy_s = _fmt_shares(t.get("total_buy_shares"))
        buy_v = _fmt_value(t.get("total_buy_value"))
        sell_s = _fmt_shares(t.get("total_sell_shares"))
        sell_v = _fmt_value(t.get("total_sell_value"))

        html_parts.append(
            f"<tr><td style='font-size:0.8rem;'>{last}</td><td>{name}</td>"
            f"<td>{buy_s}</td><td>{buy_v}</td>"
            f"<td>{sell_s}</td><td style='color:#f44336;'>{sell_v}</td></tr>"
        )

    html_parts.append("</table>")
    html_parts.append(
        "<p style='color:#556677; font-size:0.75rem; margin-top:8px;'>"
        "数据来源: SEC Form 4 申报，已排除税缴类小交易，仅展示总价值>$100K的内部人"
        "</p>"
    )
    return f"<div class='plot-container'>{''.join(html_parts)}</div>"


def _fig_shareholder_reports(reports: list) -> str:
    """股东持股报告 (大额变动)"""
    if not reports:
        return "<div class='plot-container'><p style='color:#8899aa;'>暂无大额股东变动报告</p></div>"

    html_parts = []
    html_parts.append(
        "<table class='highlight-table'>"
        "<tr><th>报告日期</th><th>投资者</th><th>持股数</th><th>占比</th><th>变动方向</th><th>变动量</th><th>市值</th></tr>"
    )
    for r in reports[:15]:
        d = r.get("date", "")
        if len(d) == 8:
            d = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        name = str(r.get("name", ""))[:40]
        shares = r.get("shares")
        ratio = r.get("ratio")
        change = r.get("change")
        value = r.get("value")

        shares_str = f"{shares/1e6:.1f}M" if shares and shares > 1e6 else (f"{shares/1e3:.0f}K" if shares else "--")
        ratio_str = f"{ratio*100:.2f}%" if ratio is not None and ratio < 1 else (f"{ratio:.2f}%" if ratio else "--")
        if change:
            # change 可能是股数也可能是比例
            if abs(change) <= 1:
                # 比例形式 (如 0.05 = +5%)
                direction = "增持 ▲" if change > 0 else "减持 ▼"
                dir_color = "#4caf50" if change > 0 else "#f44336"
                chg_str = f"{change*100:+.1f}%"
            else:
                # 股数形式
                direction = "增持 ▲" if change > 0 else "减持 ▼"
                dir_color = "#4caf50" if change > 0 else "#f44336"
                chg_str = f"{change/1e6:+.1f}M" if abs(change) > 1e6 else f"{change/1e3:+.0f}K"
        else:
            direction = "新进 ◆"
            dir_color = "#ff9800"
            chg_str = "新进"
        val_str = f"${value/1e9:.1f}B" if value and value > 1e9 else (f"${value/1e6:.1f}M" if value else "--")

        html_parts.append(
            f"<tr><td style='font-size:0.75rem;'>{d}</td><td>{name}</td><td>{shares_str}</td>"
            f"<td>{ratio_str}</td><td style='color:{dir_color}; font-weight:600;'>{direction}</td>"
            f"<td style='color:{dir_color};'>{chg_str}</td><td>{val_str}</td></tr>"
        )
    html_parts.append("</table>")
    html_parts.append(
        "<p style='color:#556677; font-size:0.75rem; margin-top:8px;'>"
        "数据来源: SEC 13F/13D/13G 申报，仅展示持股占比>0.5%或变动>0.5%的机构"
        "</p>"
    )
    return f"<div class='plot-container'>{''.join(html_parts)}</div>"


def _fig_hbm_gpu_demand(hbm_demand: dict = None, hbm_exposure: dict = None) -> str:
    """HBM GPU 需求量化模型可视化 + 公司 HBM 暴露度"""
    if not hbm_demand or not hbm_demand.get("available"):
        return "<div class='plot-container'><p style='color:#8899aa;'>暂无 HBM 需求量化数据</p></div>"

    html_parts = []

    # --- 公司 HBM 暴露度卡片 (差异化) ---
    if hbm_exposure:
        is_supplier = hbm_exposure.get("is_key_hbm_supplier", False)
        share = hbm_exposure.get("company_hbm_market_share")
        revenue_est = hbm_exposure.get("hbm_revenue_estimate")

        if is_supplier and share:
            card_color = "#4caf50"
            card_icon = "✅"
            status_text = f"HBM 主要供应商 | 市场份额 ~{share*100:.0f}%"
            if revenue_est:
                status_text += f" | 估算 HBM 营收 ~${revenue_est:.0f}亿"
        else:
            card_color = "#ff9800"
            card_icon = "⚠️"
            status_text = "非 HBM 供应商 | AI 需求通过企业级 SSD/HDD 间接受益"

        html_parts.append(
            f"<div style='background:#1a2332; border:2px solid {card_color}; border-radius:10px; "
            f"padding:14px; margin-bottom:16px;'>"
            f"<div style='display:flex; align-items:center; gap:10px;'>"
            f"<span style='font-size:1.5rem;'>{card_icon}</span>"
            f"<div>"
            f"<div style='color:#e1e8ed; font-size:0.9rem; font-weight:700;'>{status_text}</div>"
            f"<div style='color:#8899aa; font-size:0.8rem;'>{hbm_exposure.get('assessment', '')}</div>"
            f"</div></div></div>"
        )

    # --- 供需缺口总览卡片 ---
    gaps = hbm_demand.get("yearly_gaps", {})
    latest_gap = gaps.get("2026", gaps.get("2025", {}))
    gap_status = latest_gap.get("status", "未知")
    gap_color = "#f44336" if gap_status == "供给紧张" else ("#4caf50" if gap_status == "供需平衡" else "#ff9800")

    html_parts.append("<div style='display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px;'>")
    for yr in ["2024", "2025", "2026"]:
        g = gaps.get(yr, {})
        demand = g.get("demand_m_gb", 0)
        supply = g.get("supply_m_gb", 0)
        gap_val = g.get("gap_m_gb", 0)
        gap_pct = g.get("gap_ratio_pct", 0)
        yr_status = g.get("status", "")
        yr_color = "#f44336" if "紧张" in yr_status else ("#4caf50" if "平衡" in yr_status else "#ff9800")

        html_parts.append(
            f"<div style='flex:1; min-width:150px; background:#1a2332; border:1px solid #2a3a4a; border-radius:8px; padding:14px; text-align:center;'>"
            f"<div style='color:#8899aa; font-size:0.75rem;'>HBM 供需 ({yr})</div>"
            f"<div style='font-size:0.9rem; font-weight:700; color:#e1e8ed; margin:6px 0;'>需求 {demand:.0f}M GB</div>"
            f"<div style='font-size:0.9rem; color:#8899aa;'>供给 {supply:.0f}M GB</div>"
            f"<div style='font-size:0.85rem; font-weight:700; color:{yr_color}; margin-top:4px;'>" +
            (f"短缺 {gap_pct:.1f}% — {yr_status}" if gap_pct > 0 else f"盈余 {abs(gap_pct):.1f}% — {yr_status}") +
            f"</div>"
            f"</div>"
        )
    html_parts.append("</div>")

    # --- GPU 各代 HBM 容量迭代图 ---
    gen_data = hbm_demand.get("gen_analysis", [])
    if gen_data:
        gen_names = [g["name"] for g in gen_data]
        gen_capacities = [g["capacity_gb"] for g in gen_data]
        gen_types = [g["hbm_type"] for g in gen_data]
        gen_status = [g["status"] for g in gen_data]

        fig = go.Figure()

        # 柱状图: HBM 容量 — 增长率合并到 text 中，避免重叠
        colors = ["#2196f3" if s == "量产" else "#4caf50" if s == "上量中" else "#ff9800" if s == "试产" else "#9c27b0" for s in gen_status]
        bar_texts = []
        for i, g in enumerate(gen_data):
            c = g["capacity_gb"]
            t = g["hbm_type"]
            s = g["status"]
            growth = g.get("next_gen_growth_pct")
            if growth:
                bar_texts.append(f"{c}GB | {t} | {s}<br>↑+{growth:.0f}% 下一代")
            else:
                bar_texts.append(f"{c}GB | {t} | {s}")

        fig.add_trace(go.Bar(
            x=gen_names, y=gen_capacities,
            marker_color=colors,
            text=bar_texts,
            textposition="outside",
            textfont=dict(size=10, color="#e1e8ed"),
            name="HBM 容量 (GB)"
        ))

        fig.update_layout(
            template="plotly_dark", height=420,
            paper_bgcolor="#1a2332", plot_bgcolor="#1a2332",
            margin=dict(l=20, r=20, t=50, b=20),
            title="NVIDIA GPU 各代 HBM 容量迭代 (GB) — 柱上方标注含下一代增长率",
            title_font=dict(size=14, color="#90caf9"),
            yaxis=dict(title="HBM 容量 (GB)", gridcolor="#2a3a4a",
                       range=[0, max(gen_capacities) * 1.35]),
            xaxis=dict(gridcolor="#2a3a4a"),
            showlegend=False
        )
        html_parts.append(fig.to_html(full_html=False, include_plotlyjs=False, config={
            'displaylogo': False,
            'modeBarButtonsToRemove': ['zoom2d','pan2d','select2d','lasso2d','zoomIn2d','zoomOut2d','resetScale2d','hoverClosestCartesian','hoverCompareCartesian','toggleSpikelines'],
            'displayModeBar': True
        }))

    # --- 季度需求趋势图 (营收反推) ---
    demand_q = hbm_demand.get("demand_by_quarter", [])
    if demand_q:
        q_labels = [d["quarter"] for d in demand_q]
        q_revenue = [d.get("compute_rev_100m_usd", 0) / 10 for d in demand_q]  # → $B
        q_hbm_gb = [d["avg_hbm_per_gpu_gb"] for d in demand_q]
        q_total_demand = [d["total_hbm_demand_m_gb"] for d in demand_q]

        fig2 = make_subplots(specs=[[{"secondary_y": True}]])

        fig2.add_trace(go.Bar(
            x=q_labels, y=q_revenue,
            name="NVDA Compute营收 ($B)",
            marker_color="#76ff03", opacity=0.7,
            hovertemplate="%{x}<br>Compute营收: $%{y:.1f}B<extra></extra>"
        ), secondary_y=False)

        fig2.add_trace(go.Scatter(
            x=q_labels, y=q_hbm_gb,
            mode="lines+markers",
            name="每 GPU HBM (GB)",
            line=dict(color="#ff9800", width=2.5),
            marker=dict(size=6)
        ), secondary_y=True)

        fig2.update_layout(
            template="plotly_dark", height=400,
            paper_bgcolor="#1a2332", plot_bgcolor="#1a2332",
            margin=dict(l=20, r=20, t=80, b=20),
            title="NVDA Compute(GPU)营收 & 每卡 HBM 容量<br><span style='font-size:11px;color:#8899aa;'>推导公式: 需求(GB) = 营收($B)÷ASP($K)×HBM(GB)</span>",
            title_font=dict(size=14, color="#90caf9"),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="top", y=1.22, xanchor="center", x=0.5)
        )
        fig2.update_yaxes(title_text="Compute 营收 ($B)", secondary_y=False, gridcolor="#2a3a4a")
        fig2.update_yaxes(title_text="每卡 HBM (GB)", secondary_y=True, gridcolor="#2a3a4a")
        fig2.update_xaxes(gridcolor="#2a3a4a")

        html_parts.append(fig2.to_html(full_html=False, include_plotlyjs=False, config={
            'displaylogo': False,
            'modeBarButtonsToRemove': ['zoom2d','pan2d','select2d','lasso2d','zoomIn2d','zoomOut2d','resetScale2d','hoverClosestCartesian','hoverCompareCartesian','toggleSpikelines'],
            'displayModeBar': True
        }))

    # --- 评估结论文本 ---
    html_parts.append(
        f"<div style='background:rgba(144,202,249,0.06); border:1px solid {gap_color}; "
        f"border-radius:8px; padding:14px; margin-top:12px;'>"
        f"<div style='color:#90caf9; font-size:0.85rem; font-weight:700; margin-bottom:4px;'>📊 HBM 需求评估</div>"
        f"<div style='color:#d0d8e0; font-size:0.85rem; line-height:1.6;'>{hbm_demand.get('assessment', '')}</div>"
        f"<div style='color:#8899aa; font-size:0.75rem; margin-top:8px;'>"
        f"推导链路: NVDA 季报 Compute 营收($B) ÷ 加权ASP($K) → GPU出货量(K) × 每卡HBM(GB) → NVIDIA HBM需求 "
        f"× 1.30(非NVIDIA) → 全行业需求 vs 产能供给。"
        f"GPU 每代 HBM 容量增长 50-100%，供给端扩产速度较慢。"
        f"</div></div>"
    )

    return f"<div class='plot-container'>{''.join(html_parts)}</div>"


def _fig_end_market_demand(end_market: dict = None, ticker: str = "MU") -> str:
    """下游需求终端拆分可视化 + 公司业务结构"""
    if not end_market or not end_market.get("available"):
        return "<div class='plot-container'><p style='color:#8899aa;'>暂无下游需求拆分数据</p></div>"

    html_parts = []

    # --- 公司业务结构卡片 (从 industry_data.json company_profiles 读取) ---
    try:
        import json as _json, os as _os
        _cfg = _json.load(open(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                            "config", "industry_data.json"), 'r', encoding='utf-8'))
        prof = _cfg.get("company_profiles", {}).get(ticker, {})
    except Exception:
        prof = {}
    if prof:
        mix = prof.get("revenue_mix", {})
        html_parts.append(
            f"<div style='background:#1a2332; border:1px solid #2a3a4a; border-radius:8px; "
            f"padding:12px; margin-bottom:16px; font-size:0.82rem;'>"
            f"<div style='color:#90caf9; font-weight:700; margin-bottom:6px;'>🏢 {prof.get('name',ticker)} 业务结构 (影响下游需求敞口)</div>"
            f"<div style='color:#8899aa; margin-bottom:8px;'>{prof.get('description','')}</div>"
            f"<div style='display:flex; gap:8px; flex-wrap:wrap;'>" +
            "".join([
                f"<span style='background:rgba(33,150,243,0.2); border-radius:4px; padding:2px 8px; "
                f"font-size:0.78rem;'>{k.upper()}: {v*100:.0f}%</span>"
                for k, v in sorted(mix.items(), key=lambda x: -x[1]) if v > 0
            ]) +
            f"</div></div>"
        )

    # --- 三个卡片: DRAM / NAND / HBM 加权增速 ---
    dram = end_market.get("dram", {})
    nand = end_market.get("nand", {})
    hbm = end_market.get("hbm", {})

    html_parts.append("<div style='display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px;'>")
    for label, data, emoji, desc_color in [
        ("DRAM", dram, "📀", "#2196f3"),
        ("NAND", nand, "💿", "#4caf50"),
        ("HBM", hbm, "🚀", "#ff9800"),
    ]:
        growth = data.get("weighted_growth_pct", 0)
        status = data.get("status", "")
        growth_color = "#4caf50" if growth > 15 else ("#ff9800" if growth > 5 else "#f44336")
        html_parts.append(
            f"<div style='flex:1; min-width:150px; background:#1a2332; border:1px solid {desc_color}44; "
            f"border-radius:10px; padding:16px; text-align:center;'>"
            f"<div style='font-size:1.5rem; margin-bottom:4px;'>{emoji}</div>"
            f"<div style='color:{desc_color}; font-size:0.85rem; font-weight:700;'>{label}</div>"
            f"<div style='font-size:1.6rem; font-weight:900; color:{growth_color}; margin:6px 0;'>{growth:+.1f}%</div>"
            f"<div style='color:#8899aa; font-size:0.75rem;'>加权需求增速</div>"
            f"<div style='color:#90caf9; font-size:0.78rem; margin-top:4px;'>{status}</div>"
            f"</div>"
        )
    html_parts.append("</div>")

    # --- 堆叠柱状图: 按终端市场拆分的需求份额+增速 ---
    # DRAM 和 NAND 用子图并排
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("DRAM 终端需求拆分", "NAND 终端需求拆分"),
        specs=[[{"secondary_y": True}, {"secondary_y": True}]]
    )

    for col_idx, (mem_type, segments) in enumerate([
        ("dram", dram.get("segments", [])),
        ("nand", nand.get("segments", []))
    ]):
        col = col_idx + 1
        seg_names = [s["segment"] for s in segments]
        seg_shares = [s["share_pct"] for s in segments]
        seg_growth = [s["yoy_growth_pct"] for s in segments]

        bar_colors = ["#2196f3", "#4caf50", "#ff9800", "#9c27b0", "#e91e63"][:len(seg_names)]

        fig.add_trace(go.Bar(
            x=seg_names, y=seg_shares,
            name="份额 %",
            marker_color=bar_colors,
            marker_opacity=0.85,
            text=[f"{s}%" for s in seg_shares],
            textposition="inside",
            textfont=dict(size=10, color="#fff"),
            showlegend=(col == 1)
        ), row=1, col=col, secondary_y=False)

        fig.add_trace(go.Scatter(
            x=seg_names, y=seg_growth,
            mode="markers+lines",
            name="YoY 增速 %",
            line=dict(color="#ff5722", width=2, dash="dot"),
            marker=dict(size=10, symbol="diamond", color="#ff5722"),
            showlegend=(col == 1)
        ), row=1, col=col, secondary_y=True)

        fig.add_hline(y=0, line_dash="solid", line_color="#555", opacity=0.5,
                      row=1, col=col, secondary_y=True)

        fig.update_yaxes(title_text="份额 (%)", secondary_y=False, range=[0, 50],
                         row=1, col=col, gridcolor="#2a3a4a")
        fig.update_yaxes(title_text="YoY 增速 (%)", secondary_y=True,
                         row=1, col=col, gridcolor="#2a3a4a")
        fig.update_xaxes(tickangle=-20, row=1, col=col)

    fig.update_layout(
        template="plotly_dark", height=400,
        paper_bgcolor="#1a2332", plot_bgcolor="#1a2332",
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.08),
        barmode="group"
    )
    html_parts.append(fig.to_html(full_html=False, include_plotlyjs=False, config={
        'displaylogo': False,
        'modeBarButtonsToRemove': ['zoom2d','pan2d','select2d','lasso2d','zoomIn2d','zoomOut2d','resetScale2d','hoverClosestCartesian','hoverCompareCartesian','toggleSpikelines'],
        'displayModeBar': True
    }))

    # --- HBM 应用场景拆分 (饼图) ---
    hbm_segments = hbm.get("segments", [])
    if hbm_segments:
        hbm_labels = [s["segment"] for s in hbm_segments]
        hbm_shares = [s["share_pct"] for s in hbm_segments]
        hbm_drivers = [s.get("driver", "") for s in hbm_segments]

        fig2 = go.Figure()
        fig2.add_trace(go.Pie(
            labels=hbm_labels, values=hbm_shares,
            hole=0.45,
            text=[f"{l}<br>{s}%" for l, s in zip(hbm_labels, hbm_shares)],
            textinfo="text",
            textfont=dict(size=11, color="#e1e8ed"),
            marker_colors=["#2196f3", "#4caf50", "#ff9800", "#9c27b0"],
            hovertemplate="%{label}: %{value}%<br>%{customdata}<extra></extra>",
            customdata=hbm_drivers
        ))

        fig2.update_layout(
            template="plotly_dark", height=380,
            paper_bgcolor="#1a2332", plot_bgcolor="#1a2332",
            margin=dict(l=20, r=20, t=40, b=60),
            title="HBM 应用场景拆分",
            title_font=dict(size=14, color="#90caf9"),
            showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5,
                       font=dict(size=11))
        )
        html_parts.append(fig2.to_html(full_html=False, include_plotlyjs=False, config={
            'displaylogo': False,
            'modeBarButtonsToRemove': ['zoom2d','pan2d','select2d','lasso2d','zoomIn2d','zoomOut2d','resetScale2d','hoverClosestCartesian','hoverCompareCartesian','toggleSpikelines'],
            'displayModeBar': True
        }))

    # --- 综合评估 ---
    assessments = end_market.get("assessments", {})
    assessment_texts = []
    for key in ["dram", "nand", "hbm"]:
        if key in assessments:
            assessment_texts.append(
                f"<div style='padding:4px 0; font-size:0.83rem;'>"
                f"<b style='color:#90caf9;'>{key.upper()}:</b> {assessments[key]}"
                f"</div>"
            )
    html_parts.append(
        f"<div style='background:rgba(255,255,255,0.03); border-radius:8px; padding:14px; margin-top:12px;'>"
        f"<div style='color:#90caf9; font-size:0.85rem; font-weight:700; margin-bottom:8px;'>📊 下游需求综合评估</div>"
        f"{''.join(assessment_texts)}"
        f"<div style='color:#8899aa; font-size:0.75rem; margin-top:8px;'>"
        f"数据来源: TrendForce/IDC/Gartner 公开摘要 + AI 推算 | "
        f"HBM 需求完全由 AI GPU 驱动，DRAM/NAND 需求由多元下游终端共同决定。"
        f"</div></div>"
    )

    return f"<div class='plot-container'>{''.join(html_parts)}</div>"


def _fig_technology_nodes(tech_position: dict = None, ticker: str = "MU") -> str:
    """技术节点路线图可视化 + 公司位置高亮"""
    if not tech_position:
        return "<div class='plot-container'><p style='color:#8899aa;'>暂无技术节点数据</p></div>"

    dram_nodes = tech_position.get("dram_nodes", [])
    nand_nodes = tech_position.get("nand_nodes", [])

    # 读取公司技术定位
    try:
        import json as _json, os as _os
        _cfg = _json.load(open(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                            "config", "industry_data.json"), 'r', encoding='utf-8'))
        comp = _cfg.get("company_profiles", {}).get(ticker, {})
    except Exception:
        comp = {}

    html_parts = []

    # 当前主力节点信息卡片 (含公司定位)
    html_parts.append("<div style='display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px;'>")
    cur_dram = tech_position.get("current_primary_dram", "未知")
    next_dram = tech_position.get("next_dram_node", "未知")
    cur_nand = tech_position.get("current_primary_nand", "未知")
    next_nand = tech_position.get("next_nand_node", "未知")

    company_dram = comp.get("dram_node", "不涉及")
    company_nand = comp.get("nand_node", "不涉及")

    html_parts.append(
        f"<div style='flex:1; min-width:180px; background:#1a2332; border:1px solid #2196f344; border-radius:8px; padding:12px;'>"
        f"<div style='color:#2196f3; font-size:0.8rem; font-weight:700;'>DRAM — 行业当前</div>"
        f"<div style='font-size:1.3rem; font-weight:700;'>{cur_dram}</div>"
        f"<div style='color:#8899aa; font-size:0.75rem;'>下一代行业: {next_dram}</div>"
        f"<div style='color:#90caf9; font-size:0.78rem; margin-top:4px; border-top:1px solid #2a3a4a; padding-top:4px;'>🏢 {comp.get('name',ticker)}: {company_dram}</div></div>")
    html_parts.append(
        f"<div style='flex:1; min-width:180px; background:#1a2332; border:1px solid #4caf5044; border-radius:8px; padding:12px;'>"
        f"<div style='color:#4caf50; font-size:0.8rem; font-weight:700;'>NAND — 行业当前</div>"
        f"<div style='font-size:1.3rem; font-weight:700;'>{cur_nand}</div>"
        f"<div style='color:#8899aa; font-size:0.75rem;'>下一代行业: {next_nand}</div>"
        f"<div style='color:#90caf9; font-size:0.78rem; margin-top:4px; border-top:1px solid #2a3a4a; padding-top:4px;'>🏢 {comp.get('name',ticker)}: {company_nand}</div></div>")
    html_parts.append("</div>")

    # DRAM 路线图时间线
    if dram_nodes:
        fig_dram = go.Figure()
        status_colors = {"量产": "#4caf50", "上量中": "#2196f3", "试产": "#ff9800", "试产/研发": "#ff9800",
                         "研发": "#9c27b0", "成熟": "#888"}
        dram_names = [n["node"] for n in dram_nodes]
        dram_years = [n.get("mass_production", "") for n in dram_nodes]
        dram_status = [n.get("status", "") for n in dram_nodes]
        dram_notes = [n.get("note", "") for n in dram_nodes]
        dram_colors = [status_colors.get(s, "#888") for s in dram_status]

        # 用年份做x轴，节点名做label
        fig_dram.add_trace(go.Scatter(
            x=dram_years, y=[1] * len(dram_nodes),
            mode="markers+text",
            marker=dict(size=18, color=dram_colors, symbol="square",
                       line=dict(color="#fff", width=1)),
            text=dram_names,
            textposition="top center",
            textfont=dict(size=10, color="#e1e8ed"),
            hovertemplate="%{text}<br>量产: %{x}<br>状态: %{customdata}<br>%{hovertext}<extra></extra>",
            customdata=dram_status,
            hovertext=dram_notes,
            name="DRAM"
        ))
        fig_dram.update_layout(
            template="plotly_dark", height=200,
            paper_bgcolor="#1a2332", plot_bgcolor="#1a2332",
            margin=dict(l=20, r=20, t=40, b=20),
            title="DRAM 技术节点路线图",
            title_font=dict(size=14, color="#90caf9"),
            yaxis=dict(visible=False, range=[0.5, 1.8]),
            xaxis=dict(title="量产年份", gridcolor="#2a3a4a", tickformat="%Y"),
            showlegend=False
        )
        html_parts.append(fig_dram.to_html(full_html=False, include_plotlyjs=False, config={
            'displaylogo': False, 'displayModeBar': False
        }))

    # NAND 路线图时间线
    if nand_nodes:
        fig_nand = go.Figure()
        status_colors = {"量产": "#4caf50", "上量中": "#2196f3", "试产": "#ff9800", "试产/量产": "#ff9800",
                         "研发": "#9c27b0", "成熟": "#888"}
        nand_names = [n["node"] for n in nand_nodes]
        nand_years = [n.get("mass_production", "") for n in nand_nodes]
        nand_status = [n.get("status", "") for n in nand_nodes]
        nand_notes = [n.get("note", "") for n in nand_nodes]
        nand_colors = [status_colors.get(s, "#888") for s in nand_status]

        fig_nand.add_trace(go.Scatter(
            x=nand_years, y=[1] * len(nand_nodes),
            mode="markers+text",
            marker=dict(size=18, color=nand_colors, symbol="diamond",
                       line=dict(color="#fff", width=1)),
            text=nand_names,
            textposition="top center",
            textfont=dict(size=10, color="#e1e8ed"),
            hovertemplate="%{text}<br>量产: %{x}<br>状态: %{customdata}<br>%{hovertext}<extra></extra>",
            customdata=nand_status,
            hovertext=nand_notes,
            name="NAND"
        ))
        fig_nand.update_layout(
            template="plotly_dark", height=200,
            paper_bgcolor="#1a2332", plot_bgcolor="#1a2332",
            margin=dict(l=20, r=20, t=40, b=20),
            title="NAND Flash 技术节点路线图",
            title_font=dict(size=14, color="#90caf9"),
            yaxis=dict(visible=False, range=[0.5, 1.8]),
            xaxis=dict(title="量产年份", gridcolor="#2a3a4a"),
            showlegend=False
        )
        html_parts.append(fig_nand.to_html(full_html=False, include_plotlyjs=False, config={
            'displaylogo': False, 'displayModeBar': False
        }))

    # 图例
    html_parts.append(
        "<div style='display:flex; gap:12px; flex-wrap:wrap; margin-top:8px; font-size:0.75rem; color:#8899aa;'>"
        "<span>🟢 量产</span><span>🔵 上量中</span><span>🟠 试产</span><span>🟣 研发</span><span>⬜ 成熟</span>"
        "</div>"
    )
    html_parts.append(
        "<div style='color:#8899aa; font-size:0.75rem; margin-top:4px;'>"
        "数据来源: WebSearch → TrendForce/行业报告 (每次分析前动态更新) | "
        f"DRAM 当前主力: {cur_dram} → 下一代: {next_dram} | "
        f"NAND 当前主力: {cur_nand} → 下一代: {next_nand}"
        "</div>"
    )

    return f"<div class='plot-container'>{''.join(html_parts)}</div>"


def _fig_recommendation(rec: dict) -> str:
    """分析师评级共识"""
    if not rec:
        return "<div class='plot-container'><p style='color:#8899aa;'>暂无分析师评级数据</p></div>"

    mean_rating = rec.get("mean", 0)
    strong_buy = int(rec.get("strong_buy_num", 0) or 0)
    buy = int(rec.get("buy_num", 0) or 0)
    hold = int(rec.get("hold", 0) or 0)
    sell = int(rec.get("sell_num", 0) or 0)
    strong_sell = int(rec.get("strong_sell_num", 0) or 0)
    total = strong_buy + buy + hold + sell + strong_sell

    if total == 0:
        return "<div class='plot-container'><p style='color:#8899aa;'>暂无分析师评级数据</p></div>"

    # Rating scale: 1=Strong Buy, 5=Strong Sell
    if mean_rating <= 1.5:
        consensus = "强烈买入"
    elif mean_rating <= 2.0:
        consensus = "买入"
    elif mean_rating <= 3.0:
        consensus = "持有"
    elif mean_rating <= 4.0:
        consensus = "卖出"
    else:
        consensus = "强烈卖出"

    max_count = max(strong_buy, buy, hold, sell, strong_sell)
    bar_max = max_count + 10  # 最大值加10，让比例更美观
    bar_pct = lambda c: min(c / bar_max * 100, 100) if bar_max > 0 else 0

    html_parts = []
    html_parts.append("<div style='display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px;'>")
    html_parts.append(
        f"<div style='background:#1a2332; border:1px solid #2a3a4a; border-radius:8px; padding:14px; "
        f"display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:100px;'>"
        f"<div style='color:#8899aa; font-size:0.75rem;'>分析师共识</div>"
        f"<div style='font-size:1.8rem; font-weight:700; color:#4caf50;'>{consensus}</div>"
        f"<div style='color:#8899aa; font-size:0.75rem;'>评级均值 {mean_rating:.2f} / 共 {total} 位分析师</div>"
        f"</div>"
    )

    bars_html = ""
    for label, count, color in [
        ("强烈买入", strong_buy, "#00c853"),
        ("买入", buy, "#4caf50"),
        ("持有", hold, "#ff9800"),
        ("卖出", sell, "#f44336"),
        ("强烈卖出", strong_sell, "#d50000"),
    ]:
        pct = bar_pct(count)
        bars_html += (
            f"<div style='display:flex; align-items:center; gap:8px; margin:4px 0;'>"
            f"<span style='min-width:50px; font-size:0.8rem; color:#8899aa;'>{label}</span>"
            f"<span style='min-width:25px; font-size:0.8rem;'>{count}</span>"
            f"<div style='flex:1; height:14px; background:#2a3a4a; border-radius:7px;'>"
            f"<div style='width:{pct}%; height:14px; background:{color}; border-radius:7px; min-width:{4 if count > 0 else 0}px;'></div>"
            f"</div></div>"
        )

    html_parts.append(
        f"<div style='flex:1; min-width:300px; background:#1a2332; border:1px solid #2a3a4a; border-radius:8px; padding:12px;'>"
        f"<div style='color:#90caf9; font-size:0.85rem; font-weight:700; margin-bottom:8px;'>评级分布</div>"
        f"{bars_html}</div>"
    )
    html_parts.append("</div>")

    return f"<div class='plot-container'>{''.join(html_parts)}</div>"


def _fig_backtest_results(bt: dict) -> str:
    """回测结果可视化"""
    points = bt.get("points", [])
    ic_3m = bt.get("ic_3m")
    ic_6m = bt.get("ic_6m")
    ic_12m = bt.get("ic_12m")
    ir_val = bt.get("ir")
    tier_3m = bt.get("tier_3m", [])
    high_wr = bt.get("high_win_rate")
    html = []

    # --- KPI 卡片 ---
    ic_color_3m = "#4caf50" if (ic_3m and ic_3m > 0.1) else ("#ff9800" if (ic_3m and ic_3m > 0) else "#f44336")
    ic_color_6m = "#4caf50" if (ic_6m and ic_6m > 0.1) else ("#ff9800" if (ic_6m and ic_6m > 0) else "#f44336")
    ic_color_12m = "#4caf50" if (ic_12m and ic_12m > 0.1) else ("#ff9800" if (ic_12m and ic_12m > 0) else "#f44336")
    ir_color = "#4caf50" if (ir_val and ir_val > 0.3) else ("#ff9800" if (ir_val and ir_val > 0) else "#f44336")
    html.append(f"""
    <div class="section-title" id="sec-backtest">📈 历史样本诊断</div>
    <div style="color:#8899aa; font-size:0.8rem; margin-bottom:12px;">
        基于 panda_data 历史行情与财务数据的相关性诊断 | 样本区间: {bt.get('date_range','')} | 共 {bt['n_points']} 个季度；不代表未来表现
    </div>
    <div style='display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px;'>
        <div style='flex:1; min-width:130px; background:#1a2332; border-radius:8px; padding:14px; text-align:center;'>
            <div style='color:#8899aa; font-size:0.7rem;'>IC (3月)</div>
            <div style='font-size:1.5rem; font-weight:700; color:{ic_color_3m};'>{ic_3m if ic_3m else 'N/A'}</div>
            <div style='font-size:0.7rem; color:#8899aa;'>{'强正相关' if (ic_3m and ic_3m>0.15) else ('正相关' if (ic_3m and ic_3m>0) else '负相关') if ic_3m else '样本不足'}</div>
        </div>
        <div style='flex:1; min-width:130px; background:#1a2332; border-radius:8px; padding:14px; text-align:center;'>
            <div style='color:#8899aa; font-size:0.7rem;'>IC (6月)</div>
            <div style='font-size:1.5rem; font-weight:700; color:{ic_color_6m};'>{ic_6m if ic_6m else 'N/A'}</div>
            <div style='font-size:0.7rem; color:#8899aa;'>{'强正相关' if (ic_6m and ic_6m>0.15) else ('正相关' if (ic_6m and ic_6m>0) else '负相关') if ic_6m else '样本不足'}</div>
        </div>
        <div style='flex:1; min-width:130px; background:#1a2332; border-radius:8px; padding:14px; text-align:center;'>
            <div style='color:#8899aa; font-size:0.7rem;'>IC (12月)</div>
            <div style='font-size:1.5rem; font-weight:700; color:{ic_color_12m};'>{ic_12m if ic_12m else 'N/A'}</div>
            <div style='font-size:0.7rem; color:#8899aa;'>{'强正相关' if (ic_12m and ic_12m>0.15) else ('正相关' if (ic_12m and ic_12m>0) else '负相关') if ic_12m else '样本不足'}</div>
        </div>
        <div style='flex:1; min-width:130px; background:#1a2332; border-radius:8px; padding:14px; text-align:center;'>
            <div style='color:#8899aa; font-size:0.7rem;'>IR (信息比率)</div>
            <div style='font-size:1.5rem; font-weight:700; color:{ir_color};'>{ir_val if ir_val else 'N/A'}</div>
            <div style='font-size:0.7rem; color:#8899aa;'>{'优秀' if (ir_val and ir_val>0.5) else ('良好' if (ir_val and ir_val>0.2) else '一般') if ir_val else '样本不足'}</div>
        </div>
        <div style='flex:1; min-width:130px; background:#1a2332; border-radius:8px; padding:14px; text-align:center;'>
            <div style='color:#8899aa; font-size:0.7rem;'>高分(≥60)胜率</div>
            <div style='font-size:1.5rem; font-weight:700; color:{'#4caf50' if (high_wr and high_wr>50) else '#f44336'}'>{high_wr if high_wr else 'N/A'}%</div>
            <div style='font-size:0.7rem; color:#8899aa;'>评分≥60后3月正收益概率</div>
        </div>
    </div>""")

    # --- 分层收益柱状图 ---
    if tier_3m:
        ranges_3m = [t["range"] for t in tier_3m]
        rets_3m = [t["avg_fwd_return"] or 0 for t in tier_3m]
        counts_3m = [t["count"] for t in tier_3m]
        colors_3m = ["#f44336" if r < 0 else "#4caf50" for r in rets_3m]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=ranges_3m, y=rets_3m,
            marker_color=colors_3m,
            text=[f"{r:+.1f}%<br>(n={c})" for r, c in zip(rets_3m, counts_3m)],
            textposition="outside",
            textfont=dict(size=11, color="#e1e8ed"),
            name="3月后续收益"
        ))
        fig.add_hline(y=0, line_color="#555", line_width=1)
        fig.update_layout(
            template="plotly_dark", height=350,
            paper_bgcolor="#1a2332", plot_bgcolor="#1a2332",
            margin=dict(l=20, r=20, t=40, b=20),
            title="评分分层 — 后续 3 月平均收益（历史样本）",
            title_font=dict(size=14, color="#90caf9"),
            yaxis=dict(title="平均收益 (%)", gridcolor="#2a3a4a", tickformat="+.1f"),
            xaxis=dict(title="评分区间", gridcolor="#2a3a4a"),
            showlegend=False
        )
        html.append(fig.to_html(full_html=False, include_plotlyjs=False, config={
            'displaylogo': False, 'displayModeBar': False
        }))

    # --- 散点图: 评分 vs 3月收益 ---
    valid = [(p["score"], p["fwd_3m_pct"], p["quarter"]) for p in points if p["fwd_3m_pct"] is not None]
    if len(valid) >= 4:
        xs = [v[0] for v in valid]
        ys = [v[1] for v in valid]
        labels = [v[2] for v in valid]

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers+text",
            marker=dict(size=12, color=["#4caf50" if y > 0 else "#f44336" for y in ys],
                       line=dict(color="#fff", width=1)),
            text=labels, textposition="top center",
            textfont=dict(size=9, color="#8899aa"),
            hovertemplate="%{text}<br>评分: %{x}<br>3月收益: %{y:+.1f}%<extra></extra>",
            name="评分vs收益"
        ))
        # 添加趋势线
        if len(xs) >= 3:
            z = np.polyfit(xs, ys, 1)
            p_line = np.poly1d(z)
            x_line = [min(xs), max(xs)]
            y_line = [p_line(x_line[0]), p_line(x_line[1])]
            fig2.add_trace(go.Scatter(
                x=x_line, y=y_line, mode="lines",
                line=dict(color="#ff9800", width=2, dash="dash"),
                name=f"趋势 (IC={ic_3m})"
            ))

        fig2.add_hline(y=0, line_color="#555", line_width=1)
        fig2.update_layout(
            template="plotly_dark", height=380,
            paper_bgcolor="#1a2332", plot_bgcolor="#1a2332",
            margin=dict(l=20, r=20, t=60, b=30),
            title="评分与后续 3 月收益的历史样本散点图",
            title_font=dict(size=14, color="#90caf9"),
            yaxis=dict(title="3月收益 (%)", gridcolor="#2a3a4a", tickformat="+.0f"),
            xaxis=dict(title="简化评分 (0-100)", gridcolor="#2a3a4a"),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )
        html.append(fig2.to_html(full_html=False, include_plotlyjs=False, config={
            'displaylogo': False, 'displayModeBar': False
        }))

    # --- 评分方法说明 ---
    html.append(
        "<div style='background:#1a2332; border:1px solid #2a3a4a; border-radius:8px; padding:14px; "
        "margin-top:12px; font-size:0.8rem; color:#8899aa;'>"
        "<div style='color:#90caf9; font-weight:700; margin-bottom:6px;'>📐 回测评分方法</div>"
        "<b>回测评分</b> = 技术面(14%) + 库存周期(18%) + 价格周期(18%) + 🆕HBM/AI需求(13%) + 毛利率(14%) + CapEx(11%) + 财务(12%)<br>"
        "使用 panda_data 历史行情+财务 + DRAM/NAND合约价(2022-Q1) + NVDA营收(2024-Q1起)。诊断从有HBM数据的2024年开始。<br>"
        "<b>IC(信息系数)</b> = 评分与后续实际收益的相关系数；IR 为 IC × √4 的派生统计。样本有限、回填数据和模型假设会显著影响结果。<br>"
        "此处仅用于检查历史样本的可解释性，不是交易策略、投资建议或未来表现承诺。"
        "</div>"
    )

    return f"<div class='plot-container' style='margin-top:24px;'>{''.join(html)}</div>"


def _html_footer() -> str:
    """HTML 尾部 + Tab 切换 JS"""
    return """
    <div class="footer-disclaimer">
        ⚠️ 免责声明：本报告由 AI 自动生成，仅用于研究与教育。<br>
        股票数据来自 panda_data；行业资料、截至日期和来源以本地配置及数据质量提示为准。<br>
        GPU 占比、供给增速等模型参数属于行业估算，可能与实际结果显著不同。<br>
        评分、分析师观点和历史回测不构成投资建议、交易指令、收益承诺或未来表现保证。
    </div>
    <script>
        // --- 初始化: 所有 tab 先全量渲染 (均已 display:block), 渲染完后隐藏非首个 ---
        var allTabs = document.querySelectorAll('.tab-panel');
        var tabGroups = {};
        allTabs.forEach(function(el) {
            var g = el.getAttribute('data-tab-group');
            var idx = parseInt(el.getAttribute('data-tab-index'));
            if (!tabGroups[g]) tabGroups[g] = [];
            tabGroups[g].push({el: el, idx: idx});
        });

        function resizeAllPlots() {
            var plots = document.querySelectorAll('.js-plotly-plot');
            plots.forEach(function(el) { Plotly.Plots.resize(el); });
        }

        // 页面加载: 先 resize, 再隐藏非首个 tab
        window.addEventListener('load', function() {
            resizeAllPlots();
            setTimeout(function() {
                resizeAllPlots();
                // 隐藏除第一个外的所有 tab
                for (var g in tabGroups) {
                    var tabs = tabGroups[g].sort(function(a,b){return a.idx-b.idx;});
                    for (var i = 1; i < tabs.length; i++) {
                        tabs[i].el.classList.remove('active');
                        tabs[i].el.classList.add('hidden');
                    }
                }
            }, 800);
        });

        window.addEventListener('resize', function() { resizeAllPlots(); });

        // 侧边栏滚动高亮
        var tocLinks = document.querySelectorAll('.toc-sidebar a');
        var sectionIds = [];
        tocLinks.forEach(function(a) { var id = a.getAttribute('href').replace('#',''); if(id) sectionIds.push(id); });
        function updateTocActive() {
            var scrollY = window.scrollY + 120;
            var current = null;
            for (var i = sectionIds.length-1; i >= 0; i--) {
                var el = document.getElementById(sectionIds[i]);
                if (el && el.offsetTop <= scrollY) { current = sectionIds[i]; break; }
            }
            tocLinks.forEach(function(a) {
                var href = a.getAttribute('href');
                a.classList.toggle('active', href && href.replace('#','') === current);
            });
        }
        window.addEventListener('scroll', updateTocActive);
        updateTocActive();

        function switchTab(group, index, total) {
            var panels = document.querySelectorAll('.tab-panel[data-tab-group=\"' + group + '\"]');
            panels.forEach(function(p) {
                p.classList.remove('active');
                p.classList.add('hidden');
            });
            var target = document.getElementById(group + '-tab-' + index);
            if (target) {
                target.classList.remove('hidden');
                target.classList.add('active');
            }
            // 更新按钮
            var containers = document.querySelectorAll('.tabs-container');
            var container = group === 'gen' ? containers[0] : containers[1];
            if (container) {
                var btns = container.querySelectorAll('.tab-btn');
                btns.forEach(function(btn, i) {
                    btn.classList.toggle('active', i === index);
                });
            }
            setTimeout(resizeAllPlots, 150);
        }
    </script>
    </body></html>"""
