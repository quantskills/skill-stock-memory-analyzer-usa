"""
行业数据自动更新模块

支持两种更新模式:
1. WebFetch 模式: AI 通过 WebSearch/WebFetch 获取最新数据后，调用 update_xxx() 函数写入
2. CLI 模式: python data_updater.py --section dram_price --data '<JSON>'

所有更新自动记录时间戳，分析脚本可据此判断数据新鲜度。
"""
import json
import os
import sys
from datetime import datetime
from typing import Optional

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT_DIR, "config", "industry_data.json")


def _load_config() -> dict:
    """加载配置文件"""
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_config(config: dict):
    """保存配置文件（保留格式）"""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    # 备份旧配置
    backup_path = CONFIG_PATH + ".bak"
    if os.path.exists(CONFIG_PATH):
        try:
            import shutil
            shutil.copy2(CONFIG_PATH, backup_path)
        except Exception:
            pass
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_data_freshness() -> dict:
    """检查各模块数据新鲜度，返回距今天数"""
    config = _load_config()
    today = datetime.now()
    freshness = {}

    sections = {
        "dram_contract_price_qoq": "DRAM 合约价",
        "nand_contract_price_qoq": "NAND 合约价",
        "hbm_market": "HBM 市场数据",
        "gpu_hbm_specs": "GPU HBM 规格",
        "downstream_demand": "下游需求数据",
        "capex_guidance": "CapEx 指引",
        "technology_nodes": "技术节点",
        "memory_peers": "对标公司",
    }

    for key, label in sections.items():
        if key not in config:
            freshness[key] = {"label": label, "status": "missing", "age_days": None}
            continue
        updated_str = config[key].get("_last_updated", "")
        if not updated_str:
            freshness[key] = {"label": label, "status": "unknown", "age_days": None}
            continue
        try:
            updated_date = datetime.strptime(updated_str, "%Y-%m-%d")
            age = (today - updated_date).days
            if age <= 7:
                status = "fresh"
            elif age <= 30:
                status = "stale"
            else:
                status = "outdated"
            freshness[key] = {"label": label, "status": status, "age_days": age}
        except ValueError:
            freshness[key] = {"label": label, "status": "unknown", "age_days": None}

    return freshness


def print_freshness_report():
    """打印数据新鲜度报告（供 AI 判断哪些数据需要更新）"""
    freshness = get_data_freshness()
    print("\n" + "=" * 60)
    print("  industry_data.json 数据新鲜度检查")
    print("=" * 60)
    for key, info in freshness.items():
        icon = {"fresh": "🟢", "stale": "🟡", "outdated": "🔴", "missing": "⚫", "unknown": "⚪"}.get(info["status"], "⚪")
        age_str = f"{info['age_days']}天前" if info['age_days'] is not None else "未知"
        print(f"  {icon} {info['label']:12s} | 状态: {info['status']:8s} | {age_str}")
    print("=" * 60 + "\n")


def update_dram_price(quarters: dict) -> bool:
    """
    更新 DRAM 合约价环比变动数据

    Args:
        quarters: {"2026-Q2": -6.0, "2026-Q3": -3.0, ...}  # QoQ 变动百分比
    """
    config = _load_config()
    if "dram_contract_price_qoq" not in config:
        config["dram_contract_price_qoq"] = {"_note": "DRAM 合约价环比变动(%), 负值=降价周期, 正=涨价周期"}

    section = config["dram_contract_price_qoq"]
    # 清理旧值（保留 _note 和最近8个季度）
    meta_keys = {k: v for k, v in section.items() if str(k).startswith("_")}

    # 合并新数据
    merged = {k: v for k, v in section.items() if not str(k).startswith("_")}
    for q, val in quarters.items():
        merged[q] = float(val)

    # 按季度排序，只保留最近10个
    sorted_qs = sorted(merged.keys(), reverse=True)[:10]

    new_section = dict(meta_keys)
    for q in reversed(sorted_qs):
        new_section[q] = merged[q]
    new_section["_last_updated"] = datetime.now().strftime("%Y-%m-%d")

    config["dram_contract_price_qoq"] = new_section
    _save_config(config)
    print(f"  [OK] DRAM 价格数据已更新 ({len(quarters)} 个新季度)")
    return True


def update_nand_price(quarters: dict) -> bool:
    """
    更新 NAND 合约价环比变动数据

    Args:
        quarters: {"2026-Q2": -10.0, "2026-Q3": -5.0, ...}
    """
    config = _load_config()
    if "nand_contract_price_qoq" not in config:
        config["nand_contract_price_qoq"] = {"_note": "NAND 合约价环比变动(%), 负值=降价周期, 正=涨价周期"}

    section = config["nand_contract_price_qoq"]
    meta_keys = {k: v for k, v in section.items() if str(k).startswith("_")}

    merged = {k: v for k, v in section.items() if not str(k).startswith("_")}
    for q, val in quarters.items():
        merged[q] = float(val)

    sorted_qs = sorted(merged.keys(), reverse=True)[:10]

    new_section = dict(meta_keys)
    for q in reversed(sorted_qs):
        new_section[q] = merged[q]
    new_section["_last_updated"] = datetime.now().strftime("%Y-%m-%d")

    config["nand_contract_price_qoq"] = new_section
    _save_config(config)
    print(f"  [OK] NAND 价格数据已更新 ({len(quarters)} 个新季度)")
    return True


def update_hbm_market(data: dict) -> bool:
    """
    更新 HBM 市场数据

    Args:
        data: {"2024": 160, "2025": 350, "2026_e": 600, "hbm3e_share_2026": 0.65,
               "hbm4_expected": "2026H2", "market_share_estimate": {...}}
    """
    config = _load_config()
    section = config.get("hbm_market", {})
    section.update(data)
    section["_last_updated"] = datetime.now().strftime("%Y-%m-%d")
    config["hbm_market"] = section
    _save_config(config)
    print(f"  [OK] HBM 市场数据已更新")
    return True


def update_gpu_shipments(quarterly_data: dict) -> bool:
    """
    更新 NVIDIA GPU 季度出货量估算

    Args:
        quarterly_data: {"2026-Q2": 1250, "2026-Q3": 1300, ...}  # 千颗
    """
    config = _load_config()
    section = config.get("gpu_hbm_specs", {}).get("quarterly_gpu_shipments_k", {})

    meta_keys = {k: v for k, v in section.items() if str(k).startswith("_")}
    merged = {k: v for k, v in section.items() if not str(k).startswith("_")}
    for q, val in quarterly_data.items():
        merged[q] = int(val)

    sorted_qs = sorted(merged.keys(), reverse=True)[:10]
    new_section = dict(meta_keys)
    for q in reversed(sorted_qs):
        new_section[q] = merged[q]
    new_section["_last_updated"] = datetime.now().strftime("%Y-%m-%d")

    if "gpu_hbm_specs" not in config:
        config["gpu_hbm_specs"] = {}
    config["gpu_hbm_specs"]["quarterly_gpu_shipments_k"] = new_section
    _save_config(config)
    print(f"  [OK] GPU 出货量数据已更新 ({len(quarterly_data)} 个新季度)")
    return True


def update_downstream_demand(data: dict) -> bool:
    """
    更新下游需求终端拆分数据

    Args:
        data: {
            "dram": {"server_data_center": {"share_pct": 40, "yoy_growth_pct": 28}, ...},
            "nand": {"server_data_center": {"share_pct": 35, "yoy_growth_pct": 32}, ...}
        }
    """
    config = _load_config()
    section = config.get("downstream_demand", {})

    if "dram" in data:
        section["dram_demand_split"].update(data["dram"])
        # Remove any old keys that might interfere
        clean = {k: v for k, v in section["dram_demand_split"].items()
                 if not str(k).startswith("_")}
        section["dram_demand_split"] = {
            "_note": section["dram_demand_split"].get("_note", "DRAM 终端需求占比 (%)")
        }
        section["dram_demand_split"].update(clean)

    if "nand" in data:
        section["nand_demand_split"].update(data["nand"])
        clean = {k: v for k, v in section["nand_demand_split"].items()
                 if not str(k).startswith("_")}
        section["nand_demand_split"] = {
            "_note": section["nand_demand_split"].get("_note", "NAND 终端需求占比 (%)")
        }
        section["nand_demand_split"].update(clean)

    section["_last_updated"] = datetime.now().strftime("%Y-%m-%d")
    config["downstream_demand"] = section
    _save_config(config)
    print(f"  [OK] 下游需求数据已更新")
    return True


def update_gpu_mix_ratios(data: dict) -> bool:
    """
    更新 GPU 各代出货占比 (来源: 供应链信息/NVDA财报推断)

    Args:
        data: {"2024": {"H100": 0.7, "H200": 0.3, ...}, "2025-H1": {...}, ...}
    """
    config = _load_config()
    section = config.get("gpu_hbm_specs", {}).get("gpu_mix_ratios", {})
    section.update(data)
    section["_last_updated"] = datetime.now().strftime("%Y-%m-%d")
    if "gpu_hbm_specs" not in config:
        config["gpu_hbm_specs"] = {}
    config["gpu_hbm_specs"]["gpu_mix_ratios"] = section
    _save_config(config)
    print(f"  [OK] GPU 型号占比已更新 ({len(data)} 个时间段)")
    return True


def update_hbm_supply_params(data: dict) -> bool:
    """
    更新 HBM 供给模型参数 (来源: 行业晶圆产能估算)

    Args:
        data: {"base_supply_2024_m_gb": 450, "supply_growth": {...}, "non_nvidia_factor": 1.30}
    """
    config = _load_config()
    section = config.get("gpu_hbm_specs", {}).get("hbm_supply_params", {})
    section.update(data)
    section["_last_updated"] = datetime.now().strftime("%Y-%m-%d")
    if "gpu_hbm_specs" not in config:
        config["gpu_hbm_specs"] = {}
    config["gpu_hbm_specs"]["hbm_supply_params"] = section
    _save_config(config)
    print(f"  [OK] HBM 供给参数已更新")
    return True


def update_nvda_revenue(quarterly_data: dict) -> bool:
    """
    更新 NVDA Data Center Compute 季度营收 (来源: NVDA 季报)

    Args:
        quarterly_data: {"2026-Q2": 672, "2026-Q3": 750, ...}  # $100M 单位
    """
    config = _load_config()
    section = config.get("gpu_hbm_specs", {}).get("nvda_quarterly_revenue", {})

    meta_keys = {k: v for k, v in section.items() if str(k).startswith("_")}
    merged = {k: v for k, v in section.items() if not str(k).startswith("_")}
    for q, val in quarterly_data.items():
        merged[q] = float(val)

    sorted_qs = sorted(merged.keys(), reverse=True)[:10]
    new_section = dict(meta_keys)
    for q in reversed(sorted_qs):
        new_section[q] = merged[q]
    new_section["_last_updated"] = datetime.now().strftime("%Y-%m-%d")

    if "gpu_hbm_specs" not in config:
        config["gpu_hbm_specs"] = {}
    config["gpu_hbm_specs"]["nvda_quarterly_revenue"] = new_section
    _save_config(config)
    print(f"  [OK] NVDA Compute 营收已更新 ({len(quarterly_data)} 个新季度)")
    return True


def update_capex_guidance(ticker: str, capex_data: dict) -> bool:
    """
    更新某公司的 CapEx 指引

    Args:
        ticker: "MU"/"WDC"/"STX"
        capex_data: {"2025": 120, "2026_e": 140, "2027_e": 150}
    """
    config = _load_config()
    section = config.get("capex_guidance", {})
    if ticker.upper() not in section:
        section[ticker.upper()] = {}
    section[ticker.upper()].update(capex_data)
    section["_last_updated"] = datetime.now().strftime("%Y-%m-%d")
    config["capex_guidance"] = section
    _save_config(config)
    print(f"  [OK] {ticker.upper()} CapEx 指引已更新")
    return True


def update_technology_nodes(data: dict) -> bool:
    """
    更新 DRAM/NAND 技术节点路线图

    Args:
        data: {
            "dram": [{"node": "1c nm", "mass_production": "2025H2", "status": "量产", "note": "HBM4主力"},
                     {"node": "1d nm", "mass_production": "2026H2", "status": "研发", "note": "三星率先推出"}, ...],
            "nand": [{"node": "300L+", "mass_production": "2025", "status": "量产", "note": "当前主力"},
                     {"node": "400L+", "mass_production": "2026H2", "status": "试产", "note": "三星V10 BV NAND"}, ...]
        }
    """
    config = _load_config()
    section = config.get("technology_nodes", {})

    if "dram" in data:
        section["dram"] = data["dram"]
    if "nand" in data:
        section["nand"] = data["nand"]

    section["_last_updated"] = datetime.now().strftime("%Y-%m-%d")
    config["technology_nodes"] = section
    _save_config(config)
    print(f"  [OK] 技术节点数据已更新 (DRAM: {len(data.get('dram',[]))} 节点, NAND: {len(data.get('nand',[]))} 节点)")
    return True

def main():
    """CLI 入口：供 AI 通过 Bash 调用更新数据"""
    # Fix Windows console encoding
    import io as _io
    if hasattr(sys.stdout, 'buffer'):
        try:
            sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except Exception:
            pass
    parser = argparse.ArgumentParser(description="存储行业数据更新工具")
    subparsers = parser.add_subparsers(dest="command", help="更新命令")

    # freshness: 检查新鲜度
    subparsers.add_parser("freshness", help="检查所有数据新鲜度")

    # dram-price: 更新 DRAM 价格
    p_dram = subparsers.add_parser("dram-price", help="更新 DRAM 合约价")
    p_dram.add_argument("--data", type=str, required=True,
                        help='JSON 格式季度数据, 如 \'{"2026-Q2":-6,"2026-Q3":-3}\'')

    # nand-price: 更新 NAND 价格
    p_nand = subparsers.add_parser("nand-price", help="更新 NAND 合约价")
    p_nand.add_argument("--data", type=str, required=True,
                        help='JSON 格式季度数据')

    # hbm-market
    p_hbm = subparsers.add_parser("hbm-market", help="更新 HBM 市场数据")
    p_hbm.add_argument("--data", type=str, required=True,
                       help='JSON 格式 HBM 市场数据')

    # gpu-shipments
    p_gpu = subparsers.add_parser("gpu-shipments", help="更新 GPU 出货估算")
    p_gpu.add_argument("--data", type=str, required=True,
                       help='JSON 格式季度出货数据')

    # downstream
    p_down = subparsers.add_parser("downstream", help="更新下游需求拆分")
    p_down.add_argument("--data", type=str, required=True,
                        help='JSON 格式下游需求数据')

    # gpu-mix: 更新GPU型号占比
    p_mix = subparsers.add_parser("gpu-mix", help="更新 GPU 各代出货占比")
    p_mix.add_argument("--data", type=str, required=True,
                       help='JSON format: {"2026":{"H100":0,"H200":0,"B200":0.4,...}}')

    # hbm-supply: 更新HBM供给参数
    p_supply = subparsers.add_parser("hbm-supply", help="更新 HBM 供给模型参数")
    p_supply.add_argument("--data", type=str, required=True,
                          help='JSON: {"base_supply_2024_m_gb":500,"supply_growth":{...},"non_nvidia_factor":1.3}')

    # nvda-revenue: 更新NVDA Compute营收
    p_nvda = subparsers.add_parser("nvda-revenue", help="更新 NVDA DC Compute 季度营收")
    p_nvda.add_argument("--data", type=str, required=True,
                        help='JSON format: {"2026-Q2": 672, ...} ($100M单位)')

    # tech-nodes: 更新技术节点路线图
    p_tech = subparsers.add_parser("tech-nodes", help="更新 DRAM/NAND 技术节点路线图")
    p_tech.add_argument("--data", type=str, required=True,
                        help='JSON format: {"dram": [...], "nand": [...]}')

    # capex
    p_capex = subparsers.add_parser("capex", help="更新 CapEx 指引")
    p_capex.add_argument("--ticker", type=str, required=True)
    p_capex.add_argument("--data", type=str, required=True,
                         help='JSON 格式 CapEx 数据')

    args = parser.parse_args()

    if args.command == "freshness":
        print_freshness_report()

    elif args.command == "dram-price":
        data = json.loads(args.data)
        update_dram_price(data)

    elif args.command == "nand-price":
        data = json.loads(args.data)
        update_nand_price(data)

    elif args.command == "hbm-market":
        data = json.loads(args.data)
        update_hbm_market(data)

    elif args.command == "gpu-shipments":
        data = json.loads(args.data)
        update_gpu_shipments(data)

    elif args.command == "downstream":
        data = json.loads(args.data)
        update_downstream_demand(data)

    elif args.command == "gpu-mix":
        data = json.loads(args.data)
        update_gpu_mix_ratios(data)

    elif args.command == "hbm-supply":
        data = json.loads(args.data)
        update_hbm_supply_params(data)

    elif args.command == "nvda-revenue":
        data = json.loads(args.data)
        update_nvda_revenue(data)

    elif args.command == "tech-nodes":
        data = json.loads(args.data)
        update_technology_nodes(data)

    elif args.command == "capex":
        data = json.loads(args.data)
        update_capex_guidance(args.ticker, data)

    else:
        parser.print_help()


# argparse 在函数内导入避免污染模块级命名空间
import argparse

if __name__ == "__main__":
    main()
