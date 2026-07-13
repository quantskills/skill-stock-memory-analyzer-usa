#!/usr/bin/env python3
"""
存储芯片深度分析 - 主入口 (基于 panda_data)

用法:
    python analyze.py --ticker MU --username 86xxx --password xxx
    python analyze.py --ticker MU,WDC,STX --username 86xxx --password xxx
"""
import argparse
import io
import math
import os
import sys
from datetime import datetime


# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from utils.preflight import run_preflight


def load_runtime_dependencies() -> None:
    """Load optional dependencies only after the preflight has passed."""
    global pd
    global init_token, fetch_stock_data, fetch_fundamentals
    global fetch_institutional, fetch_analyst, fetch_insider_trades
    global load_industry_data, fetch_peer_comparison, fetch_benchmark_data
    global fetch_financial_events, fetch_ir_events
    global fetch_insider_transactions, fetch_shareholder_reports
    global fetch_recommendation, get_data_freshness, run_backtest, calc_technicals
    global analyze_inventory_cycle, analyze_memory_price_cycle
    global analyze_hbm_exposure, analyze_technology_position
    global analyze_capex_trend, generate_memory_assessment
    global analyze_hbm_gpu_demand, analyze_end_market_demand, build_report

    import pandas as pd
    from utils.fetcher import (
        init_token, fetch_stock_data, fetch_fundamentals,
        fetch_institutional, fetch_analyst, fetch_insider_trades,
        load_industry_data, fetch_peer_comparison, fetch_benchmark_data,
        fetch_financial_events, fetch_ir_events,
        fetch_insider_transactions, fetch_shareholder_reports,
        fetch_recommendation,
    )
    from utils.data_updater import get_data_freshness
    from utils.backtester import run_backtest
    from utils.indicators import calc_technicals
    from utils.memory_analyzer import (
        analyze_inventory_cycle, analyze_memory_price_cycle,
        analyze_hbm_exposure, analyze_technology_position,
        analyze_capex_trend, generate_memory_assessment,
        analyze_hbm_gpu_demand, analyze_end_market_demand,
    )
    from utils.report_builder import build_report


def _safe_float(val, default=None):
    """安全转换为 float，处理 None/nan"""
    if val is None:
        return default
    try:
        f = float(val)
        import math
        return f if not math.isnan(f) else default
    except (ValueError, TypeError):
        return default


def _fmt(val, suffix="", default="--"):
    """格式化数值，处理 None/nan"""
    v = _safe_float(val)
    if v is None:
        return default
    return f"{v}{suffix}"


def analyze_single(ticker: str, period: str, output_path: str = None,
                   username: str = None, password: str = None) -> str:
    """对单只股票执行完整分析流程"""
    ticker = ticker.strip().upper()

    # 认证
    if username and password:
        ok = init_token(username, password)
        if not ok:
            raise RuntimeError(
                "panda_data 登录失败，请检查账号密码。\n"
                f"   账号: 86{str(username).replace('86', '')}\n"
                "   如未注册，请先注册 panda_data 账号"
            )
    else:
        raise RuntimeError(
            "未提供 panda_data 账号信息。\n"
            "用法: python analyze.py --ticker MU --username 138xxxx --password xxx\n"
            "或设置环境变量: PANDA_DATA_USERNAME / PANDA_DATA_PASSWORD"
        )

    print(f"\n{'=' * 60}")
    print(f"  开始分析 {ticker}")
    print(f"{'=' * 60}")

    # 1. 行情数据
    print("[1/6] 获取行情数据...")
    price_df = fetch_stock_data(ticker, period)

    # 2. 基本面数据
    print("[2/6] 获取基本面数据...")
    fundamentals = fetch_fundamentals(ticker)
    info = fundamentals.get("info", {})
    company_name = info.get("shortName") or info.get("longName", ticker)
    print(f"       公司: {company_name}")

    # 3. 技术指标
    print("[3/6] 计算技术指标...")
    technicals = calc_technicals(price_df)

    # 机构 & 分析师
    try:
        institutional = fetch_institutional(ticker)
    except Exception:
        institutional = {}

    try:
        analyst = fetch_analyst(ticker)
        tp = analyst.get("target_price", {})
        info["targetMeanPrice"] = _safe_float(tp.get("mean"))
        info["targetHighPrice"] = _safe_float(tp.get("high"))
        info["targetLowPrice"] = _safe_float(tp.get("low"))
        info["lt_growth"] = analyst.get("lt_growth", {})
    except Exception:
        pass

    # 4. 行业数据（先检查新鲜度）
    freshness = get_data_freshness()
    stale_sections = [info["label"] for key, info in freshness.items()
                      if info["status"] in ("stale", "outdated", "missing", "unknown")]
    if stale_sections:
        print(f"  [WARNING] 以下行业数据可能已过时: {', '.join(stale_sections)}")
        print(f"            建议运行: python utils/data_updater.py freshness 查看详情")
        print(f"            或通过 WebSearch 获取最新数据后更新 industry_data.json")

    industry_data = load_industry_data()

    # 对标 (仅用 panda_data 支持的股票)
    memory_peers_cfg = industry_data.get("memory_peers", {})
    peer_tickers = []
    for category in ["dram_focused", "nand_focused", "hdd_hybrid"]:
        for p in memory_peers_cfg.get(category, []):
            pt = p.get("ticker", "")
            if pt.upper() != ticker and not pt.startswith("000"):
                peer_tickers.append(pt)
    peer_tickers = peer_tickers[:5]

    print(f"[4/6] 获取对标数据 ({', '.join(peer_tickers)})...")
    peers = fetch_peer_comparison(peer_tickers)

    # 公司事件
    fin_events = fetch_financial_events(ticker)
    ir_events = fetch_ir_events(ticker)
    insider_trades = fetch_insider_transactions(ticker)
    shareholder_reports = fetch_shareholder_reports(ticker)
    recommendation = fetch_recommendation(ticker)
    print(f"       财务事件: {len(fin_events)} 条, IR活动: {len(ir_events)} 条, 内部人: {len(insider_trades)} 人, 股东: {len(shareholder_reports)} 条, 评级: {recommendation.get('total',0)} 分析师")

    # ---- 从价格数据填充 info ----
    current_price = float(price_df["Close"].iloc[-1])
    info["currentPrice"] = current_price
    info["regularMarketPrice"] = current_price

    # 52周高低
    year_ago = price_df.index[-1] - pd.Timedelta(days=365)
    year_data = price_df[price_df.index >= year_ago]
    if not year_data.empty:
        info["fiftyTwoWeekHigh"] = float(year_data["High"].max())
        info["fiftyTwoWeekLow"] = float(year_data["Low"].min())

    # ---- 从 pv_metric 补充估值数据 ----
    pv = fundamentals.get("pv_metric", {})
    if pv:
        info["marketCap"] = pv.get("market_cap")
        info["beta"] = pv.get("beta_5y")
        info["fiftyTwoWeekHigh"] = pv.get("high_52w") or info.get("fiftyTwoWeekHigh")
        info["fiftyTwoWeekLow"] = pv.get("low_52w") or info.get("fiftyTwoWeekLow")
        if pv.get("close_price"):
            info["currentPrice"] = pv["close_price"]
            info["regularMarketPrice"] = pv["close_price"]

    # ---- 从 mktfin_metric 补充估值比率 ----
    mktfin = fundamentals.get("mktfin_metric", {})
    if mktfin:
        info["trailingPE"] = mktfin.get("pe")
        info["priceToBook"] = mktfin.get("pb")
        info["priceToSales"] = mktfin.get("ps")
        info["pegRatio"] = mktfin.get("peg")
        info["enterpriseToEbitda"] = mktfin.get("ev_ebitda")

    # PE 兜底: 如果 mktfin_metric 无 PE (如新上市公司)，用市值/TTM净利计算
    if not info.get("trailingPE"):
        mcap = info.get("marketCap")
        ttm_ni = info.get("ttmNetIncome")
        if mcap and ttm_ni and ttm_ni > 0:
            info["trailingPE"] = round(mcap / ttm_ni, 1)

    # ---- 从 get_fina_ex 财务数据计算指标 ----
    fin = fundamentals.get("financials", {})
    if fin:
        # 按 fy_period 排序取最新季度
        sorted_periods = sorted(fin.keys())
        latest_q = fin[sorted_periods[-1]] if sorted_periods else {}

        rev = latest_q.get("revenue")
        ni = latest_q.get("net_income")
        gp = latest_q.get("gross_profit")
        ebitda = latest_q.get("ebitda")
        equity = latest_q.get("shareholders_equity")
        assets = latest_q.get("total_assets")
        liabilities = latest_q.get("total_liabilities")
        cash_val = latest_q.get("cash")

        # 计算 TTM (最近4个季度汇总)
        ttm_rev = 0; ttm_ni = 0; ttm_gp = 0
        for p in sorted_periods[-4:]:
            q = fin[p]
            ttm_rev += abs(q.get("revenue") or 0)
            ttm_ni += abs(q.get("net_income") or 0)
            ttm_gp += abs(q.get("gross_profit") or 0)

        if rev and rev != 0:
            if ni and ni != 0:
                info["profitMargins"] = round(ni / rev * 100, 2)
            if gp and gp != 0:
                info["grossMargins"] = round(gp / rev * 100, 2)

        if ttm_rev > 0:
            if ttm_ni > 0:
                info["profitMarginsTTM"] = round(ttm_ni / ttm_rev * 100, 2)
            if ttm_gp > 0:
                info["grossMarginsTTM"] = round(ttm_gp / ttm_rev * 100, 2)

        if equity and equity != 0 and ttm_ni > 0:
            info["returnOnEquity"] = round(ttm_ni / equity * 100, 2)

        if equity and liabilities:
            info["debtToEquity"] = round(liabilities / equity, 4) if equity != 0 else None

        # PE/PB/PS 需要市值和股数，panda_data 不提供，通过 revenue/equity 比率展示财务面
        # 用最新季度年化来近似
        info["latestRevenue"] = rev
        info["latestNetIncome"] = ni
        info["ttmRevenue"] = ttm_rev
        info["ttmNetIncome"] = ttm_ni
        info["totalAssets"] = assets

    # 5. 存储行业专属分析
    print("[5/6] 执行存储行业专属分析...")

    # 从 get_fina_ex 财务数据构造实时趋势
    fin = fundamentals.get("financials", {})
    periods = sorted(fin.keys())
    gross_margin_trend = []
    inv_days_trend = []
    for p in periods[-8:]:  # 取最近8个季度
        q = fin[p]
        rev = q.get("revenue") or 0
        gp = q.get("gross_profit") or 0
        inv = q.get("inventory") or 0
        cogs = q.get("cogs") or 0
        if rev and rev != 0:
            gross_margin_trend.append({
                "date": p,
                "gross_margin": round(gp / rev * 100, 1)
            })
        # 库存周转天数 = 库存 / 单季COGS * 91.25 (约一个季度天数)
        if inv and cogs and cogs != 0:
            inv_days_trend.append({
                "date": p,
                "inventory_days": round(inv / abs(cogs) * 91.25, 1)
            })

    if inv_days_trend:
        print(f"       库存数据: {len(inv_days_trend)}个季度 (最新={inv_days_trend[-1]['date']}, {inv_days_trend[-1]['inventory_days']}天)")
    else:
        print("       库存数据: 无 (inventory/COGS 字段不可用)")

    inv_analysis = analyze_inventory_cycle(inv_days_trend)
    print(f"       库存周期: {inv_analysis.get('cycle_phase', 'N/A')}")

    price_cycle = analyze_memory_price_cycle(industry_data, gross_margin_trend)
    print(f"       价格周期: {price_cycle.get('cycle_phase', 'N/A')}")

    capex_analysis = analyze_capex_trend(fundamentals, industry_data, ticker)
    print(f"       CapEx: {capex_analysis.get('expansion_phase', 'N/A')}")

    # 新增: HBM GPU需求量化模型
    print("[5b] HBM GPU需求量化...")
    hbm_demand = analyze_hbm_gpu_demand(industry_data)
    if hbm_demand.get("available"):
        gap_2026 = hbm_demand.get("yearly_gaps", {}).get("2026", {})
        print(f"       HBM供需: {gap_2026.get('status', 'N/A')} (需求{gap_2026.get('demand_m_gb', 0):.0f}M GB vs 供给{gap_2026.get('supply_m_gb', 0):.0f}M GB, 缺口{gap_2026.get('gap_ratio_pct', 0):.1f}%)")
    else:
        print(f"       HBM需求: 数据不可用")

    # 公司 HBM 暴露度 (公司差异化)
    hbm_exposure = analyze_hbm_exposure(fundamentals, industry_data)

    # 技术节点路线图
    tech_position = analyze_technology_position(info, industry_data)

    # 下游需求终端拆分
    print("[5c] 下游需求终端拆分...")
    end_market = analyze_end_market_demand(industry_data)
    if end_market.get("available"):
        dram_g = end_market.get("dram", {}).get("weighted_growth_pct", 0)
        nand_g = end_market.get("nand", {}).get("weighted_growth_pct", 0)
        hbm_g = end_market.get("hbm", {}).get("weighted_growth_pct", 0)
        print(f"       下游增速: DRAM {dram_g:+.1f}% | NAND {nand_g:+.1f}% | HBM {hbm_g:+.1f}%")
    else:
        print(f"       下游需求: 数据不可用")

    # 综合评分 (所有模块分析完成后)
    memory_assessment = generate_memory_assessment(
        inv_analysis, price_cycle, capex_analysis,
        hbm_demand, end_market, tech_position,
        industry_data, ticker
    )
    print(f"       综合评分: {memory_assessment.get('composite_score')}/100 ({memory_assessment.get('rating')})")

    # 6. 回测（可选）
    backtest_result = None
    backtest_result = run_backtest(ticker, price_df, fin, industry_data)

    # 7. 生成报告 (使用数据最新日期，而非当天日期)
    print("[6/6] 生成 HTML 报告...")
    data_latest_date = price_df.index[-1].strftime("%Y-%m-%d") if hasattr(price_df.index[-1], 'strftime') else str(price_df.index[-1])[:10]
    gen_date = datetime.now().strftime("%Y-%m-%d")
    report_date = f"{data_latest_date} (生成于 {gen_date})"
    html_content = build_report(
        ticker=ticker,
        company_name=company_name,
        report_date=report_date,
        price_df=price_df,
        fundamentals=fundamentals,
        technicals=technicals,
        peers=peers,
        inv_analysis=inv_analysis,
        price_cycle=price_cycle,
        capex_analysis=capex_analysis,
        memory_assessment=memory_assessment,
        institutional=institutional,
        fin_events=fin_events,
        ir_events=ir_events,
        insider_trades=insider_trades,
        shareholder_reports=shareholder_reports,
        recommendation=recommendation,
        hbm_demand=hbm_demand,
        end_market=end_market,
        tech_position=tech_position,
        data_freshness=freshness,
        hbm_exposure=hbm_exposure,
        backtest_result=backtest_result,
    )

    # 保存
    output_dir = os.path.join(ROOT_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)

    if output_path:
        filepath = output_path
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ticker}_analysis_{ts}.html"
        filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n[OK] 报告已生成: {filepath}")
    print(f"   文件大小: {os.path.getsize(filepath) / 1024:.1f} KB")
    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="存储芯片深度分析工具 (基于 panda_data)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python analyze.py --check-env
  python analyze.py --install-deps --check-env
  # 推荐：先设置 PANDA_DATA_USERNAME / PANDA_DATA_PASSWORD
  python analyze.py --ticker MU
  python analyze.py --ticker MU --username 86xxx --password xxx
  python analyze.py --ticker MU,WDC,STX --username 86xxx --password xxx
  python analyze.py --ticker MU -u 86xxx -p xxx --period 5y
        """
    )
    parser.add_argument("--ticker", "-t", type=str, default=None,
                        help="股票代码，多个用逗号分隔 (如 MU,WDC,STX)")
    parser.add_argument("--username", "-u", type=str, default=None,
                        help="panda_data 账号 (86手机号)")
    parser.add_argument("--password", "-p", type=str, default=None,
                        help="panda_data 密码")
    parser.add_argument("--period", type=str, default="5y",
                        help="历史数据时间跨度 (1y/2y/5y/10y/max)，默认5y")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="自定义输出路径")
    parser.add_argument("--check-env", action="store_true",
                        help="检查 panda_data 账号、Python 依赖与网络要求后退出")
    parser.add_argument("--install-deps", action="store_true",
                        help="显式同意通过 requirements.txt 安装缺失依赖")

    args = parser.parse_args()

    # 也可以从环境变量读取
    username = args.username or os.environ.get("PANDA_DATA_USERNAME")
    password = args.password or os.environ.get("PANDA_DATA_PASSWORD")

    preflight_ok = run_preflight(
        username,
        password,
        install_deps=args.install_deps,
        check_only=args.check_env,
    )
    if args.check_env:
        raise SystemExit(0 if preflight_ok else 1)
    if not preflight_ok:
        raise SystemExit(1)
    if not args.ticker:
        parser.error("--ticker is required unless --check-env is used")

    load_runtime_dependencies()

    tickers = [t.strip() for t in args.ticker.split(",")]

    results = []
    for t in tickers:
        try:
            filepath = analyze_single(t, args.period, args.output if len(tickers) == 1 else None,
                                       username, password)
            results.append((t, filepath, "success"))
        except Exception as e:
            print(f"\n[ERROR] 分析 {t} 时出错: {e}")
            import traceback
            traceback.print_exc()
            results.append((t, None, str(e)))

    # 总结
    print(f"\n{'=' * 60}")
    print(f"  分析完成")
    print(f"{'=' * 60}")
    for t, path, status in results:
        if status == "success":
            print(f"  [OK] {t}: {path}")
        else:
            print(f"  [ERROR] {t}: {status}")


if __name__ == "__main__":
    main()
