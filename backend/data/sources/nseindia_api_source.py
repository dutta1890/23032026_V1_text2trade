"""NseIndiaApi data source — PRIMARY for all OHLCV data.

No signup. No API key. No demat account. Built-in rate limiting.
Uses the `nse` package (pip install nse).
"""

import time
import logging
import tempfile
import pandas as pd
from datetime import datetime, timedelta, date
from data.sources.base import MarketDataSource

logger = logging.getLogger(__name__)

NSE_REQUEST_DELAY = 1.5


class NseIndiaApiSource(MarketDataSource):
    """Fetches historical OHLCV data via nse library."""

    def __init__(self):
        self._last_request_time = 0
        self._nse = None

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < NSE_REQUEST_DELAY:
            time.sleep(NSE_REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def _get_nse(self):
        if self._nse is None:
            from nse import NSE
            cache_dir = tempfile.mkdtemp(prefix="nse_cache_")
            self._nse = NSE(cache_dir)
        return self._nse

    def fetch_historical(self, symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch daily OHLCV data. nse package only provides daily data."""
        nse = self._get_nse()
        all_frames = []

        # Convert datetime to date objects
        start_d = start.date() if isinstance(start, datetime) else start
        end_d = end.date() if isinstance(end, datetime) else end

        # Chunk into 60-day windows for reliability
        chunk_days = 60
        current = start_d
        while current < end_d:
            chunk_end = min(current + timedelta(days=chunk_days), end_d)
            self._rate_limit()
            try:
                if symbol in ("NIFTY 50", "NIFTY BANK"):
                    data = nse.fetch_historical_index_data(
                        index=symbol,
                        from_date=current,
                        to_date=chunk_end,
                    )
                else:
                    data = nse.fetch_equity_historical_data(
                        symbol=symbol,
                        series="EQ",
                        from_date=current,
                        to_date=chunk_end,
                    )

                if data and isinstance(data, list) and len(data) > 0:
                    if symbol in ("NIFTY 50", "NIFTY BANK"):
                        df = self._normalize_index_data(data)
                    else:
                        df = self._normalize_equity_data(data)
                    if not df.empty:
                        all_frames.append(df)
                        logger.debug(f"NseIndiaApi: {symbol} {current} to {chunk_end}: {len(df)} rows")
            except Exception as e:
                logger.warning(f"NseIndiaApi: {symbol} {current} to {chunk_end} failed: {e}")

            current = chunk_end + timedelta(days=1)

        if not all_frames:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        df = pd.concat(all_frames, ignore_index=True)
        df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
        return df

    def _normalize_equity_data(self, data: list) -> pd.DataFrame:
        """Normalize nse equity response to standard schema."""
        rows = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                ts_str = (
                    item.get("mtimestamp")
                    or item.get("CH_TIMESTAMP")
                    or item.get("mTIMESTAMP")
                )
                rows.append({
                    "timestamp": pd.to_datetime(ts_str, dayfirst=True),
                    "open": float(item.get("chOpeningPrice", 0) or item.get("CH_OPENING_PRICE", 0) or 0),
                    "high": float(item.get("chTradeHighPrice", 0) or item.get("CH_TRADE_HIGH_PRICE", 0) or 0),
                    "low": float(item.get("chTradeLowPrice", 0) or item.get("CH_TRADE_LOW_PRICE", 0) or 0),
                    "close": float(item.get("chClosingPrice", 0) or item.get("CH_CLOSING_PRICE", 0) or 0),
                    "volume": int(float(item.get("chTotTradedQty", 0) or item.get("CH_TOT_TRADED_QTY", 0) or 0)),
                })
            except (ValueError, TypeError) as e:
                logger.debug(f"Skipping equity row: {e}")
                continue

        if not rows:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        return pd.DataFrame(rows)

    def _normalize_index_data(self, data: list) -> pd.DataFrame:
        """Normalize nse index response."""
        rows = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                ts_str = (
                    item.get("EOD_TIMESTAMP")
                    or item.get("effectiveDate")
                    or item.get("TIMESTAMP")
                )
                rows.append({
                    "timestamp": pd.to_datetime(ts_str, dayfirst=True),
                    "open": float(item.get("EOD_OPEN_INDEX_VAL", 0) or item.get("OPEN", 0) or 0),
                    "high": float(item.get("EOD_HIGH_INDEX_VAL", 0) or item.get("HIGH", 0) or 0),
                    "low": float(item.get("EOD_LOW_INDEX_VAL", 0) or item.get("LOW", 0) or 0),
                    "close": float(item.get("EOD_CLOSE_INDEX_VAL", 0) or item.get("CLOSE", 0) or 0),
                    "volume": int(float(item.get("HIT_TRADED_QTY", 0) or 0)),
                })
            except (ValueError, TypeError):
                continue

        if not rows:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        return pd.DataFrame(rows)

    def test_connection(self) -> dict:
        try:
            nse = self._get_nse()
            self._rate_limit()
            # Test by fetching a small data request
            from datetime import date
            data = nse.fetch_equity_historical_data("RELIANCE", from_date=date.today() - timedelta(days=5), to_date=date.today(), series="EQ")
            if data and len(data) > 0:
                return {"status": "ok", "message": f"NSE India API reachable. Got {len(data)} records.", "provider": "nse-india-api"}
            return {"status": "ok", "message": "NSE India API reachable (no recent data)", "provider": "nse-india-api"}
        except Exception as e:
            return {"status": "error", "message": str(e), "provider": "nse-india-api"}
