"""NSEPython data source — BACKUP for daily OHLCV data.

NOTE: NSE has blocked the free historical equity API endpoint as of late 2024.
This source may fail with KeyError: 'data'. Falls back gracefully.
"""

import time
import logging
import pandas as pd
from datetime import datetime
from data.sources.base import MarketDataSource

logger = logging.getLogger(__name__)

NSE_REQUEST_DELAY = 1.5


class NSEPythonSource(MarketDataSource):
    """Fetches daily OHLCV data from NSE India via nsepython."""

    def __init__(self):
        self._last_request_time = 0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < NSE_REQUEST_DELAY:
            time.sleep(NSE_REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def fetch_historical(self, symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
        if interval != "1d":
            raise ValueError(f"NSEPython only supports '1d' interval, got '{interval}'")

        from nsepython import equity_history, index_history

        start_str = start.strftime("%d-%m-%Y")
        end_str = end.strftime("%d-%m-%Y")

        self._rate_limit()

        try:
            if symbol in ("NIFTY 50", "NIFTY BANK"):
                df = index_history(symbol, start_str, end_str)
            else:
                df = equity_history(symbol, "EQ", start_str, end_str)
        except KeyError as e:
            logger.warning(f"NSEPython API blocked for {symbol} (KeyError: {e}). NSE may have removed this endpoint.")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        except Exception as e:
            logger.warning(f"NSEPython fetch failed for {symbol}: {e}")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        return self._normalize(df)

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        col_map = {}
        for c in df.columns:
            cl = c.lower().strip()
            if "timestamp" in cl or cl == "date" or cl == "ch_timestamp":
                col_map[c] = "timestamp"
            elif cl in ("open", "ch_opening_price"):
                col_map[c] = "open"
            elif cl in ("high", "ch_trade_high_price"):
                col_map[c] = "high"
            elif cl in ("low", "ch_trade_low_price"):
                col_map[c] = "low"
            elif cl in ("close", "ch_closing_price"):
                col_map[c] = "close"
            elif cl in ("volume", "ch_tod_trd_qty"):
                col_map[c] = "volume"

        df = df.rename(columns=col_map)
        if "volume" not in df.columns:
            df["volume"] = 0
        if "timestamp" not in df.columns:
            for c in df.columns:
                try:
                    pd.to_datetime(df[c])
                    df = df.rename(columns={c: "timestamp"})
                    break
                except Exception:
                    continue

        required = ["timestamp", "open", "high", "low", "close", "volume"]
        for r in required:
            if r not in df.columns:
                return pd.DataFrame(columns=required)

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)
        df = df[required].dropna(subset=["timestamp", "close"])
        return df.sort_values("timestamp").reset_index(drop=True)

    def test_connection(self) -> dict:
        try:
            from nsepython import nse_marketStatus
            self._rate_limit()
            status = nse_marketStatus()
            return {"status": "ok", "message": "NSE reachable via nsepython", "provider": "nsepython"}
        except Exception as e:
            return {"status": "error", "message": str(e), "provider": "nsepython"}
