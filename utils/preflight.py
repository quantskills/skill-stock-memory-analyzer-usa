"""Runtime preflight checks for the stock-memory-analyzer skill.

This module deliberately uses only the Python standard library so it can explain
missing third-party dependencies before the main analyzer imports them.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parent.parent
REQUIREMENTS_FILE = ROOT_DIR / "requirements.txt"
REQUIRED_PACKAGES = ("panda_data", "pandas", "numpy", "plotly")


def missing_packages(packages: Iterable[str] = REQUIRED_PACKAGES) -> list[str]:
    """Return packages that cannot be imported by the current interpreter."""
    return [package for package in packages if importlib.util.find_spec(package) is None]


def report_dependency_status() -> bool:
    """Print dependency readiness without requesting or inspecting credentials."""
    missing = missing_packages()
    if missing:
        print(f"[SETUP] 缺少 Python 依赖: {', '.join(missing)}")
        print("  安装命令: python -m pip install -r requirements.txt")
        return False
    print("[SETUP] Python 依赖: 就绪")
    return True


def _print_setup_guidance(missing: list[str], credentials_ready: bool) -> None:
    print("\n[SETUP] stock-memory-analyzer 环境检查")
    if missing:
        print(f"  缺少 Python 依赖: {', '.join(missing)}")
        print("  安装命令:")
        print("    python -m pip install -r requirements.txt")
        print("  或自动安装:")
        print("    python analyze.py --install-deps --check-env")
    else:
        print("  Python 依赖: 就绪")

    if credentials_ready:
        print("  panda_data 账号: 已由本地临时进程检测到")
    else:
        print("  panda_data 账号: 未检测到")
        print("  推荐通过可见的本机临时终端窗口输入凭据:")
        print("    Windows: powershell -ExecutionPolicy Bypass -File scripts/run_with_prompt.ps1 -Ticker MU")
        print("    macOS:  bash scripts/run_with_prompt.sh --ticker MU --period 5y")

    print("  网络要求: 需要允许 Python 访问 panda_data API；受限沙箱/企业网络请授予网络权限后重试。")
    print("  报告图表: 首次打开 HTML 时需要访问 cdn.plot.ly；离线环境可正常查看文本和表格。\n")


def run_preflight(
    username: str | None,
    password: str | None,
    *,
    install_deps: bool = False,
    check_only: bool = False,
) -> bool:
    """Check prerequisites and optionally install missing packages.

    Returns ``True`` only when the required Python packages and credentials are
    available.  Installation is opt-in so a normal analysis never changes the
    user's environment unexpectedly.
    """
    missing = missing_packages()
    if install_deps and missing:
        print(f"[SETUP] 正在安装缺失依赖: {', '.join(missing)}")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)]
            )
        except subprocess.CalledProcessError as exc:
            print(f"[ERROR] 依赖安装失败 (exit code {exc.returncode})。请检查网络与 pip 权限。")
            return False
        missing = missing_packages()

    credentials_ready = bool(username and password)
    _print_setup_guidance(missing, credentials_ready)

    if check_only:
        return not missing and credentials_ready
    if missing:
        print("[ERROR] 请先安装依赖，再运行分析。")
        return False
    if not credentials_ready:
        print("[ERROR] 完整分析需要 panda_data 用户名和密码。")
        return False
    return True
