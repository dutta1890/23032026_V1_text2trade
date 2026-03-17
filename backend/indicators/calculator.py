"""Indicator calculator — wraps `ta` library for all technical indicator computations.

Input DataFrame must have lowercase columns: open, high, low, close, volume.
Each function returns a pd.Series or dict of pd.Series.
15 indicators total.
"""

import numpy as np
import pandas as pd
import ta.momentum
import ta.trend
import ta.volatility
import ta.volume


# =============================================================================
# EXISTING 5
# =============================================================================

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """RSI (Relative Strength Index)."""
    return ta.momentum.RSIIndicator(df["close"], window=period).rsi()


def calculate_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Simple Moving Average."""
    return df["close"].rolling(window=period).mean()


def calculate_ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Exponential Moving Average."""
    return ta.trend.EMAIndicator(df["close"], window=period).ema_indicator()


def calculate_macd(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
) -> dict:
    """MACD. Returns {"macd": Series, "signal": Series, "histogram": Series}."""
    ind = ta.trend.MACD(df["close"], window_fast=fast, window_slow=slow, window_sign=signal)
    return {
        "macd": ind.macd(),
        "signal": ind.macd_signal(),
        "histogram": ind.macd_diff(),
    }


def calculate_bollinger(
    df: pd.DataFrame, period: int = 20, std_dev: int = 2
) -> dict:
    """Bollinger Bands. Returns {"upper": Series, "middle": Series, "lower": Series}."""
    ind = ta.volatility.BollingerBands(df["close"], window=period, window_dev=std_dev)
    return {
        "upper": ind.bollinger_hband(),
        "middle": ind.bollinger_mavg(),
        "lower": ind.bollinger_lband(),
    }


# =============================================================================
# COMPLETING EXISTING 3
# =============================================================================

def calculate_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> dict:
    """Stochastic Oscillator. Returns {"k": Series, "d": Series}."""
    stoch = ta.momentum.StochasticOscillator(
        df["high"], df["low"], df["close"],
        window=k_period, smooth_window=d_period,
    )
    return {"k": stoch.stoch(), "d": stoch.stoch_signal()}


def calculate_adx(df: pd.DataFrame, period: int = 14) -> dict:
    """ADX with +DI and -DI. Returns {"adx": Series, "plus_di": Series, "minus_di": Series}."""
    ind = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], window=period)
    return {"adx": ind.adx(), "plus_di": ind.adx_pos(), "minus_di": ind.adx_neg()}


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    return ta.volatility.AverageTrueRange(
        df["high"], df["low"], df["close"], window=period
    ).average_true_range()


# =============================================================================
# 7 NEW INDICATORS
# =============================================================================

def calculate_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3) -> dict:
    """Supertrend indicator. Returns {"supertrend": Series, "direction": Series}.
    direction: 1 = bullish (price above), -1 = bearish (price below).
    """
    atr = ta.volatility.AverageTrueRange(
        df["high"], df["low"], df["close"], window=period
    ).average_true_range()

    hl2 = (df["high"] + df["low"]) / 2
    upper_band = hl2 + multiplier * atr
    lower_band = hl2 - multiplier * atr

    supertrend = pd.Series(np.nan, index=df.index)
    direction = pd.Series(0, index=df.index, dtype=int)

    # Initialize
    first_valid = atr.first_valid_index()
    if first_valid is None:
        return {"supertrend": supertrend, "direction": direction}

    start = df.index.get_loc(first_valid)

    # Carry-forward bands
    final_upper = upper_band.copy()
    final_lower = lower_band.copy()

    for i in range(start + 1, len(df)):
        # Upper band: can only decrease
        if final_upper.iloc[i] < final_upper.iloc[i - 1] or df["close"].iloc[i - 1] > final_upper.iloc[i - 1]:
            pass  # keep current
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]

        # Lower band: can only increase
        if final_lower.iloc[i] > final_lower.iloc[i - 1] or df["close"].iloc[i - 1] < final_lower.iloc[i - 1]:
            pass  # keep current
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]

    # Determine direction and supertrend value
    for i in range(start, len(df)):
        if i == start:
            direction.iloc[i] = 1 if df["close"].iloc[i] > final_upper.iloc[i] else -1
            supertrend.iloc[i] = final_lower.iloc[i] if direction.iloc[i] == 1 else final_upper.iloc[i]
            continue

        prev_dir = direction.iloc[i - 1]
        if prev_dir == 1:
            if df["close"].iloc[i] < final_lower.iloc[i]:
                direction.iloc[i] = -1
                supertrend.iloc[i] = final_upper.iloc[i]
            else:
                direction.iloc[i] = 1
                supertrend.iloc[i] = final_lower.iloc[i]
        else:
            if df["close"].iloc[i] > final_upper.iloc[i]:
                direction.iloc[i] = 1
                supertrend.iloc[i] = final_lower.iloc[i]
            else:
                direction.iloc[i] = -1
                supertrend.iloc[i] = final_upper.iloc[i]

    return {"supertrend": supertrend, "direction": direction}


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """VWAP — resets daily for intraday timeframes.
    For daily data, computes cumulative VWAP over the full range.
    """
    tp = (df["high"] + df["low"] + df["close"]) / 3
    tp_vol = tp * df["volume"]

    # Detect if intraday by checking if multiple candles share the same date
    if "timestamp" in df.columns:
        dates = pd.to_datetime(df["timestamp"]).dt.date
        is_intraday = dates.nunique() < len(df) * 0.8  # heuristic
    else:
        is_intraday = False

    if is_intraday:
        # Reset cumulative sums at each new day
        groups = dates
        cum_tp_vol = tp_vol.groupby(groups).cumsum()
        cum_vol = df["volume"].groupby(groups).cumsum()
    else:
        cum_tp_vol = tp_vol.cumsum()
        cum_vol = df["volume"].cumsum()

    vwap = cum_tp_vol / cum_vol.replace(0, np.nan)
    return vwap


def calculate_pivot_points(df: pd.DataFrame, method: str = "standard") -> dict:
    """Pivot Points from previous candle's HLC.
    Returns {"pivot": Series, "r1": Series, "r2": Series, "s1": Series, "s2": Series}.
    """
    prev_high = df["high"].shift(1)
    prev_low = df["low"].shift(1)
    prev_close = df["close"].shift(1)

    pivot = (prev_high + prev_low + prev_close) / 3

    if method == "standard":
        r1 = 2 * pivot - prev_low
        s1 = 2 * pivot - prev_high
        r2 = pivot + (prev_high - prev_low)
        s2 = pivot - (prev_high - prev_low)
    elif method == "fibonacci":
        diff = prev_high - prev_low
        r1 = pivot + 0.382 * diff
        r2 = pivot + 0.618 * diff
        s1 = pivot - 0.382 * diff
        s2 = pivot - 0.618 * diff
    else:
        # Woodie
        pivot = (prev_high + prev_low + 2 * df["close"]) / 4
        r1 = 2 * pivot - prev_low
        s1 = 2 * pivot - prev_high
        r2 = pivot + (prev_high - prev_low)
        s2 = pivot - (prev_high - prev_low)

    return {"pivot": pivot, "r1": r1, "r2": r2, "s1": s1, "s2": s2}


def calculate_psar(
    df: pd.DataFrame, af_start: float = 0.02, af_increment: float = 0.02, af_max: float = 0.2
) -> pd.Series:
    """Parabolic SAR."""
    ind = ta.trend.PSARIndicator(
        df["high"], df["low"], df["close"],
        step=af_start, max_step=af_max,
    )
    # Combine up and down indicators into a single series
    psar_up = ind.psar_up()
    psar_down = ind.psar_down()
    psar = psar_up.combine_first(psar_down)
    return psar


def calculate_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Commodity Channel Index."""
    return ta.trend.CCIIndicator(
        df["high"], df["low"], df["close"], window=period
    ).cci()


def calculate_williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Williams %R."""
    return ta.momentum.WilliamsRIndicator(
        df["high"], df["low"], df["close"], lbp=period
    ).williams_r()


def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume."""
    return ta.volume.OnBalanceVolumeIndicator(
        df["close"], df["volume"]
    ).on_balance_volume()


# =============================================================================
# REGISTRY: all 15 indicators
# =============================================================================

CALCULATOR_REGISTRY = {
    "RSI": {"fn": calculate_rsi, "defaults": {"period": 14}},
    "SMA": {"fn": calculate_sma, "defaults": {"period": 20}},
    "EMA": {"fn": calculate_ema, "defaults": {"period": 20}},
    "MACD": {"fn": calculate_macd, "defaults": {"fast": 12, "slow": 26, "signal": 9}},
    "Bollinger": {"fn": calculate_bollinger, "defaults": {"period": 20, "std_dev": 2}},
    "Stochastic": {"fn": calculate_stochastic, "defaults": {"k_period": 14, "d_period": 3}},
    "ADX": {"fn": calculate_adx, "defaults": {"period": 14}},
    "ATR": {"fn": calculate_atr, "defaults": {"period": 14}},
    "Supertrend": {"fn": calculate_supertrend, "defaults": {"period": 10, "multiplier": 3}},
    "VWAP": {"fn": calculate_vwap, "defaults": {}},
    "PivotPoints": {"fn": calculate_pivot_points, "defaults": {"method": "standard"}},
    "PSAR": {"fn": calculate_psar, "defaults": {"af_start": 0.02, "af_increment": 0.02, "af_max": 0.2}},
    "CCI": {"fn": calculate_cci, "defaults": {"period": 20}},
    "WilliamsR": {"fn": calculate_williams_r, "defaults": {"period": 14}},
    "OBV": {"fn": calculate_obv, "defaults": {}},
}


def compute_indicator(df: pd.DataFrame, name: str, params: dict):
    """Compute a named indicator with given params. Returns Series or dict of Series."""
    reg = CALCULATOR_REGISTRY.get(name)
    if not reg:
        raise ValueError(f"Unknown indicator: {name}")
    merged = {**reg["defaults"], **params}
    return reg["fn"](df, **merged)
