"""
技术指标计算模块 - 全部用 pandas/numpy 手算，减少依赖
"""
import numpy as np
import pandas as pd


def calc_sma(series: pd.Series, window: int) -> pd.Series:
    """简单移动均线"""
    return series.rolling(window=window, min_periods=1).mean()


def calc_ema(series: pd.Series, window: int) -> pd.Series:
    """指数移动均线"""
    return series.ewm(span=window, adjust=False).mean()


def calc_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder's smoothing)"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1/window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50)
    return rsi


def calc_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    MACD 指标

    Returns:
        (macd_line, signal_line, histogram)
    """
    ema_fast = calc_ema(close, fast)
    ema_slow = calc_ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calc_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calc_bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2.0):
    """
    布林带

    Returns:
        (middle, upper, lower, bandwidth, %b)
    """
    middle = calc_sma(close, window)
    std = close.rolling(window=window, min_periods=1).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    # bandwidth = (upper - lower) / middle * 100
    bandwidth = (upper - lower) / middle.replace(0, np.nan) * 100
    # %b = (price - lower) / (upper - lower)
    pct_b = (close - lower) / (upper - lower).replace(0, np.nan)
    return middle, upper, lower, bandwidth, pct_b


def calc_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume"""
    direction = np.sign(close.diff().fillna(0))
    obv = (direction * volume).cumsum()
    return obv


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Average True Range"""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(alpha=1/window, adjust=False).mean()
    return atr


def calc_historical_volatility(close: pd.Series, window: int = 252) -> float:
    """
    历史年化波动率（基于日对数收益率）
    """
    log_returns = np.log(close / close.shift(1)).dropna()
    daily_vol = log_returns.std()
    annual_vol = daily_vol * np.sqrt(window)
    return float(annual_vol)


def calc_rolling_volatility(close: pd.Series, window: int = 30, annualize: int = 252) -> pd.Series:
    """滚动波动率"""
    log_returns = np.log(close / close.shift(1))
    rolling_vol = log_returns.rolling(window=window).std() * np.sqrt(annualize)
    return rolling_vol


def calc_max_drawdown(close: pd.Series) -> dict:
    """
    计算最大回撤

    Returns:
        dict with max_drawdown_pct, peak_date, trough_date, recovery_date
    """
    rolling_max = close.expanding().max()
    drawdown = (close - rolling_max) / rolling_max

    max_dd = drawdown.min()
    trough_idx = drawdown.idxmin()

    if isinstance(trough_idx, pd.Timestamp):
        peak_idx = close[:trough_idx].idxmax()

        # 寻找恢复时间
        peak_value = close[peak_idx]
        recovery_series = close[trough_idx:]
        recovery_idx = None
        for idx, val in recovery_series.items():
            if val >= peak_value:
                recovery_idx = idx
                break

        return {
            "max_drawdown_pct": round(float(max_dd) * 100, 2),
            "peak_date": str(peak_idx).split("T")[0] if peak_idx else None,
            "trough_date": str(trough_idx).split("T")[0],
            "recovery_date": str(recovery_idx).split("T")[0] if recovery_idx else "未恢复",
            "drawdown_series": drawdown
        }
    return {"max_drawdown_pct": 0.0}


def calc_beta(stock_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    计算 Beta 系数

    Beta = Cov(stock, benchmark) / Var(benchmark)
    """
    aligned = pd.concat([stock_returns, benchmark_returns], axis=1).dropna()
    if aligned.empty:
        return 1.0

    cov = aligned.cov().iloc[0, 1]
    var = aligned.iloc[:, 1].var()
    if var == 0:
        return 1.0

    return float(cov / var)


def calc_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    历史模拟法 VaR (Value at Risk)

    Args:
        returns: 日收益率序列
        confidence: 置信水平
    """
    var = np.percentile(returns.dropna(), (1 - confidence) * 100)
    return float(var)


def calc_returns_summary(close: pd.Series) -> dict:
    """
    计算多周期涨跌幅

    Returns:
        {period: pct_change}
    """
    if len(close) < 2:
        return {}

    current = close.iloc[-1]

    def _pct(period: str) -> float:
        try:
            past = close.asof(close.index[-1] - pd.Timedelta(period))
            if pd.isna(past):
                return None
            return round(float((current - past) / past * 100), 2)
        except Exception:
            return None

    return {
        "1W": _pct("7D"),
        "1M": _pct("30D"),
        "3M": _pct("90D"),
        "6M": _pct("180D"),
        "1Y": _pct("365D"),
        "YTD": _pct("365D") if close.index[-1].year == close.index[0].year else _pct(f"{close.index[-1].month * 30}D")
        if close.index[-1].year == close.index[0].year else _pct("365D")
    }


def calc_technicals(df: pd.DataFrame) -> dict:
    """
    批量计算所有技术指标

    Args:
        df: 包含 Open, High, Low, Close, Volume 的 DataFrame

    Returns:
        dict of technical indicators as Series/DataFrames
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    results = {}

    # 均线
    for window in [5, 10, 20, 50, 200]:
        results[f"ma_{window}"] = calc_sma(close, window)
    results["ema_12"] = calc_ema(close, 12)
    results["ema_26"] = calc_ema(close, 26)

    # RSI
    results["rsi_14"] = calc_rsi(close, 14)

    # MACD
    results["macd_line"], results["macd_signal"], results["macd_hist"] = calc_macd(close)

    # 布林带
    results["bb_middle"], results["bb_upper"], results["bb_lower"], results["bb_bw"], results["bb_pct_b"] = \
        calc_bollinger_bands(close)

    # OBV
    results["obv"] = calc_obv(close, volume)

    # ATR
    results["atr_14"] = calc_atr(high, low, close)

    # 波动率
    results["hist_vol"] = calc_historical_volatility(close)
    results["rolling_vol_30"] = calc_rolling_volatility(close, 30)
    results["rolling_vol_60"] = calc_rolling_volatility(close, 60)

    # 最大回撤
    results["max_drawdown"] = calc_max_drawdown(close)

    # 涨跌幅
    results["returns_summary"] = calc_returns_summary(close)

    # VaR
    log_returns = np.log(close / close.shift(1)).dropna()
    results["var_95"] = calc_var(log_returns, 0.95)
    results["var_99"] = calc_var(log_returns, 0.99)

    # 日均成交量
    results["avg_volume_20"] = volume.rolling(20).mean().iloc[-1]
    results["volume_ratio"] = volume.iloc[-1] / results["avg_volume_20"] if results["avg_volume_20"] > 0 else 1.0

    return results
