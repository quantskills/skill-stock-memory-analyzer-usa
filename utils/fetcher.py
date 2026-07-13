"""
数据获取模块 - 基于 panda_data

panda_data 提供以下美股数据:
- get_us_daily: 日线 OHLCV
- get_us_detail: 公司基本信息
- get_stock_operating_metric: 标准化营运指标 (按财年)
- get_stock_sector_median: 行业中位统计 (估值对比)
- get_stock_ncycl_estimate: 非周期一致预期 (目标价/长期增长)
- get_stock_recommendation_consensus: 买卖评级共识
- get_stock_top10_investors: 前十大投资者
- get_stock_insider_transaction: 内部人交易
"""
import json
import os
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ============ 认证 ============

def init_token(username: str, password: str) -> bool:
    """
    初始化 panda_data 认证 token

    - username 自动补全 86 前缀
    - 验证连通性并输出结果

    Returns:
        True if connected successfully
    """
    try:
        import panda_data
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "缺少 panda_data 客户端。请在 skill 根目录运行："
            "python -m pip install -r requirements.txt"
        ) from exc

    # 自动补全 86 前缀
    username = str(username).strip()
    if not username.startswith("86"):
        username = "86" + username

    masked_username = f"{username[:2]}***{username[-4:]}" if len(username) > 6 else "***"
    print(f"  [panda_data] 正在登录 (账号: {masked_username})...")

    try:
        panda_data.init_token(username=username, password=password)
    except Exception as e:
        error_text = str(e)
        print(f"  [panda_data] 登录失败: {error_text}")
        if "10013" in error_text or "access socket" in error_text.lower():
            print("  [panda_data] 提示：当前环境阻止网络连接。请授予 Python 网络权限后重试。")
        elif "401" in error_text or "403" in error_text:
            print("  [panda_data] 提示：请确认 panda_data 用户名、密码和账号权限。")
        return False

    # 验证连通性：尝试获取美股交易日历
    try:
        trade_cal = panda_data.get_trade_cal(
            exchange="US",
            is_trading_day=1,
        )
        if trade_cal is not None and not trade_cal.empty:
            latest_date = trade_cal.iloc[0].get("nature_date", "未知")
            print(f"  [panda_data] 连接成功! 美股最新交易日: {latest_date}")
            return True
        else:
            print("  [panda_data] 连接成功，但未获取到交易日信息")
            return True
    except Exception as e:
        # 交易日历接口可能不可用，但不影响数据获取
        print(f"  [panda_data] 连接成功 (交易日历接口: {e})")
        return True


# ============ 历史行情 ============

def fetch_stock_data(ticker: str, period: str = "5y") -> pd.DataFrame:
    """
    获取美股历史日线数据

    Args:
        ticker: 股票代码 (如 MU, AAPL)
        period: 1y/2y/5y/10y/max

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
    """
    import panda_data

    end_date = datetime.now().strftime("%Y%m%d")

    period_days = {"1y": 365, "2y": 730, "5y": 1825, "10y": 3650, "max": 7300}
    days = period_days.get(period, 1825)
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

    print(f"  [panda_data] 获取 {ticker} 日线数据 ({start_date} ~ {end_date})...")

    result = panda_data.get_us_daily(
        symbol=[ticker],
        start_date=start_date,
        end_date=end_date,
        fields=[]
    )

    if result is None or result.empty:
        raise ValueError(f"无法获取 {ticker} 的历史数据，请检查代码和登录状态")

    # 标准化列名
    df = result.copy()
    col_map = {
        "date": "Date", "open": "Open", "high": "High",
        "low": "Low", "close": "Close", "volume": "Volume"
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d", errors="coerce")
    df = df.set_index("Date")
    df = df.sort_index()

    # 确保必要的列
    for col in ["Open", "High", "Low", "Close"]:
        if col not in df.columns:
            df[col] = df.get("Close", 0)
    if "Volume" not in df.columns:
        df["Volume"] = 0

    # 转换为数值
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])

    print(f"  [panda_data] 获取到 {len(df)} 条日线数据")
    return df


# ============ 公司信息 & 基本面 ============

def fetch_financials(ticker: str) -> dict:
    """
    通过 get_fina_ex 获取完整季度财务数据

    Returns:
        {fy_period: {field: value}, ...}  按季度排列
    """
    import panda_data

    now = datetime.now()
    end_q = f"{now.year}q{(now.month - 1) // 3 + 1}"
    # API 限制最多5年(20个季度)，所以 start 往回推4年
    start_q = f"{now.year - 4}q1"

    print(f"  [panda_data] 获取 {ticker} 财务数据 ({start_q}~{end_q})...")

    df = panda_data.get_fina_ex(
        symbol=ticker,
        start_quarter=start_q,
        end_quarter=end_q,
        is_latest=True,
        fields=[
            "fy_period", "date",
            # 利润表
            "is_revenue_business_total",
            "is_gross_profit",
            "is_ebitda",
            "is_ebit",
            "is_net_income",
            "is_cost_revenues_total",
            "is_operating_expenses",
            "is_diluted_income_excl_exord",
            # 资产负债表
            "bs_total_assets",
            "bs_total_liabilities",
            "bs_shareholders_equity_parent",
            "bs_cash_and_cash_equivalents",
            "bs_total_current_assets",
            "bs_inventories_total",
            # 现金流量表
            "cfs_capex_total",
            "cfs_capex_net",
            "cfs_ppe_purchased",
        ]
    )

    if df is None or df.empty:
        print(f"  [panda_data] {ticker} 无财务数据")
        return {}

    # 按 fy_period 组织
    quarters = {}
    for _, row in df.iterrows():
        r = row.to_dict()
        period = r.get("fy_period", "")
        quarters[period] = {
            "report_date": str(r.get("date", "")),
            "revenue": _safe_val(r.get("is_revenue_business_total")),
            "gross_profit": _safe_val(r.get("is_gross_profit")),
            "ebitda": _safe_val(r.get("is_ebitda")),
            "ebit": _safe_val(r.get("is_ebit")),
            "net_income": _safe_val(r.get("is_net_income")),
            "cogs": _safe_val(r.get("is_cost_revenues_total")),
            "op_expenses": _safe_val(r.get("is_operating_expenses")),
            "total_assets": _safe_val(r.get("bs_total_assets")),
            "total_liabilities": _safe_val(r.get("bs_total_liabilities")),
            "shareholders_equity": _safe_val(r.get("bs_shareholders_equity_parent")),
            "cash": _safe_val(r.get("bs_cash_and_cash_equivalents")),
            "current_assets": _safe_val(r.get("bs_total_current_assets")),
            "inventory": _safe_val(r.get("bs_inventories_total")),
            "capex": _safe_val(r.get("cfs_capex_total")),
            "eps_diluted": _safe_val(r.get("is_diluted_income_excl_exord")),
        }

    print(f"  [panda_data] 获取到 {len(quarters)} 个季度财务数据")
    return quarters


def _safe_val(v):
    """安全转换值为 float，NaN 返回 None"""
    import math
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    return float(v)


def fetch_pv_metric(ticker: str) -> dict:
    """获取估值与市场数据 (市值、Beta、52周高低等)"""
    import panda_data
    try:
        pv = panda_data.get_stock_pv_metric(symbol=[ticker], fields=[])
        if pv is not None and not pv.empty:
            r = pv.iloc[0].to_dict()
            return {
                "market_cap": _safe_val(r.get("pv_market_cap")),
                "beta_5y": _safe_val(r.get("pv_beta_5y")),
                "close_price": _safe_val(r.get("pv_close")),
                "close_date": str(r.get("pv_close_date", "")),
                "high_52w": _safe_val(r.get("pv_high_52w")),
                "low_52w": _safe_val(r.get("pv_low_52w")),
                "return_ytd": _safe_val(r.get("pv_return_ytd")),
                "return_1d": _safe_val(r.get("pv_return_1d")),
                "return_5d": _safe_val(r.get("pv_return_5d")),
                "return_mtd": _safe_val(r.get("pv_return_mtd")),
                "return_13w": _safe_val(r.get("pv_return_13w")),
                "return_26w": _safe_val(r.get("pv_return_26w")),
                "return_52w": _safe_val(r.get("pv_return_52w")),
                "avg_vol_90d": _safe_val(r.get("pv_avg_vol_90d")),
                "avg_val_3m": _safe_val(r.get("pv_avg_val_3m")),
            }
    except Exception as e:
        print(f"  [panda_data] PV指标获取失败: {e}")
    return {}


def fetch_mktfin_metric(ticker: str) -> dict:
    """获取市场估值指标 (PE/PB/PS/PEG/EV_EBITDA等)"""
    import panda_data
    try:
        mkt = panda_data.get_stock_mktfin_metric(symbol=[ticker], fields=[])
        if mkt is not None and not mkt.empty:
            # 取最新一条有效数据 (按 date 排序，PE不为NaN)
            mkt = mkt.sort_values("date", ascending=True)
            pe_col = "curr_pe_dil_excl"
            if pe_col in mkt.columns:
                valid = mkt[mkt[pe_col].notna()]
                r = valid.iloc[-1].to_dict() if not valid.empty else mkt.iloc[-1].to_dict()
            else:
                r = mkt.iloc[-1].to_dict()

            return {
                "data_date": str(r.get("date", "")),
                "pe": _safe_val(r.get("curr_pe_dil_excl")),
                "pe_ttm": _safe_val(r.get("curr_pe_dil_excl_ttm")),
                "pb": _safe_val(r.get("curr_pb_lfy")),
                "ps": _safe_val(r.get("curr_price_to_rev_pershr")),
                "peg": _safe_val(r.get("curr_peg")),
                "ev_ebitda": _safe_val(r.get("curr_ev_to_ebitda")),
                "price_to_fcf": _safe_val(r.get("curr_price_to_fcf_pershr")),
                "div_yield": _safe_val(r.get("curr_div_yld_issue_ratio")),
                "earn_yield": _safe_val(r.get("curr_earn_yld_dil_excl_ratio")),
            }
    except Exception as e:
        print(f"  [panda_data] 市场估值获取失败: {e}")
    return {}


def fetch_fundamentals(ticker: str) -> dict:
    """
    获取公司基本面和财务数据

    Returns:
        dict with: info, financials (quarterly), pv_metric, mktfin_metric
    """
    import panda_data

    # 1. 公司基本信息
    print(f"  [panda_data] 获取 {ticker} 基本信息...")
    detail = panda_data.get_us_detail(symbol=[ticker], fields=[], status=None)
    info = _parse_us_detail(detail, ticker)

    # 2. 季度财务数据
    financials = fetch_financials(ticker)

    # 3. 估值与市场数据
    print(f"  [panda_data] 获取 {ticker} 估值指标...")
    pv_metric = fetch_pv_metric(ticker)
    mktfin_metric = fetch_mktfin_metric(ticker)

    return {
        "info": info,
        "financials": financials,
        "pv_metric": pv_metric,
        "mktfin_metric": mktfin_metric,
        "data_source": "panda_data",
    }


def _parse_us_detail(detail: pd.DataFrame, ticker: str) -> dict:
    """解析 get_us_detail 返回数据为 info dict"""
    if detail is None or detail.empty:
        return {"symbol": ticker}

    row = detail.iloc[0].to_dict()
    return {
        "symbol": ticker,
        "shortName": row.get("name", ticker),
        "longName": row.get("name", ticker),
        "sector": row.get("economic_sector", ""),
        "industry": row.get("industry_group", ""),
        "business_sector": row.get("business_sector", ""),
        "exchange": row.get("exchange_name", ""),
        "website": row.get("website", ""),
        "country": row.get("office_country", ""),
        "listed_date": row.get("listed_date", ""),
        "isin": row.get("isin_code", ""),
    }


def _parse_operating_metrics(df: pd.DataFrame, ticker: str) -> dict:
    """
    解析 get_stock_operating_metric 的 item-based 格式
    返回: {financial_year: {item_name: item_num}}
    """
    if df is None or df.empty:
        return {}

    # 只取 "Original To Original" 数据避免重复
    df = df[df.get("report_type", "") == "Original To Original"] if "report_type" in df.columns else df
    df = df[df.get("is_final", 1) == 1] if "is_final" in df.columns else df

    result = {}
    for _, row in df.iterrows():
        year = row.get("financial_year", "")
        item = row.get("item_name", "")
        value = row.get("item_num", np.nan)

        if not year or pd.isna(value):
            continue

        year_str = str(int(year)) if isinstance(year, (int, float)) else str(year)
        if year_str not in result:
            result[year_str] = {}

        # 标准化指标名
        item_clean = _clean_item_name(str(item))
        result[year_str][item_clean] = float(value)

    return result


def _clean_item_name(name: str) -> str:
    """映射 panda_data 指标名为统一格式"""
    mapping = {
        "Operating Revenue": "Total Revenue",
        "Total Revenue": "Total Revenue",
        "Gross Profit": "Gross Profit",
        "Operating Income": "Operating Income",
        "Net Income": "Net Income",
        "EBITDA": "EBITDA",
        "Diluted EPS": "EPS",
        "Basic EPS": "EPS_Basic",
        "Total Assets": "Total Assets",
        "Total Liabilities": "Total Liabilities",
        "Total Equity": "Total Equity",
        "Cash & Equivalents": "Cash",
        "Total Debt": "Total Debt",
        "Inventory": "Inventory",
        "Operating Cash Flow": "Operating CF",
        "Capital Expenditure": "Capex",
        "Free Cash Flow": "Free Cash Flow",
        "Dividends Paid": "Dividends Paid",
        "Revenue Growth": "Revenue Growth",
    }
    # 先精确匹配，再模糊匹配
    for key, val in mapping.items():
        if key.lower() in name.lower():
            return val
    return name


def _parse_sector_median(df: pd.DataFrame, ticker: str) -> dict:
    """解析行业中位统计数据，取最新非 NaN 行"""
    if df is None or df.empty:
        return {}

    import math

    # 按 date 排序，取 PE 不为 NaN 的最新行
    df_sorted = df.sort_values("date", ascending=True)
    pe_col = "imed_pe_excl_exord_ttm"
    if pe_col in df_sorted.columns:
        valid = df_sorted[df_sorted[pe_col].apply(lambda x: not (isinstance(x, float) and math.isnan(x)))]
        if not valid.empty:
            row = valid.iloc[-1].to_dict()
        else:
            row = df_sorted.iloc[-1].to_dict()
    else:
        row = df_sorted.iloc[-1].to_dict()

    def _val(key):
        v = row.get(key)
        if v is None:
            return None
        if isinstance(v, float) and math.isnan(v):
            return None
        return v

    return {
        "industry_name": row.get("industry_name", ""),
        "data_date": str(row.get("date", "")),
        "pe_ttm": _val("imed_pe_excl_exord_ttm"),
        "pb_ttm": _val("imed_pb_ttm"),
        "ps_ttm": _val("imed_price_to_rev_per_shr_ttm"),
        "roe": _val("imed_roe_avg_common_ttm"),
        "roic": _val("imed_roic_ratio_ttm"),
        "gross_margin": _val("imed_gross_margin_ratio_fye_mid"),
        "net_margin": _val("imed_net_margin_ratio_fye_mid"),
        "op_margin": _val("imed_op_margin_ratio_fye_mid"),
        "ebitda_margin": _val("imed_ebitda_margin_ratio_fye_mid"),
        "debt_to_equity": _val("imed_debt_to_equity_ratio_fye_mid"),
        "current_ratio": _val("imed_curr_ratio_fye_mid"),
        "div_yield": _val("imed_gross_div_yield_ttm"),
        "operating_cf": _val("imed_cfo_abs_fye_mid"),
    }


# ============ 分析师 & 一致预期 ============

def fetch_analyst(ticker: str) -> dict:
    """获取分析师一致预期数据"""
    import panda_data

    result = {}

    try:
        # 非周期一致预期 (目标价 TP, 长期增长 LTGROWTH)
        est = panda_data.get_stock_ncycl_estimate(symbol=[ticker], fields=[])
        if est is not None and not est.empty:
            tp_row = est[est.get("indicator", "") == "TP"]
            lg_row = est[est.get("indicator", "") == "LTGROWTH"]

            if not tp_row.empty:
                r = tp_row.iloc[0].to_dict()
                result["target_price"] = {
                    "mean": r.get("mean"), "median": r.get("median"),
                    "high": r.get("high"), "low": r.get("low"),
                    "std": r.get("std"), "estimates_num": r.get("estimates_num"),
                }
            if not lg_row.empty:
                r = lg_row.iloc[0].to_dict()
                result["lt_growth"] = {
                    "mean": r.get("mean"), "median": r.get("median"),
                    "high": r.get("high"), "low": r.get("low"),
                }
    except Exception as e:
        print(f"  [panda_data] 一致预期获取失败: {e}")

    # 评级共识 (panda_data 仅支持港股，美股跳过)
    # 目标价 (TP) 已通过 get_stock_ncycl_estimate 获取

    return result


# ============ 机构 & 内部人 ============

def fetch_institutional(ticker: str) -> dict:
    """获取前十大投资者持仓数据 (使用 get_stock_investor_leaderboard)"""
    import panda_data

    try:
        top10 = panda_data.get_stock_investor_leaderboard(
            symbol=ticker,
            fields=[],
            max_rank=10
        )
        if top10 is not None and not top10.empty:
            investors = []
            for _, row in top10.iterrows():
                r = row.to_dict()
                investors.append({
                    "name": r.get("investor_name", ""),
                    "type": r.get("investor_type", ""),
                    "shares": r.get("sharehold"),
                    "outstanding_ratio": r.get("investor_outstanding_ratio"),
                    "change": r.get("sharehold_change"),
                    "date": r.get("info_date", ""),
                    "rank": r.get("rank"),
                })
            print(f"  [panda_data] 机构持仓获取成功 ({len(investors)} 条)")
            return {"top10_investors": investors}
    except Exception as e:
        print(f"  [panda_data] 机构持仓获取失败: {e}")

    return {}


def fetch_insider_trades(ticker: str) -> dict:
    """获取内部人交易数据"""
    import panda_data

    try:
        trades = panda_data.get_stock_insider_transaction(
            symbol=[ticker],
            fields=[]
        )
        if trades is not None and not trades.empty:
            return {
                "insider_transactions": trades.head(30).to_dict(orient="records")
            }
    except Exception as e:
        print(f"  [panda_data] 内部人交易获取失败: {e}")

    return {}


# ============ 对标 & 行业 ============

def fetch_peer_comparison(tickers: list) -> dict:
    """
    获取对标公司的关键指标 (使用 pv_metric + mktfin_metric)
    """
    import panda_data
    import math

    result = {}
    for t in tickers:
        try:
            entry = {"name": t}
            # 公司基本信息
            try:
                detail = panda_data.get_us_detail(symbol=[t], fields=[], status=None)
                if detail is not None and not detail.empty:
                    entry["name"] = detail.iloc[0].get("name", t)
            except Exception:
                pass

            # PV 指标 (市值、Beta)
            try:
                pv = panda_data.get_stock_pv_metric(symbol=[t], fields=[])
                if pv is not None and not pv.empty:
                    r = pv.iloc[0]
                    entry["market_cap"] = _safe_val(r.get("pv_market_cap"))
                    entry["beta"] = _safe_val(r.get("pv_beta_5y"))
            except Exception:
                pass

            # 估值比率 (PE/PB/PS/PEG)
            try:
                mkt = panda_data.get_stock_mktfin_metric(symbol=[t], fields=[])
                if mkt is not None and not mkt.empty:
                    mkt = mkt.sort_values("date", ascending=True)
                    pe_col = "curr_pe_dil_excl"
                    if pe_col in mkt.columns:
                        valid = mkt[mkt[pe_col].notna()]
                        r = valid.iloc[-1].to_dict() if not valid.empty else mkt.iloc[-1].to_dict()
                    else:
                        r = mkt.iloc[-1].to_dict()
                    entry["pe_ttm"] = _safe_val(r.get("curr_pe_dil_excl"))
                    entry["pb"] = _safe_val(r.get("curr_pb_lfy"))
                    entry["ps"] = _safe_val(r.get("curr_price_to_rev_pershr"))
                    entry["peg"] = _safe_val(r.get("curr_peg"))
            except Exception:
                pass

            result[t] = entry
        except Exception as e:
            result[t] = {"error": str(e), "name": t}

    return result


# ============ 基准指数 ============

def fetch_benchmark_data(benchmark_ticker: str = "SOX", period: str = "5y") -> Optional[pd.DataFrame]:
    """获取基准指数数据 - panda_data 不支持 ETF/指数"""
    print(f"  [panda_data] 基准指数跳过 (panda_data 不支持指数/ETF)")
    return None


def fetch_recommendation(ticker: str) -> dict:
    """获取分析师买卖建议一致预期"""
    import panda_data
    try:
        rec = panda_data.get_stock_recommendation_estimate(symbol=[ticker], fields=[])
        if rec is not None and not rec.empty:
            r = rec.iloc[0].to_dict()
            return {
                "mean": _safe_val(r.get("mean")),
                "strong_buy_num": _safe_val(r.get("strong_buy_num")),
                "buy_num": _safe_val(r.get("buy_num")),
                "hold": _safe_val(r.get("hold")),
                "sell_num": _safe_val(r.get("sell_num")),
                "strong_sell_num": _safe_val(r.get("strong_sell_num")),
                "total": _safe_val(r.get("recommendations_num")),
            }
    except Exception as e:
        print(f"  [panda_data] 评级获取失败: {e}")
    return {}


# ============ 内部人交易 ============

def fetch_insider_transactions(ticker: str) -> list:
    """获取内部人交易 (聚合去重，保留大额交易)"""
    import panda_data
    import math
    try:
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=730)).strftime("%Y%m%d")
        it = panda_data.get_stock_insider_transaction(
            symbol=[ticker], fields=[], start_date=start, end_date=end
        )
        if it is None or it.empty:
            return []

        # 按人聚合，排除小额的税/奖励类交易
        by_person = {}
        for _, r in it.iterrows():
            name = str(r.get("investor_name", ""))
            if not name or name == "nan":
                continue
            shares = _safe_val(r.get("reported_trade_shares"))
            price = _safe_val(r.get("transaction_price"))
            tx_type = str(r.get("transaction_type", ""))
            tx_date = str(r.get("transaction_date", ""))
            filing = str(r.get("filing_type", ""))

            if shares is None:
                continue

            # 归类: 卖出(负股数), 买入/奖励(正股数/价格0), 忽略(税缴)
            is_tax = "tax" in tx_type.lower() or "withholding" in tx_type.lower()
            is_grant = price is None or price == 0
            is_sell = shares < 0

            if is_tax:
                continue  # 跳过税缴类小交易

            value = abs(shares) * (price or 0)

            if name not in by_person:
                by_person[name] = {"name": name, "total_buy_shares": 0, "total_buy_value": 0,
                                   "total_sell_shares": 0, "total_sell_value": 0,
                                   "last_date": "", "filing": filing}
            p = by_person[name]
            if is_sell:
                p["total_sell_shares"] += abs(shares)
                p["total_sell_value"] += value
            else:
                p["total_buy_shares"] += shares
                p["total_buy_value"] += value
            if tx_date > p["last_date"]:
                p["last_date"] = tx_date
                p["filing"] = filing

        # 过滤: 只保留总价值 > $100K 的
        result = []
        for name, p in by_person.items():
            total_val = p["total_sell_value"] + p["total_buy_value"]
            if total_val > 100000:
                p["total_buy_value"] = round(p["total_buy_value"])
                p["total_sell_value"] = round(p["total_sell_value"])
                result.append(p)

        return sorted(result, key=lambda x: x["total_sell_value"] + x["total_buy_value"], reverse=True)
    except Exception as e:
        print(f"  [panda_data] 内部人交易获取失败: {e}")
        return []


def fetch_shareholder_reports(ticker: str) -> list:
    """获取股东持股报告 (大额变动)"""
    import panda_data
    try:
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=730)).strftime("%Y%m%d")
        sr = panda_data.get_stock_shareholder_report(
            symbol=[ticker], fields=[], start_date=start, end_date=end
        )
        if sr is None or sr.empty:
            return []

        reports = []
        for _, r in sr.iterrows():
            shares = _safe_val(r.get("sharehold"))
            ratio = _safe_val(r.get("outstanding_ratio"))
            change = _safe_val(r.get("sharehold_change"))
            if shares is None:
                continue
            # 保留有持股变动信息的记录 (>0.5%持仓 或 >50万股变动 或 >0.5%变动)
            significant = False
            if ratio and ratio > 0.005:
                significant = True
            if change:
                # change 可能是股数(如 5000000)也可能是比例(如 0.05)
                if abs(change) > 5e5 or (0 < abs(change) <= 1 and abs(change) > 0.005):
                    significant = True
            if significant:
                reports.append({
                    "date": str(r.get("holding_date", r.get("info_date", ""))),
                    "name": str(r.get("investor_name", "")),
                    "shares": shares,
                    "ratio": ratio,
                    "change": change,
                    "value": _safe_val(r.get("sharehold_value")),
                })
        return sorted(reports, key=lambda x: x.get("date", ""), reverse=True)[:20]
    except Exception as e:
        print(f"  [panda_data] 股东报告获取失败: {e}")
        return []


# ============ 公司事件 ============

def fetch_financial_events(ticker: str) -> list:
    """获取财务披露事件 (财报发布、电话会议等)"""
    import panda_data
    import math
    try:
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=730)).strftime("%Y%m%d")
        fa = panda_data.get_stock_financial_activity(
            symbol=[ticker],
            fields=[],
            start_date=start,
            end_date=end
        )
        if fa is not None and not fa.empty:
            events = []
            for _, r in fa.iterrows():
                fq = r.get("fiscal_quarter")
                if fq is None or (isinstance(fq, float) and math.isnan(fq)):
                    continue  # 跳过无季度的事件
                events.append({
                    "date": str(r.get("info_date", "")),
                    "event_type": str(r.get("event_type", "")),
                    "fiscal_quarter": str(fq),
                    "event": str(r.get("event", "")),
                })
            return events
    except Exception as e:
        print(f"  [panda_data] 财务事件获取失败: {e}")
    return []


def fetch_ir_events(ticker: str) -> list:
    """获取投资者关系活动 (会议、路演等)"""
    import panda_data
    try:
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=730)).strftime("%Y%m%d")
        ir = panda_data.get_stock_ir_activity(
            symbol=[ticker],
            fields=[],
            start_date=start,
            end_date=end
        )
        if ir is not None and not ir.empty:
            events = []
            for _, r in ir.iterrows():
                events.append({
                    "date": str(r.get("info_date", "")),
                    "event_type": str(r.get("event_type", "")),
                    "event": str(r.get("event", "")),
                })
            return events
    except Exception as e:
        print(f"  [panda_data] IR活动获取失败: {e}")
    return []


# ============ 行业数据 ============

def load_industry_data() -> dict:
    """加载存储行业基准数据"""
    config_path = os.path.join(ROOT_DIR, "config", "industry_data.json")
    if not os.path.exists(config_path):
        print(f"[WARNING] 行业数据配置文件不存在: {config_path}")
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)
