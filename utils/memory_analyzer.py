"""
存储芯片行业专属分析模块
- 库存周期判定
- NAND/DRAM 价格周期定位
- HBM/技术节点分析
- Capex 趋势
"""
from typing import Optional


def analyze_inventory_cycle(inventory_days_trend: list) -> dict:
    """
    分析库存周期位置

    判定逻辑:
    - 库存天数从高位持续下降 → 被动去库存 / 补库存前期 (利多)
    - 库存天数从低位持续上升 → 主动补库存 / 去库存前期 (利空)
    - 库存天数稳定在低位 → 供需平衡偏紧 (中性偏多)
    - 库存天数稳定在高位 → 供需平衡偏松 (中性偏空)

    Returns:
        dict with cycle_phase, trend, current_days, avg_historical, signal
    """
    if not inventory_days_trend or len(inventory_days_trend) < 2:
        return {
            "cycle_phase": "数据不足",
            "trend": "unknown",
            "current_days": None,
            "avg_historical": None,
            "signal": "neutral",
            "analysis": "无法判定库存周期阶段，需要更多季度数据"
        }

    days_values = [d["inventory_days"] for d in inventory_days_trend]
    # 数据按时间升序排列（最老→最新），取最后一个为当前值
    current = days_values[-1]
    avg = sum(days_values) / len(days_values)

    # 趋势判定：看最近几个季度的方向（取最后4个，反转使[0]=最新）
    recent = list(reversed(days_values[-min(4, len(days_values)):]))
    if len(recent) >= 3:
        # recent[0]=最新, recent[1]=上一季, recent[2]=再上一季
        # 库存天数递减 = 库存状况改善
        if recent[0] < recent[1] < recent[2]:
            trend = "declining"   # 库存天数连续下降（向好）
        elif recent[0] > recent[1] > recent[2]:
            trend = "rising"      # 库存天数连续上升（恶化）
        else:
            trend = "mixed"       # 波动
    else:
        trend = "declining" if days_values[-1] < days_values[0] else "rising"

    # 周期阶段判定
    current_vs_avg = current / avg if avg > 0 else 1.0

    if trend == "declining" and current_vs_avg < 0.8:
        cycle_phase = "🔵 被动去库存 → 补库前期"
        signal = "bullish"
        detail = "库存天数持续下降且低于历史均值，下游开始补库存，存储价格有望企稳回升"
    elif trend == "declining" and current_vs_avg >= 0.8:
        cycle_phase = "🟢 主动去库存后期"
        signal = "moderately_bullish"
        detail = "库存天数在下降但仍在历史均值附近，去库存接近尾声"
    elif trend == "rising" and current_vs_avg > 1.2:
        cycle_phase = "🔴 主动补库过度 → 去库前期"
        signal = "bearish"
        detail = "库存天数持续上升且显著高于历史均值，警惕价格下行压力"
    elif trend == "rising" and current_vs_avg <= 1.2:
        cycle_phase = "🟡 补库存中后期"
        signal = "moderately_bearish"
        detail = "库存天数在上升但尚未显著偏离均值，需关注后续走向"
    else:
        cycle_phase = "⚪ 库存水平波动中"
        signal = "neutral"
        detail = "库存天数走势不明确，建议结合 NAND/DRAM 价格信号综合判断"

    return {
        "cycle_phase": cycle_phase,
        "trend": trend,
        "current_days": round(current, 1),
        "avg_historical": round(avg, 1),
        "current_vs_avg_ratio": round(current_vs_avg, 2),
        "signal": signal,
        "analysis": detail,
        "recent_quarters": [
            {"quarter": d["date"], "days": d["inventory_days"]}
            for d in reversed(inventory_days_trend[-4:])
        ]
    }


def analyze_memory_price_cycle(industry_data: dict, gross_margin_trend: list) -> dict:
    """
    分析 NAND/DRAM 价格周期位置

    双重信号:
    1. industry_data.json 中的合约价数据 (手动维护, 作为参考基准)
    2. 公司毛利率趋势 (从 get_fina_ex 实时计算, 作为交叉验证)

    Returns:
        周期阶段判定, 包含 industry_signal + margin_signal + 综合 signal
    """
    dram_prices = industry_data.get("dram_contract_price_qoq", {})
    nand_prices = industry_data.get("nand_contract_price_qoq", {})

    # --- 信号1: 行业价格数据 (手动维护) ---
    quarters = sorted([k for k in dram_prices.keys() if not str(k).startswith("_")], reverse=True)
    recent_dram = [float(dram_prices.get(q, 0)) for q in quarters[:4]]
    nand_quarters = sorted([k for k in nand_prices.keys() if not str(k).startswith("_")], reverse=True)
    recent_nand = [float(nand_prices.get(q, 0)) for q in nand_quarters[:4]]

    avg_dram_change = sum(recent_dram) / len(recent_dram) if recent_dram else 0
    avg_nand_change = sum(recent_nand) / len(recent_nand) if recent_nand else 0
    combined = (avg_dram_change + avg_nand_change) / 2

    # --- 信号2: 公司毛利率趋势 (实时财务数据) ---
    margin_trend = "unknown"
    recent_margins = []
    if gross_margin_trend and len(gross_margin_trend) >= 3:
        recent_margins = [m["gross_margin"] for m in gross_margin_trend[-4:]]
        # 方向判定: 最近3个季度 vs 前一个季度
        if len(recent_margins) >= 3:
            recent_avg = sum(recent_margins[-3:]) / 3
            prev_val = recent_margins[0] if len(recent_margins) >= 4 else recent_margins[-3]
            if recent_avg > prev_val + 3:
                margin_trend = "rising"      # 毛利率上升 = 定价能力增强
            elif recent_avg < prev_val - 3:
                margin_trend = "declining"   # 毛利率下降 = 定价能力减弱
            else:
                margin_trend = "stable"

    # --- 综合判定: 行业价格为主, 毛利率趋势为修正 ---
    # 信号映射
    if combined > 10:
        industry_phase = "🔥 强涨价周期"
        industry_signal = "bullish"
    elif combined > 3:
        industry_phase = "📈 温和涨价周期"
        industry_signal = "moderately_bullish"
    elif combined > -3:
        industry_phase = "➡️ 价格平稳期"
        industry_signal = "neutral"
    elif combined > -10:
        industry_phase = "📉 温和降价周期"
        industry_signal = "moderately_bearish"
    else:
        industry_phase = "❄️ 强降价周期"
        industry_signal = "bearish"

    # 毛利率交叉验证修正
    final_signal = industry_signal
    margin_note = ""
    if margin_trend == "rising" and industry_signal in ("neutral", "moderately_bearish"):
        # 毛利率上升但行业价格平稳/降 → 公司定价能力强于行业, 上调一级
        upgrade = {"neutral": "moderately_bullish", "moderately_bearish": "neutral"}
        final_signal = upgrade.get(industry_signal, industry_signal)
        margin_note = f"（毛利率上升{recent_margins[-1]:.1f}%，公司定价能力强于行业）"
    elif margin_trend == "declining" and industry_signal in ("neutral", "moderately_bullish"):
        # 毛利率下降但行业价格平稳/涨 → 公司可能存在问题, 下调一级
        downgrade = {"neutral": "moderately_bearish", "moderately_bullish": "neutral"}
        final_signal = downgrade.get(industry_signal, industry_signal)
        margin_note = f"（毛利率下降{recent_margins[-1]:.1f}%，注意成本压力）"
    elif margin_trend == "rising" and industry_signal in ("bullish", "moderately_bullish"):
        margin_note = f"（毛利率上升，与行业方向一致，信号增强）"
    elif margin_trend == "declining" and industry_signal in ("bearish", "moderately_bearish"):
        margin_note = f"（毛利率下降，与行业方向一致，双重承压）"
    elif recent_margins:
        margin_note = f"（毛利率稳定在{recent_margins[-1]:.1f}%）"

    # 信号 → 展示用阶段名
    phase_map = {
        "bullish": "🔥 强涨价周期",
        "moderately_bullish": "📈 温和涨价周期",
        "neutral": "➡️ 价格平稳期",
        "moderately_bearish": "📉 温和降价周期",
        "bearish": "❄️ 强降价周期",
    }
    phase = phase_map.get(final_signal, industry_phase)
    if margin_note:
        phase = f"{phase} {margin_note}"

    return {
        "cycle_phase": phase,
        "signal": final_signal,
        "industry_signal": industry_signal,
        "avg_dram_qoq": round(avg_dram_change, 1),
        "avg_nand_qoq": round(avg_nand_change, 1),
        "combined_qoq": round(combined, 1),
        "recent_dram_trend": recent_dram,
        "recent_nand_trend": recent_nand,
        "quarters": quarters[:4],
        "margin_trend": margin_trend,
        "margin_note": margin_note,
        "analysis": _price_analysis_detail(final_signal, avg_dram_change, avg_nand_change)
    }


def _price_analysis_detail(signal: str, dram: float, nand: float) -> str:
    """生成价格分析详情文字"""
    parts = []
    if dram > 0:
        parts.append(f"DRAM 合约价环比上涨 {dram:.1f}%")
    else:
        parts.append(f"DRAM 合约价环比下跌 {abs(dram):.1f}%")
    if nand > 0:
        parts.append(f"NAND 合约价环比上涨 {nand:.1f}%")
    else:
        parts.append(f"NAND 合约价环比下跌 {abs(nand):.1f}%")

    base = "；".join(parts)

    signal_map = {
        "bullish": f"{base}。价格处于上行通道，利好存储厂商营收和毛利率",
        "moderately_bullish": f"{base}。价格温和上行，盈利能力逐步改善",
        "neutral": f"{base}。价格变化不大，需关注后续方向选择",
        "moderately_bearish": f"{base}。价格温和下行，注意毛利率压力",
        "bearish": f"{base}。价格处于下行通道，存储厂商盈利承压严重"
    }
    return signal_map.get(signal, base)


def analyze_hbm_exposure(fundamentals: dict, industry_data: dict) -> dict:
    """
    分析公司 HBM 业务暴露度

    主要依赖行业数据和公司财务指标推算
    """
    info = fundamentals.get("info", {})
    hbm_market = industry_data.get("hbm_market", {})

    company_name = info.get("shortName") or info.get("longName", "")

    # 判定公司是否在 HBM 主要供应商中
    hbm_share = hbm_market.get("market_share_estimate", {})
    company_hbm_share = None
    for name, share in hbm_share.items():
        if name.lower() in company_name.lower():
            company_hbm_share = share
            break

    # 如果没有直接匹配，根据 ticker 判断
    if company_hbm_share is None:
        symbol = info.get("symbol", "").upper()
        if symbol == "MU":
            company_hbm_share = 0.15
        elif "000660" in symbol:
            company_hbm_share = 0.50
        elif "005930" in symbol:
            company_hbm_share = 0.35
        else:
            company_hbm_share = None  # 非 HBM 主要供应商

    result = {
        "hbm_market_size": hbm_market.get("2026_e"),
        "hbm_growth": f"{hbm_market.get('2026_e', 0) / hbm_market.get('2024', 1) * 100 - 100:.0f}%" if hbm_market.get('2024') else None,
        "hbm3e_share": hbm_market.get("hbm3e_share_2026"),
        "hbm4_timeline": hbm_market.get("hbm4_expected"),
        "company_hbm_market_share": company_hbm_share,
        "is_key_hbm_supplier": company_hbm_share is not None,
        "gross_margin_benefit": _estimate_hbm_gm_benefit(company_hbm_share)
    }

    if result["is_key_hbm_supplier"]:
        result["hbm_revenue_estimate"] = hbm_market.get("2026_e", 0) * company_hbm_share
        result["assessment"] = (
            f"公司是 HBM 主要供应商之一，"
            f"估算 2026 年 HBM 营收约 ${result['hbm_revenue_estimate']} 亿。"
            f"HBM 毛利率显著高于传统 DRAM，是公司盈利增长的核心驱动力。"
        )
    else:
        result["assessment"] = "公司当前不是 HBM 主要供应商，AI 存储需求主要通过企业级 SSD 间接受益。"

    return result


def _estimate_hbm_gm_benefit(share: Optional[float]) -> str:
    """估算 HBM 对毛利率的贡献"""
    if share is None:
        return "N/A"
    if share > 0.3:
        return "高 - HBM 营收占比大，毛利率受益显著"
    elif share > 0.1:
        return "中等 - HBM 贡献增长中，毛利率改善有利"
    else:
        return "低位 - HBM 影响暂有限"


def analyze_technology_position(info: dict, industry_data: dict) -> dict:
    """
    分析公司在技术节点竞争中的位置
    """
    tech_nodes = industry_data.get("technology_nodes", {})
    dram_nodes = tech_nodes.get("dram", [])
    nand_nodes = tech_nodes.get("nand", [])

    company_name = info.get("shortName") or info.get("longName", "")

    # 根据公司判断技术路线关注重点
    is_dram_heavy = any(kw in company_name.lower() for kw in ["micron", "sk hynix", "samsung"])
    is_nand_heavy = any(kw in company_name.lower() for kw in ["micron", "western digital", "kioxia"])

    result = {
        "dram_nodes": dram_nodes,
        "nand_nodes": nand_nodes,
        "is_dram_heavy": is_dram_heavy,
        "is_nand_heavy": is_nand_heavy,
    }

    # 判断当前主力节点和下一代 (用包含匹配，兼容"试产/研发""试产/量产"等组合状态)
    def _is_current(status: str) -> bool:
        return any(kw in status for kw in ["成熟", "上量中", "量产"])
    def _is_next(status: str) -> bool:
        return any(kw in status for kw in ["试产", "研发"]) and "量产" not in status

    current_dram = [n for n in dram_nodes if _is_current(n["status"])]
    next_dram = [n for n in dram_nodes if _is_next(n["status"])]
    current_nand = [n for n in nand_nodes if _is_current(n["status"])]
    next_nand = [n for n in nand_nodes if _is_next(n["status"])]

    result["current_primary_dram"] = current_dram[-1]["node"] if current_dram else "未知"
    result["next_dram_node"] = next_dram[0]["node"] if next_dram else "未知"
    result["current_primary_nand"] = current_nand[-1]["node"] if current_nand else "未知"
    result["next_nand_node"] = next_nand[0]["node"] if next_nand else "未知"

    return result


def analyze_capex_trend(fundamentals: dict, industry_data: dict, ticker: str) -> dict:
    """
    分析 Capex 趋势

    从 get_fina_ex 季度财务数据中提取 Capex (cfs_capex_total),
    与 industry_data.json 中的指引对比 (手动维护)
    """
    ticker_upper = ticker.upper()
    capex_guidance = industry_data.get("capex_guidance", {}).get(ticker_upper, {})

    # 从 get_fina_ex 财务数据提取 Capex (每季度)
    fin = fundamentals.get("financials", {})
    actual_capex = {}  # {year: capex_billion_usd}
    capex_yearly = {}  # {year: sum_of_quarterly_capex}

    for period, metrics in sorted(fin.items()):
        capex_val = metrics.get("capex")
        if capex_val is None:
            continue
        # period 格式: "2024q1" → year = 2024
        year = period[:4]
        capex_abs = abs(capex_val) / 1e8  # 转为亿美元
        if year not in capex_yearly:
            capex_yearly[year] = 0
        capex_yearly[year] += capex_abs

    # 用年度汇总结果填充 (取完整4季度数据)
    for year, total in sorted(capex_yearly.items()):
        # 只保留有完整数据的年份 (>=3个季度)
        q_count = sum(1 for p in fin if p.startswith(year))
        if q_count >= 3:
            actual_capex[year] = round(total, 1)

    years = sorted(actual_capex.keys())
    if len(years) >= 2:
        recent_capex = actual_capex[years[-1]]
        prev_capex = actual_capex[years[-2]]
        if prev_capex > 0:
            capex_growth = (recent_capex - prev_capex) / prev_capex * 100
        else:
            capex_growth = 0
    elif len(years) == 1:
        capex_growth = 0
    else:
        capex_growth = 0

    if capex_growth > 20:
        expansion_phase = "激进扩产"
    elif capex_growth > 5:
        expansion_phase = "温和扩产"
    elif capex_growth > -5:
        expansion_phase = "维持"
    else:
        expansion_phase = "收缩"

    return {
        "actual_capex": actual_capex,
        "guidance": capex_guidance,
        "capex_growth_pct": round(capex_growth, 1),
        "expansion_phase": expansion_phase,
        "years": years
    }


def analyze_hbm_gpu_demand(industry_data: dict) -> dict:
    """
    HBM GPU 需求量化模型 (v2: 基于 NVDA 财报营收反推)

    核心逻辑:
    1. 需求侧: NVDA 季度 Compute(GPU)营收 → ÷加权ASP → GPU出货量 → ×每卡HBM → HBM需求
    2. 供给侧: 基于行业产能估算
    3. 代际迭代: HBM容量/GPU 从 80GB→512GB

    数据来源:
    - NVDA Compute 营收: NVDA 季报(公开) → industry_data.json
    - GPU ASP: 行业估算 (H100~$25K, H200~$35K, B200~$45K, B300~$55K)
    - HBM 规格: NVIDIA 官方白皮书
    - 非 NVIDIA 因子: TrendForce 行业份额估算
    - 供给: 行业产能估算

    Returns:
        dict with demand_supply gap, per-generation breakdown, growth trajectory
    """
    gpu_specs = industry_data.get("gpu_hbm_specs", {})
    generations = gpu_specs.get("generations", [])
    nvda_revenue = gpu_specs.get("nvda_quarterly_revenue", {})
    asp_data = gpu_specs.get("asp_per_gpu_k_usd", {})

    if not generations or not nvda_revenue:
        return {"available": False, "reason": "NVDA 营收或 GPU 规格数据不可用"}

    # --- 1. 需求侧: NVDA Compute营收 → GPU出货 → HBM需求 ---
    quarters = sorted([q for q in nvda_revenue.keys() if not str(q).startswith("_")])
    demand_by_quarter = []

    # GPU 型号占比 (从配置文件读取, 可通过 WebSearch 更新)
    mix_config = gpu_specs.get("gpu_mix_ratios", {})
    def _get_mix(q: str):
        """从配置读取各季度 GPU 型号占比"""
        if "2024" in q:
            m = mix_config.get("2024", {})
        elif q in ("2025-Q1", "2025-Q2"):
            m = mix_config.get("2025-H1", {})
        elif q in ("2025-Q3", "2025-Q4"):
            m = mix_config.get("2025-H2", {})
        else:
            m = mix_config.get("2026", {})
        return (
            m.get("H100", 0), m.get("H200", 0),
            m.get("B200", 0), m.get("B300", 0), m.get("Rubin", 0)
        )

    # GPU 各代规格 (NVIDIA 官方白皮书)
    hbm_per_gen = [80, 141, 192, 288, 384]  # H100, H200, B200, B300, Rubin
    asp_per_gen = [
        asp_data.get("H100", 25),
        asp_data.get("H200", 35),
        asp_data.get("B200", 45),
        asp_data.get("B300", 55),
        asp_data.get("Rubin", 65)
    ]

    for q in quarters:
        compute_rev_100m = float(nvda_revenue.get(q, 0))  # $100M 单位
        if compute_rev_100m <= 0:
            continue

        shares = _get_mix(q)

        # 加权平均 ASP ($K)
        weighted_asp = sum(s * a for s, a in zip(shares, asp_per_gen))
        # 加权平均 HBM/卡 (GB)
        weighted_hbm = sum(s * h for s, h in zip(shares, hbm_per_gen))

        # GPU出货(千颗) = 营收($100M) × 100 / ASP($K)
        gpu_shipments_k = compute_rev_100m * 100 / weighted_asp if weighted_asp > 0 else 0
        # HBM需求(百万GB) = GPU出货(千颗) × 1000 × HBM/卡(GB) / 1e6
        hbm_demand_m_gb = gpu_shipments_k * 1000 * weighted_hbm / 1e6

        demand_by_quarter.append({
            "quarter": q,
            "compute_rev_100m_usd": compute_rev_100m,
            "gpu_shipments_k": round(gpu_shipments_k, 0),
            "weighted_asp_k_usd": round(weighted_asp, 1),
            "avg_hbm_per_gpu_gb": round(weighted_hbm, 1),
            "total_hbm_demand_m_gb": round(hbm_demand_m_gb, 1)
        })

    # --- 2. 非 NVIDIA 加速器 HBM 需求 (从配置读取) ---
    supply_params = gpu_specs.get("hbm_supply_params", {})
    non_nvidia_factor = supply_params.get("non_nvidia_factor", 1.30)

    # --- 3. HBM 供应端 (从配置读取基准+增速) ---
    base_supply_2024 = supply_params.get("base_supply_2024_m_gb", 450)
    supply_growth = supply_params.get("supply_growth", {2024: 0.0, 2025: 0.45, 2026: 0.50})
    supply_by_year = {}
    cumulative = base_supply_2024
    for yr in ["2024", "2025", "2026"]:
        yr_int = int(yr)
        growth = supply_growth.get(yr_int, 0.5)
        if yr == "2024":
            supply = base_supply_2024
        else:
            supply = cumulative * (1 + growth)
        supply_by_year[yr] = round(supply, 1)
        cumulative = supply

    # --- 4. 供需缺口 ---
    yearly_demand = {}
    for d in demand_by_quarter:
        yr = d["quarter"][:4]
        if yr not in yearly_demand:
            yearly_demand[yr] = 0
        yearly_demand[yr] += d["total_hbm_demand_m_gb"]

    # 2026年目前只报了Q1-Q2, 用NVDA指引外推Q3-Q4
    for yr in yearly_demand:
        q_count = sum(1 for d in demand_by_quarter if d["quarter"].startswith(yr))
        if q_count < 4 and yr == "2026":
            # 用最近两个季度的均值外推剩余季度
            recent_avg = yearly_demand[yr] / q_count
            missing_qs = 4 - q_count
            yearly_demand[yr] += recent_avg * missing_qs
            yearly_demand[yr] = round(yearly_demand[yr], 1)

    gaps = {}
    for yr in ["2024", "2025", "2026"]:
        nv_demand = yearly_demand.get(yr, 0)
        total_demand = nv_demand * non_nvidia_factor
        supply = supply_by_year.get(yr, 0)
        gap = total_demand - supply  # 正=短缺, 负=过剩
        gap_ratio = (gap / total_demand * 100) if total_demand > 0 else 0
        # 判定: 短缺>5%=紧张, ±5%=紧平衡, 过剩>5%=充裕
        if gap_ratio > 5:
            status = "供给紧张"
        elif gap_ratio > -5:
            status = "紧平衡"
        else:
            status = "供给充裕"
        gaps[yr] = {
            "demand_m_gb": round(total_demand, 1),
            "supply_m_gb": round(supply, 1),
            "gap_m_gb": round(gap, 1),
            "gap_ratio_pct": round(gap_ratio, 1),
            "status": status
        }

    # --- 5. 代际迭代分析 ---
    gen_analysis = []
    for gen in generations:
        next_gen = None
        for g in generations:
            if g.get("ship_year", "") > gen.get("ship_year", ""):
                if next_gen is None or g.get("ship_year", "") < next_gen.get("ship_year", ""):
                    next_gen = g
        capacity_growth = 0
        if next_gen:
            capacity_growth = (next_gen["hbm_capacity_gb"] - gen["hbm_capacity_gb"]) / gen["hbm_capacity_gb"] * 100
        gen_analysis.append({
            "name": gen["name"],
            "hbm_type": gen["hbm_type"],
            "capacity_gb": gen["hbm_capacity_gb"],
            "stacks": gen.get("stacks"),
            "ship_year": gen["ship_year"],
            "status": gen["status"],
            "next_gen_growth_pct": round(capacity_growth, 0) if capacity_growth else None
        })

    latest_gap = gaps.get("2026", gaps.get("2025", {}))
    gap_status = latest_gap.get("status", "未知")

    if gap_status == "供给紧张":
        assessment = (
            f"在当前模型假设下，HBM 供给缺口估算为 {latest_gap.get('gap_ratio_pct', 0):.1f}%，"
            f"对应“供给紧张”情景。该结果由 GPU 营收、ASP、型号占比和供应增速推导，"
            f"不是供应商直接披露的完整行业位元供给；应结合报告中的范围、假设和置信度解读。"
        )
    elif gap_status == "紧平衡":
        assessment = (
            f"在当前模型假设下，HBM 供需差估算为 {latest_gap.get('gap_ratio_pct', 0):.1f}%"
            f"（正值=短缺，负值=过剩），对应“紧平衡”情景。"
            f"该结果不是公司披露事实，需结合输入范围与敏感性复核。"
        )
    else:
        assessment = "在当前模型假设下，HBM 供给对应充裕情景；该判断不是公司披露事实。"

    return {
        "available": True,
        "demand_by_quarter": demand_by_quarter,
        "supply_by_year": supply_by_year,
        "yearly_gaps": gaps,
        "gen_analysis": gen_analysis,
        "assessment": assessment,
        "gap_status": gap_status
    }


def analyze_end_market_demand(industry_data: dict) -> dict:
    """
    下游需求终端拆分分析

    按 DRAM/NAND/HBM 三类存储，分别拆分下游终端需求:
    - DRAM: 服务器/PC/手机/汽车/工业
    - NAND: 服务器/PC/手机/汽车/工业
    - HBM: AI训练/AI推理/HPC/其他

    Returns:
        dict with per-type breakdown, weighted growth, key insights
    """
    downstream = industry_data.get("downstream_demand", {})
    if not downstream:
        return {"available": False, "reason": "下游需求数据不可用"}

    results = {}

    # --- DRAM 需求拆分 ---
    dram = downstream.get("dram_demand_split", {})
    dram_weighted_growth = 0
    dram_segments = []
    for seg_name, seg_data in dram.items():
        if str(seg_name).startswith("_"):
            continue  # 跳过元数据字段
        share = seg_data.get("share_pct", 0)
        growth = seg_data.get("yoy_growth_pct", 0)
        driver = seg_data.get("driver", "")
        dram_weighted_growth += share * growth / 100
        dram_segments.append({
            "segment": seg_name.replace("_", " ").title(),
            "share_pct": share,
            "yoy_growth_pct": growth,
            "driver": driver,
            "impact": "🚀 核心驱动" if share >= 25 and growth > 10 else
                      ("📈 稳健增长" if growth > 10 else
                       ("➡️ 平稳" if growth >= 0 else "📉 拖累"))
        })
    dram_segments.sort(key=lambda x: x["share_pct"], reverse=True)

    # --- NAND 需求拆分 ---
    nand = downstream.get("nand_demand_split", {})
    nand_weighted_growth = 0
    nand_segments = []
    for seg_name, seg_data in nand.items():
        if str(seg_name).startswith("_"):
            continue  # 跳过元数据字段
        share = seg_data.get("share_pct", 0)
        growth = seg_data.get("yoy_growth_pct", 0)
        driver = seg_data.get("driver", "")
        nand_weighted_growth += share * growth / 100
        nand_segments.append({
            "segment": seg_name.replace("_", " ").title(),
            "share_pct": share,
            "yoy_growth_pct": growth,
            "driver": driver,
            "impact": "🚀 核心驱动" if share >= 25 and growth > 10 else
                      ("📈 稳健增长" if growth > 10 else
                       ("➡️ 平稳" if growth >= 0 else "📉 拖累"))
        })
    nand_segments.sort(key=lambda x: x["share_pct"], reverse=True)

    # --- HBM 需求拆分 ---
    hbm = downstream.get("hbm_demand_split", {})
    hbm_weighted_growth = 0
    hbm_segments = []
    # HBM 整体增速 ~60% YoY (AI驱动)
    hbm_overall_growth = 60
    for seg_name, seg_data in hbm.items():
        if str(seg_name).startswith("_"):
            continue  # 跳过元数据字段
        share = seg_data.get("share_pct", 0)
        note = seg_data.get("note", "")
        hbm_segments.append({
            "segment": seg_name.replace("_", " ").title(),
            "share_pct": share,
            "yoy_growth_pct": hbm_overall_growth * share / max(share, 1),
            "driver": note,
            "impact": "🚀 核心驱动"
        })
    hbm_segments.sort(key=lambda x: x["share_pct"], reverse=True)

    # --- 综合评估 ---
    dram_status = "强需求" if dram_weighted_growth > 15 else ("温和增长" if dram_weighted_growth > 5 else "需求疲软")
    nand_status = "强需求" if nand_weighted_growth > 15 else ("温和增长" if nand_weighted_growth > 5 else "需求疲软")
    hbm_status = "爆发增长" if hbm_overall_growth > 40 else "快速增长"

    assessments = {
        "dram": f"DRAM 加权需求增速 {dram_weighted_growth:.1f}%，{dram_status}。"
                f"最大驱动力为{'AI服务器' if dram_segments[0]['share_pct'] >= 30 else dram_segments[0]['segment']}（占比{dram_segments[0]['share_pct']}%）。",
        "nand": f"NAND 加权需求增速 {nand_weighted_growth:.1f}%，{nand_status}。"
                f"AI 数据存储和企业级 SSD 需求旺盛，消费级市场逐步复苏。",
        "hbm": f"HBM 市场处于{hbm_status}阶段，完全由 AI 大模型训练和推理需求驱动。"
               f"训练需求占比 55%，推理需求快速增长至 30%。"
    }

    return {
        "available": True,
        "dram": {
            "segments": dram_segments,
            "weighted_growth_pct": round(dram_weighted_growth, 1),
            "status": dram_status
        },
        "nand": {
            "segments": nand_segments,
            "weighted_growth_pct": round(nand_weighted_growth, 1),
            "status": nand_status
        },
        "hbm": {
            "segments": hbm_segments,
            "weighted_growth_pct": round(hbm_overall_growth, 1),
            "status": hbm_status
        },
        "assessments": assessments
    }


def generate_memory_assessment(
    inv_analysis: dict,
    price_analysis: dict,
    capex_analysis: dict,
    hbm_demand: dict = None,
    end_market: dict = None,
    tech_position: dict = None,
    industry_data: dict = None,
    ticker: str = "MU"
) -> dict:
    """
    综合评估：汇总所有存储专属分析，给出综合评分（公司差异化版本）
    权重: 库存20%, 价格25%, CapEx15%, HBM供需20%, 下游需求15%, 技术节点5%
    """
    # 读取公司业务结构
    profiles = (industry_data or {}).get("company_profiles", {})
    comp = profiles.get(ticker, {})
    comp_mix = comp.get("revenue_mix", {})
    comp_hbm = comp.get("hbm_tier", "")
    comp_dram_node = comp.get("dram_node", "")
    comp_nand_node = comp.get("nand_node", "")
    score = 50
    signals = []
    detail = {}

    # 1. 库存周期 (权重 20%)
    inv_map = {"bullish": 20, "moderately_bullish": 10, "neutral": 0,
               "moderately_bearish": -10, "bearish": -20}
    inv_score = inv_map.get(inv_analysis.get("signal", "neutral"), 0)
    score += inv_score
    signals.append(f"库存: {inv_analysis.get('cycle_phase', 'N/A')} ({'+' if inv_score >= 0 else ''}{inv_score})")
    detail["库存周期"] = f"{inv_analysis.get('cycle_phase', 'N/A')} | 得分{inv_score:+d}"

    # 2. 价格周期 (权重 25%) — 行业通用, 但NAND/DRAM价格对不涉及的公司影响降低
    price_map = {"bullish": 25, "moderately_bullish": 12, "neutral": 0,
                 "moderately_bearish": -12, "bearish": -25}
    price_score = price_map.get(price_analysis.get("signal", "neutral"), 0)
    score += price_score
    signals.append(f"价格: DRAM {price_analysis.get('avg_dram_qoq', 0):+.0f}% / NAND {price_analysis.get('avg_nand_qoq', 0):+.0f}% ({'+' if price_score >= 0 else ''}{price_score})")
    detail["价格周期"] = f"DRAM {price_analysis.get('avg_dram_qoq', 0):+.1f}% / NAND {price_analysis.get('avg_nand_qoq', 0):+.1f}% QoQ | 得分{price_score:+d}"

    # 3. CapEx 趋势 (权重 15%)
    phase = capex_analysis.get("expansion_phase", "维持")
    capex_map = {"激进扩产": 12, "温和扩产": 6, "维持": 0, "收缩": -6}
    capex_score = capex_map.get(phase, 0)
    score += capex_score
    signals.append(f"Capex: {phase} ({'+' if capex_score >= 0 else ''}{capex_score})")
    detail["CapEx趋势"] = f"{phase} (增速{capex_analysis.get('capex_growth_pct', 0):+.1f}%) | 得分{capex_score:+d}"

    # 4. HBM 供需 (权重 20%) — 🔧 公司差异化
    if hbm_demand and hbm_demand.get("available"):
        gaps = hbm_demand.get("yearly_gaps", {})
        latest_gap = gaps.get("2026", gaps.get("2025", {}))
        gap_pct = latest_gap.get("gap_ratio_pct", 0)
        gap_status = latest_gap.get("status", "")
        if gap_status == "供给紧张":
            base_hbm = 18 if gap_pct > 15 else 12
        elif gap_status == "紧平衡":
            base_hbm = 6
        else:
            base_hbm = -5
        # 公司差异化因子: 主要供应商=1.0, 部分涉及=0.6, 不涉及=0.3
        hbm_factor = 1.0 if comp_hbm == "主要供应商" else (0.3 if comp_hbm == "不涉及" else 0.6)
        hbm_score = int(base_hbm * hbm_factor)
        score += hbm_score
        tier_tag = "直接受益" if hbm_factor >= 1.0 else "间接受益"
        signals.append(f"HBM供需模型: {gap_status} {tier_tag} ({'+' if hbm_score >= 0 else ''}{hbm_score})")
        detail["HBM供需"] = f"模型估算 {gap_status} (缺口{gap_pct:.0f}%) | 基础{base_hbm:+d}×{hbm_factor}={hbm_score:+d}"
    else:
        detail["HBM供需"] = "数据不可用 | 得分0"

    # 5. 下游需求 (权重 15%) — 🔧 公司加权增速
    if end_market and end_market.get("available"):
        dram_g = end_market.get("dram", {}).get("weighted_growth_pct", 0)
        nand_g = end_market.get("nand", {}).get("weighted_growth_pct", 0)
        hbm_g = end_market.get("hbm", {}).get("weighted_growth_pct", 0)
        hdd_g = 5
        w = (comp_mix.get("dram",0)*dram_g + comp_mix.get("nand",0)*nand_g +
             comp_mix.get("hbm",0)*hbm_g + comp_mix.get("hdd",0)*hdd_g)
        if w > 15:
            demand_score = 12
        elif w > 8:
            demand_score = 6
        elif w > 0:
            demand_score = 2
        else:
            demand_score = -5
        score += demand_score
        signals.append(f"下游: 公司加权{w:+.0f}% ({'+' if demand_score >= 0 else ''}{demand_score})")
        detail["下游需求"] = f"公司加权 {w:+.1f}% (DRAM{comp_mix.get('dram',0)*dram_g:+.0f} NAND{comp_mix.get('nand',0)*nand_g:+.0f} HBM{comp_mix.get('hbm',0)*hbm_g:+.0f} HDD{comp_mix.get('hdd',0)*hdd_g:+.0f}) | 得分{demand_score:+d}"
    else:
        detail["下游需求"] = "数据不可用 | 得分0"

    # 6. 技术节点 (权重 5%) — 🔧 公司实际节点
    dram_s = 3 if any(x in comp_dram_node for x in ["1c","1d"]) else (1 if any(x in comp_dram_node for x in ["1a","1b"]) else 0)
    nand_s = 3 if any(x in comp_nand_node for x in ["400","500","1000"]) else (1 if any(x in comp_nand_node for x in ["276","300","321","218"]) else 0)
    tech_score = dram_s + nand_s + (1 if dram_s + nand_s > 0 else 0)  # 0~7
    score += tech_score
    detail["技术节点"] = f"{comp.get('name',ticker)}: DRAM {comp_dram_node} | NAND {comp_nand_node} | 得分{tech_score:+d}"

    score = max(0, min(100, round(score)))

    if score >= 70:
        rating = "🟢 较强研究信号"
    elif score >= 55:
        rating = "🟡 偏强研究信号"
    elif score >= 45:
        rating = "⚪ 中性研究信号"
    elif score >= 30:
        rating = "🟠 偏弱研究信号"
    else:
        rating = "🔴 较弱研究信号"

    return {
        "composite_score": score,
        "rating": rating,
        "signals": signals,
        "detail": detail,
        "key_observations": _generate_observations(score, signals, hbm_demand, end_market)
    }


def _generate_observations(score: int, signals: list,
                           hbm_demand: dict = None, end_market: dict = None) -> list:
    """生成关键观察"""
    observations = []
    for s in signals:
        observations.append(s)

    hbm_note = ""
    if hbm_demand and hbm_demand.get("available"):
        gaps = hbm_demand.get("yearly_gaps", {})
        g2026 = gaps.get("2026", {})
        hbm_note = f" | HBM模型缺口{g2026.get('gap_ratio_pct',0):.0f}%"

    if score >= 70:
        observations.append(f"💡 多项研究指标偏正面；请结合数据新鲜度和 HBM 估算假设复核{hbm_note}")
    elif score >= 55:
        observations.append(f"💡 正面与不确定指标并存；重点复核价格拐点和 HBM 进展{hbm_note}")
    elif score >= 45:
        observations.append("💡 指标分歧较大，需补充数据或等待下一期公开披露验证")
    elif score >= 30:
        observations.append("💡 多项指标偏弱，应重点核验 NAND/DRAM 价格和库存变化")
    else:
        observations.append("💡 风险或数据缺失信号占主导，需要进一步核验周期与财务数据")

    return observations
