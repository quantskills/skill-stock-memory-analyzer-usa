"""
简易回测模块 — 基于 panda_data 历史数据验证评分有效性

回测逻辑:
1. 每季度基于当时可用的行情+财务数据计算简化评分
2. 记录后续 3个月/6个月 实际收益
3. 分析评分与实际收益的相关性

简化评分权重（去掉不可回测的分析师/内部人/股东/HBM/下游，重新归一化到0-100）:
- 技术面(20%): RSI + MACD
- 库存周期(25%): 库存天数趋势
- 毛利率趋势(20%): 定价能力代理
- CapEx趋势(15%): 扩张/收缩
- 财务质量(20%): 净利率/ROE/负债率
"""
import math
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd


def _calc_quarterly_score(price_df: pd.DataFrame, fin_quarters: dict,
                          quarter_key: str, report_date: str,
                          industry_data: dict = None) -> Optional[dict]:
    """
    计算单个季度的简化评分

    Args:
        price_df: 该季度截止日之前的全部日线数据
        fin_quarters: 所有季度财务数据 {fy_period: {revenue, gross_profit, ...}}
        quarter_key: 当前评估的季度(fy_period)
        report_date: 财报公布日(用该日之前的行情)

    Returns:
        {score, rsi, macd_hist, inv_days, gross_margin, capex_growth, ...} or None
    """
    if price_df.empty or quarter_key not in fin_quarters:
        return None

    close = price_df["Close"]
    if len(close) < 30:
        return None

    # --- 技术面 (20分) ---
    # RSI(14)
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi_val = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = float((macd_line - macd_signal).iloc[-1])

    tech_score = 10  # 基准
    if rsi_val < 30:
        tech_score += 6
    elif rsi_val > 70:
        tech_score -= 4
    if macd_hist > 0:
        tech_score += 4
    else:
        tech_score -= 4
    tech_score = max(0, min(20, tech_score))

    # --- 库存周期 (25分) ---
    q = fin_quarters[quarter_key]
    inv = abs(q.get("inventory") or 0)
    cogs = abs(q.get("cogs") or 0)
    inv_days = inv / cogs * 365 if cogs > 0 else None

    # 计算历史均值
    sorted_keys = sorted(fin_quarters.keys())
    idx = sorted_keys.index(quarter_key)
    hist_inv_days = []
    for k in sorted_keys[max(0, idx-7):idx+1]:
        hq = fin_quarters[k]
        hi = abs(hq.get("inventory") or 0)
        hc = abs(hq.get("cogs") or 0)
        if hc > 0:
            hist_inv_days.append(hi / hc * 365)

    inv_score = 13  # 基准
    if inv_days and len(hist_inv_days) >= 3:
        avg_hist = sum(hist_inv_days) / len(hist_inv_days)
        # 库存低于历史均值 = 利多
        if inv_days < avg_hist * 0.8:
            inv_score = 22
        elif inv_days < avg_hist:
            inv_score = 17
        elif inv_days > avg_hist * 1.2:
            inv_score = 5
        else:
            inv_score = 10

    # --- 毛利率趋势 (20分) ---
    recent_gms = []
    for k in sorted_keys[max(0, idx-3):idx+1]:
        kq = fin_quarters[k]
        kr = abs(kq.get("revenue") or 0)
        kg = abs(kq.get("gross_profit") or 0)
        if kr > 0:
            recent_gms.append(kg / kr * 100)

    gm_score = 10
    gm_current = recent_gms[-1] if recent_gms else 0
    if len(recent_gms) >= 3:
        if recent_gms[-1] > recent_gms[-3] + 3:
            gm_score = 17  # 毛利率上升
        elif recent_gms[-1] < recent_gms[-3] - 3:
            gm_score = 5   # 毛利率下降

    # --- 🆕 价格周期 (25分) — 使用 industry_data DRAM/NAND 合约价 ---
    price_score = 13
    dram_qoq = 0
    nand_qoq = 0
    if industry_data:
        dram_prices = industry_data.get("dram_contract_price_qoq", {})
        nand_prices = industry_data.get("nand_contract_price_qoq", {})
        # 提取年份和季度: "FY2022Q1" → yr=2022, q=1
        qk_clean = quarter_key.replace("FY", "")  # "2022Q1"
        yr = int(qk_clean[:4])
        q_num = int(qk_clean[5:6])  # 1-4
        # 公司财季映射到日历年季度: MU FY Q1=Sep-Nov≈cal Q4, Q2=Dec-Feb≈cal Q1, Q3≈Q2, Q4≈Q3
        cal_q_num = ((q_num + 2) % 4) + 1  # Q1→Q4, Q2→Q1, Q3→Q2, Q4→Q3
        # 找最近4个已知合约价季度
        dram_vals = []
        nand_vals = []
        for offset in range(4):
            target_yr = yr - (1 if cal_q_num - offset <= 0 else 0)
            target_q = ((cal_q_num - offset - 1) % 4) + 1
            target_key = f"{target_yr}-Q{target_q}"
            if target_key in dram_prices:
                dram_vals.append(float(dram_prices[target_key]))
            if target_key in nand_prices:
                nand_vals.append(float(nand_prices[target_key]))
        if dram_vals:
            dram_qoq = sum(dram_vals) / len(dram_vals)
        if nand_vals:
            nand_qoq = sum(nand_vals) / len(nand_vals)
        combined = (dram_qoq + nand_qoq) / 2 if dram_qoq or nand_qoq else 0

        if combined > 10:
            price_score = 23  # 强涨价周期 → 大利好
        elif combined > 3:
            price_score = 18  # 温和涨价
        elif combined > -3:
            price_score = 13  # 平稳
        elif combined > -10:
            price_score = 7   # 温和降价
        else:
            price_score = 2   # 强降价周期 → 利空
    else:
        dram_qoq = 0
        nand_qoq = 0

    # --- 🆕 HBM/AI需求 (15分) — 使用 NVDA 营收增速作为代理 ---
    hbm_score = 8  # 基准
    nvda_rev_growth = None
    if industry_data:
        nvda_rev = industry_data.get("gpu_hbm_specs", {}).get("nvda_quarterly_revenue", {})
        # 映射财季到日历季
        qk_clean = quarter_key.replace("FY", "")
        yr = int(qk_clean[:4])
        q_num = int(qk_clean[5:6])
        cal_q_num = ((q_num + 2) % 4) + 1
        cal_key = f"{yr}-Q{cal_q_num}"
        # 找最近的NVDA营收数据
        for offset in range(2):
            try_yr = yr - (1 if cal_q_num - offset <= 0 else 0)
            try_q = ((cal_q_num - offset - 1) % 4) + 1
            try_key = f"{try_yr}-Q{try_q}"
            if try_key in nvda_rev:
                curr_rev = float(nvda_rev[try_key])
                nvda_rev_growth = None
                # 优先YoY，回退QoQ
                prev_key = f"{try_yr-1}-Q{try_q}"
                if prev_key in nvda_rev:
                    prev_rev = float(nvda_rev[prev_key])
                    nvda_rev_growth = (curr_rev - prev_rev) / prev_rev * 100
                else:
                    # 回退: 用绝对营收规模判定 (无YoY数据时)
                    # NVDA DC Compute营收($100M): <200=早期, 200-400=爆发, >400=巨量
                    nvda_rev_growth = curr_rev / 2  # 规模代理(180→90, 600→300)
                if nvda_rev_growth is not None:
                    if nvda_rev_growth > 80:
                        hbm_score = 14
                    elif nvda_rev_growth > 40:
                        hbm_score = 12
                    elif nvda_rev_growth > 15:
                        hbm_score = 9
                    elif nvda_rev_growth < 0:
                        hbm_score = 4
                break
    hbm_available = nvda_rev_growth is not None

    # --- CapEx趋势 (12分) ---
    capex_vals = []
    for k in sorted_keys[max(0, idx-3):idx+1]:
        kq = fin_quarters[k]
        kc = abs(kq.get("capex") or 0)
        capex_vals.append(kc)

    capex_score = 8
    if len(capex_vals) >= 2 and capex_vals[-2] > 0:
        capex_growth = (capex_vals[-1] - capex_vals[-2]) / capex_vals[-2] * 100
        if capex_growth > 20:
            capex_score = 12  # 激进扩产=看好需求
        elif capex_growth > 5:
            capex_score = 9
        elif capex_growth < -10:
            capex_score = 4

    # --- 财务质量 (20分) ---
    rev = abs(q.get("revenue") or 0)
    ni = abs(q.get("net_income") or 0)
    equity = abs(q.get("shareholders_equity") or 0)
    liab = abs(q.get("total_liabilities") or 0)

    nm = ni / rev * 100 if rev > 0 else 0
    roe = ni / equity * 100 if equity > 0 else 0
    de = liab / equity if equity > 0 else 1

    fin_score = 10
    if nm > 30: fin_score += 4
    elif nm > 15: fin_score += 2
    elif nm <= 0: fin_score -= 5
    if roe > 30: fin_score += 3
    elif roe > 15: fin_score += 1
    elif roe <= 0: fin_score -= 3
    if de < 0.5: fin_score += 2
    elif de > 3: fin_score -= 3
    fin_score = max(0, min(20, fin_score))

    total_score = tech_score + inv_score + price_score + hbm_score + gm_score + capex_score + fin_score
    total_score = max(0, min(100, total_score))

    return {
        "quarter": quarter_key,
        "date": report_date,
        "score": total_score,
        "rsi": round(rsi_val, 1),
        "macd_hist": round(macd_hist, 4),
        "inv_days": round(inv_days, 1) if inv_days else None,
        "gross_margin": round(gm_current, 1),
        "nm": round(nm, 1),
        "sub_scores": {
            "tech": tech_score, "inventory": inv_score,
            "price": price_score, "hbm": hbm_score, "gm": gm_score,
            "capex": capex_score, "finance": fin_score
        },
        "nvda_rev_growth": round(nvda_rev_growth, 1) if nvda_rev_growth else None,
        "hbm_available": hbm_available
    }


def run_backtest(ticker: str, price_df: pd.DataFrame,
                 fin_quarters: dict, industry_data: dict = None) -> dict:
    """
    执行回测

    Args:
        ticker: 股票代码
        price_df: 完整日线数据
        fin_quarters: 所有季度财务 {fy_period: {revenue, ...}}

    Returns:
        {points: [...], correlation, win_rate, tier_returns, strategy_return}
    """
    # 按季度排序
    sorted_qs = sorted(fin_quarters.keys())
    if len(sorted_qs) < 5:
        return {"error": "财务数据不足5个季度，无法回测"}

    # 从 2024-Q1 或第4个季度开始回测（取较晚者, 确保有HBM数据）
    start_idx = 3
    for i, qk in enumerate(sorted_qs):
        if "2024" in qk or "2025" in qk or "2026" in qk:
            start_idx = max(3, i)
            break
    points = []
    for i in range(start_idx, len(sorted_qs)):
        qk = sorted_qs[i]
        q = fin_quarters[qk]
        report_date = q.get("report_date", "")
        if not report_date or report_date == "nan":
            # 估算财报日在季度结束后45天
            yr = int(qk[:4])
            q_num = int(qk[5:6])
            month = q_num * 3
            report_date = f"{yr}-{month+1:02d}-15"

        # 截取财报日之前的行情
        try:
            cutoff = pd.Timestamp(report_date)
        except Exception:
            continue
        hist_price = price_df[price_df.index <= cutoff]
        if len(hist_price) < 60:
            continue

        result = _calc_quarterly_score(hist_price, fin_quarters, qk, report_date, industry_data)
        if result is None:
            continue

        # 计算后续3/6/12月收益
        fwd_3m = None
        fwd_6m = None
        fwd_12m = None
        try:
            price_at_cutoff = float(hist_price["Close"].iloc[-1])
            # 3个月后
            fwd_3m_date = cutoff + pd.DateOffset(months=3)
            fwd_3m_prices = price_df[(price_df.index > cutoff) & (price_df.index <= fwd_3m_date)]
            if len(fwd_3m_prices) > 0:
                fwd_3m = (float(fwd_3m_prices["Close"].iloc[-1]) / price_at_cutoff - 1) * 100

            # 6个月后
            fwd_6m_date = cutoff + pd.DateOffset(months=6)
            fwd_6m_prices = price_df[(price_df.index > cutoff) & (price_df.index <= fwd_6m_date)]
            if len(fwd_6m_prices) > 0:
                fwd_6m = (float(fwd_6m_prices["Close"].iloc[-1]) / price_at_cutoff - 1) * 100

            # 12个月后
            fwd_12m_date = cutoff + pd.DateOffset(months=12)
            fwd_12m_prices = price_df[(price_df.index > cutoff) & (price_df.index <= fwd_12m_date)]
            if len(fwd_12m_prices) > 0:
                fwd_12m = (float(fwd_12m_prices["Close"].iloc[-1]) / price_at_cutoff - 1) * 100
        except Exception:
            pass

        result["fwd_3m_pct"] = round(fwd_3m, 2) if fwd_3m is not None else None
        result["fwd_6m_pct"] = round(fwd_6m, 2) if fwd_6m is not None else None
        result["fwd_12m_pct"] = round(fwd_12m, 2) if fwd_12m is not None else None
        points.append(result)

    if len(points) < 4:
        return {"error": f"有效回测点不足(仅{len(points)}个)"}

    # --- 统计分析 ---
    scores = [p["score"] for p in points]
    fwd_3m_list = [p["fwd_3m_pct"] for p in points if p["fwd_3m_pct"] is not None]
    fwd_6m_list = [p["fwd_6m_pct"] for p in points if p["fwd_6m_pct"] is not None]

    # IC (信息系数): 评分与后续收益的相关性
    valid_3m = [(p["score"], p["fwd_3m_pct"]) for p in points if p["fwd_3m_pct"] is not None]
    valid_6m = [(p["score"], p["fwd_6m_pct"]) for p in points if p["fwd_6m_pct"] is not None]
    valid_12m = [(p["score"], p["fwd_12m_pct"]) for p in points if p["fwd_12m_pct"] is not None]

    def _safe_ic(pairs):
        if len(pairs) < 5: return None
        scores = [s for s, _ in pairs]
        rets = [r for _, r in pairs]
        if np.std(scores) == 0 or np.std(rets) == 0: return None
        return round(np.corrcoef(scores, rets)[0, 1], 3)

    ic_3m = _safe_ic(valid_3m)
    ic_6m = _safe_ic(valid_6m)
    ic_12m = _safe_ic(valid_12m)

    # IR (信息比率) = 策略超额收益 / 超额收益标准差 (年化)
    strategy_excess = []
    for p in points:
        if p["fwd_3m_pct"] is not None and p["fwd_6m_pct"] is not None:
            # 策略收益: 评分≥60买, <40空, 间半仓
            if p["score"] >= 60:
                strat_ret = p["fwd_6m_pct"]
            elif p["score"] < 40:
                strat_ret = 0
            else:
                strat_ret = p["fwd_6m_pct"] * 0.5
            excess = strat_ret - p["fwd_6m_pct"]  # 超额 = 策略 - 持有
            strategy_excess.append(excess)
    if strategy_excess and np.std(strategy_excess) > 0:
        ir_val = round(np.mean(strategy_excess) * 2 / (np.std(strategy_excess) * np.sqrt(2)), 3)
    elif ic_12m is not None:
        # 回退: IR ≈ IC × √breadth (季度再平衡, 每年约4次独立决策)
        ir_val = round(ic_12m * np.sqrt(4), 3)
    else:
        ir_val = None

    # 分层收益
    def tier_returns(pairs, buckets=[(0,20),(20,40),(40,60),(60,80),(80,101)]):
        result = []
        for lo, hi in buckets:
            tier_scores = [s for s, r in pairs if lo <= s < hi]
            tier_rets = [r for s, r in pairs if lo <= s < hi]
            avg_ret = np.mean(tier_rets) if tier_rets else None
            win_rate = sum(1 for r in tier_rets if r > 0) / len(tier_rets) * 100 if tier_rets else None
            result.append({
                "range": f"{lo}-{hi-1 if hi<=100 else 100}",
                "count": len(tier_scores),
                "avg_fwd_return": round(avg_ret, 2) if avg_ret is not None else None,
                "win_rate": round(win_rate, 1) if win_rate is not None else None
            })
        return result

    tier_3m = tier_returns(valid_3m)
    tier_6m = tier_returns(valid_6m)

    # 策略模拟: 评分≥60买入, <40卖出, 之间持有
    strategy_rets = []
    bh_rets = []
    for p in points:
        if p["fwd_3m_pct"] is not None:
            bh_rets.append(p["fwd_3m_pct"])
            if p["score"] >= 60:
                strategy_rets.append(p["fwd_3m_pct"])
            elif p["score"] < 40:
                strategy_rets.append(0)  # 空仓
            else:
                strategy_rets.append(p["fwd_3m_pct"] * 0.5)  # 半仓

    strategy_cum = np.prod([1 + r/100 for r in strategy_rets]) - 1 if strategy_rets else 0
    bh_cum = np.prod([1 + r/100 for r in bh_rets]) - 1 if bh_rets else 0

    # 胜率
    high_score_wins = [r for s, r in valid_3m if s >= 60 and r is not None]
    high_win_rate = sum(1 for r in high_score_wins if r > 0) / len(high_score_wins) * 100 if high_score_wins else None
    low_score_wins = [r for s, r in valid_3m if s < 30 and r is not None]
    low_lose_rate = sum(1 for r in low_score_wins if r < 0) / len(low_score_wins) * 100 if low_score_wins else None

    return {
        "ticker": ticker,
        "points": points,
        "n_points": len(points),
        "date_range": f"{points[0]['quarter']} ~ {points[-1]['quarter']}",
        "ic_3m": ic_3m,
        "ic_6m": ic_6m,
        "ic_12m": ic_12m,
        "ir": ir_val,
        "tier_3m": tier_3m,
        "tier_6m": tier_6m,
        "tier_12m": tier_returns(valid_12m),
        "strategy_cum_pct": round(strategy_cum * 100, 1),
        "bh_cum_pct": round(bh_cum * 100, 1),
        "high_win_rate": round(high_win_rate, 1) if high_win_rate else None,
        "low_lose_rate": round(low_lose_rate, 1) if low_lose_rate else None,
        "avg_score": round(np.mean(scores), 1),
        "avg_fwd_3m": round(np.mean(fwd_3m_list), 2) if fwd_3m_list else None,
    }
