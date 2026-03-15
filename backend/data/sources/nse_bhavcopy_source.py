"""NSE Bhavcopy data source — FALLBACK for daily OHLCV.

No install, no signup, no API key. Public government data.
Downloads official NSE end-of-day CSV archives.
Daily OHLCV only (no intraday).
"""

import io
import time
import zipfile
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from data.sources.base import MarketDataSource

logger = logging.getLogger(__name__)

NSE_REQUEST_DELAY = 1.5

BHAVCOPY_URL_TEMPLATE = (
    "https://nsearchives.nseindia.com/content/cm/"
    "BhavCopy_NSE_CM_0_0_0_{date}_F_0000.csv.zip"
)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.nseindia.com/",
}


class NSEBhavcopySource(MarketDataSource):
    """Fetches daily OHLCV from official NSE Bhavcopy archives."""

    def __init__(self):
        self._last_request_time = 0
        self._session = None

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < NSE_REQUEST_DELAY:
            time.sleep(NSE_REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def _get_session(self):
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(NSE_HEADERS)
            # Warm up session with NSE homepage
            try:
                self._rate_limit()
                self._session.get("https://www.nseindia.com/", timeout=10)
            except Exception:
                pass
        return self._session

    def fetch_historical(self, symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch daily OHLCV from Bhavcopy archives. Only supports '1d'."""
        if interval != "1d":
            raise ValueError("NSE Bhavcopy only supports '1d' interval")

        session = self._get_session()
        all_rows = []
        current = start

        while current <= end:
            # Skip weekends
            if current.weekday() >= 5:
                current += timedelta(days=1)
                continue

            date_str = current.strftime("%Y%m%d")
            url = BHAVCOPY_URL_TEMPLATE.format(date=date_str)

            self._rate_limit()
            try:
                resp = session.get(url, timeout=15)
                if resp.status_code == 200:
                    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                        for name in zf.namelist():
                            if name.endswith(".csv"):
                                csv_data = zf.read(name).decode("utf-8")
                                df = pd.read_csv(io.StringIO(csv_data))
                                # Filter for our symbol
                                df.columns = [c.strip() for c in df.columns]
                                sym_col = None
                                for c in df.columns:
                                    if "SYMBOL" in c.upper() or "TckrSymb" in c:
                                        sym_col = c
                                        break
                                if sym_col and symbol in df[sym_col].values:
                                    row = df[df[sym_col] == symbol].iloc[0]
                                    all_rows.append(self._extract_row(row, current))
                elif resp.status_code != 404:
                    logger.debug(f"Bhavcopy {date_str}: HTTP {resp.status_code}")
            except Exception as e:
                logger.debug(f"Bhavcopy {date_str} failed: {e}")

            current += timedelta(days=1)

        if not all_rows:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        return pd.DataFrame(all_rows).sort_values("timestamp").reset_index(drop=True)

    def _extract_row(self, row, date: datetime) -> dict:
        """Extract OHLCV from a bhavcopy CSV row."""
        # Column names vary across bhavcopy formats
        def get_val(row, candidates, default=0):
            for c in candidates:
                if c in row.index:
                    try:
                        return float(row[c])
                    except (ValueError, TypeError):
                        continue
            return default

        return {
            "timestamp": pd.Timestamp(date),
            "open": get_val(row, ["OpnPric", "OPEN_PRICE", "OPEN", "open"]),
            "high": get_val(row, ["HghPric", "HIGH_PRICE", "HIGH", "high"]),
            "low": get_val(row, ["LwPric", "LOW_PRICE", "LOW", "low"]),
            "close": get_val(row, ["ClsPric", "CLOSE_PRICE", "CLOSE", "close"]),
            "volume": int(get_val(row, ["TtlTradgVol", "TTL_TRD_QNTY", "VOLUME", "volume"])),
        }

    def test_connection(self) -> dict:
        try:
            session = self._get_session()
            self._rate_limit()
            resp = session.get("https://www.nseindia.com/", timeout=10)
            if resp.status_code == 200:
                return {"status": "ok", "message": "NSE India reachable (Bhavcopy fallback ready)", "provider": "nse-bhavcopy"}
            return {"status": "error", "message": f"HTTP {resp.status_code}", "provider": "nse-bhavcopy"}
        except Exception as e:
            return {"status": "error", "message": str(e), "provider": "nse-bhavcopy"}
