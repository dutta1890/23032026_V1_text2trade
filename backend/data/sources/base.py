"""Abstract base class for all market data sources."""

from abc import ABC, abstractmethod
from datetime import datetime
import pandas as pd


class MarketDataSource(ABC):
    @abstractmethod
    def fetch_historical(self, symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Returns DataFrame with columns: timestamp, open, high, low, close, volume"""

    @abstractmethod
    def test_connection(self) -> dict:
        """Returns { 'status': 'ok'|'error', 'message': str, 'provider': str }"""
