"""Indicator calculator — wraps `ta` library for all technical indicator computations.

Input DataFrame must have lowercase columns: open, high, low, close, volume.
Each function returns a pd.Series or dict of pd.Series.
"""

import pandas as pd
import ta.momentum
import ta.trend
import ta.volatility


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """RSI (Relative Strength Index). Returns series with NaN for first `period` candles."""
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


# Registry mapping indicator name -> calculator function + default params
CALCULATOR_REGISTRY = {
    "RSI": {"fn": calculate_rsi, "defaults": {"period": 14}},
    "SMA": {"fn": calculate_sma, "defaults": {"period": 20}},
    "EMA": {"fn": calculate_ema, "defaults": {"period": 20}},
    "MACD": {"fn": calculate_macd, "defaults": {"fast": 12, "slow": 26, "signal": 9}},
    "Bollinger": {"fn": calculate_bollinger, "defaults": {"period": 20, "std_dev": 2}},
}


def compute_indicator(df: pd.DataFrame, name: str, params: dict):
    """Compute a named indicator with given params. Returns Series or dict of Series."""
    reg = CALCULATOR_REGISTRY.get(name)
    if not reg:
        raise ValueError(f"Unknown indicator: {name}")
    merged = {**reg["defaults"], **params}
    return reg["fn"](df, **merged)
