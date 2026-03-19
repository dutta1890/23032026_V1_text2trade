"""Seed 12 equity strategy templates into strategy_templates collection."""

import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "test_database")

TEMPLATES = [
    {
        "template_id": str(uuid.uuid4()),
        "name": "Golden Cross",
        "description": "Classic trend-following strategy. Buy when 50-day SMA crosses above 200-day SMA (golden cross), sell on the death cross.",
        "category": "Trend",
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": {"symbol": "RELIANCE", "base": None, "quote": None},
        "timeframe": {"interval": "1d", "candle_count": None},
        "entry_conditions": [
            {"name": "SMA", "params": {"short": 50, "long": 200}, "operator": "crosses_above"}
        ],
        "exit_conditions": [
            {"name": "SMA", "params": {"short": 50, "long": 200}, "operator": "crosses_below"}
        ],
        "filters": [],
        "risk_management": {
            "stop_loss": {"type": "percentage", "value": 3.0},
            "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
            "target_profit": None,
            "time_based_exit": {"enabled": False, "exit_time": "15:10"},
            "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
            "position_sizing": {"method": "fixed_quantity", "value": 1},
        },
    },
    {
        "template_id": str(uuid.uuid4()),
        "name": "RSI Mean Reversion",
        "description": "Buy oversold stocks when RSI drops below 30, sell when overbought above 70. Classic mean reversion play.",
        "category": "Mean Reversion",
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": {"symbol": "RELIANCE", "base": None, "quote": None},
        "timeframe": {"interval": "1d", "candle_count": None},
        "entry_conditions": [
            {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
        ],
        "exit_conditions": [
            {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}
        ],
        "filters": [],
        "risk_management": {
            "stop_loss": {"type": "percentage", "value": 2.0},
            "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
            "target_profit": None,
            "time_based_exit": {"enabled": False, "exit_time": "15:10"},
            "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
            "position_sizing": {"method": "fixed_quantity", "value": 1},
        },
    },
    {
        "template_id": str(uuid.uuid4()),
        "name": "Supertrend Follower",
        "description": "Ride the trend using Supertrend indicator. Enter on buy signal, exit on sell signal with trailing stop.",
        "category": "Trend",
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": {"symbol": "RELIANCE", "base": None, "quote": None},
        "timeframe": {"interval": "1d", "candle_count": None},
        "entry_conditions": [
            {"name": "Supertrend", "params": {"period": 10, "multiplier": 3.0}, "operator": "buy_signal"}
        ],
        "exit_conditions": [
            {"name": "Supertrend", "params": {"period": 10, "multiplier": 3.0}, "operator": "sell_signal"}
        ],
        "filters": [],
        "risk_management": {
            "stop_loss": None,
            "trailing_stop_loss": {"enabled": True, "type": "percentage", "value": 1.5, "activation_profit": 0},
            "target_profit": None,
            "time_based_exit": {"enabled": False, "exit_time": "15:10"},
            "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
            "position_sizing": {"method": "fixed_quantity", "value": 1},
        },
    },
    {
        "template_id": str(uuid.uuid4()),
        "name": "MACD Momentum",
        "description": "Catch momentum with MACD bullish crossover, confirmed by strong trend (ADX > 25). Exit on bearish cross.",
        "category": "Momentum",
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": {"symbol": "RELIANCE", "base": None, "quote": None},
        "timeframe": {"interval": "1d", "candle_count": None},
        "entry_conditions": [
            {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "bullish_cross"}
        ],
        "exit_conditions": [
            {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "bearish_cross"}
        ],
        "filters": [
            {"name": "ADX", "params": {"period": 14}, "operator": ">", "value": 25}
        ],
        "risk_management": {
            "stop_loss": {"type": "percentage", "value": 2.5},
            "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
            "target_profit": None,
            "time_based_exit": {"enabled": False, "exit_time": "15:10"},
            "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
            "position_sizing": {"method": "fixed_quantity", "value": 1},
        },
    },
    {
        "template_id": str(uuid.uuid4()),
        "name": "Bollinger Bounce",
        "description": "Buy when price touches lower Bollinger Band with RSI confirming oversold. Exit on upper band touch.",
        "category": "Mean Reversion",
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": {"symbol": "RELIANCE", "base": None, "quote": None},
        "timeframe": {"interval": "1d", "candle_count": None},
        "entry_conditions": [
            {"name": "Bollinger", "params": {"period": 20, "std_dev": 2}, "operator": "lower_touch"}
        ],
        "exit_conditions": [
            {"name": "Bollinger", "params": {"period": 20, "std_dev": 2}, "operator": "upper_touch"}
        ],
        "filters": [
            {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 35}
        ],
        "risk_management": {
            "stop_loss": {"type": "percentage", "value": 2.0},
            "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
            "target_profit": None,
            "time_based_exit": {"enabled": False, "exit_time": "15:10"},
            "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
            "position_sizing": {"method": "fixed_quantity", "value": 1},
        },
    },
    {
        "template_id": str(uuid.uuid4()),
        "name": "VWAP Intraday",
        "description": "Intraday strategy using VWAP. Buy when price crosses above VWAP, exit on cross below or at 15:10.",
        "category": "Intraday",
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": {"symbol": "RELIANCE", "base": None, "quote": None},
        "timeframe": {"interval": "15m", "candle_count": None},
        "entry_conditions": [
            {"name": "VWAP", "params": {}, "operator": "cross_above"}
        ],
        "exit_conditions": [
            {"name": "VWAP", "params": {}, "operator": "cross_below"}
        ],
        "filters": [],
        "risk_management": {
            "stop_loss": {"type": "percentage", "value": 1.0},
            "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
            "target_profit": None,
            "time_based_exit": {"enabled": True, "exit_time": "15:10"},
            "daily_limits": {"max_loss_per_day": 3.0, "max_trades_per_day": 5},
            "position_sizing": {"method": "fixed_quantity", "value": 1},
        },
    },
    {
        "template_id": str(uuid.uuid4()),
        "name": "Pivot Breakout",
        "description": "Breakout strategy using Pivot Points. Buy above R1, exit below S1. Works on daily charts.",
        "category": "Breakout",
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": {"symbol": "RELIANCE", "base": None, "quote": None},
        "timeframe": {"interval": "1d", "candle_count": None},
        "entry_conditions": [
            {"name": "PivotPoints", "params": {"method": "standard"}, "operator": "above_r1"}
        ],
        "exit_conditions": [
            {"name": "PivotPoints", "params": {"method": "standard"}, "operator": "below_s1"}
        ],
        "filters": [],
        "risk_management": {
            "stop_loss": {"type": "percentage", "value": 1.5},
            "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
            "target_profit": None,
            "time_based_exit": {"enabled": False, "exit_time": "15:10"},
            "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
            "position_sizing": {"method": "fixed_quantity", "value": 1},
        },
    },
    {
        "template_id": str(uuid.uuid4()),
        "name": "Stochastic Reversal",
        "description": "Mean reversion using Stochastic oscillator. Buy when %K crosses above %D in oversold zone (< 20).",
        "category": "Mean Reversion",
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": {"symbol": "RELIANCE", "base": None, "quote": None},
        "timeframe": {"interval": "1d", "candle_count": None},
        "entry_conditions": [
            {"name": "Stochastic", "params": {"k_period": 14, "d_period": 3}, "operator": "cross_above", "value": 20}
        ],
        "exit_conditions": [
            {"name": "Stochastic", "params": {"k_period": 14, "d_period": 3}, "operator": ">", "value": 80}
        ],
        "filters": [],
        "risk_management": {
            "stop_loss": {"type": "percentage", "value": 2.0},
            "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
            "target_profit": None,
            "time_based_exit": {"enabled": False, "exit_time": "15:10"},
            "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
            "position_sizing": {"method": "fixed_quantity", "value": 1},
        },
    },
    {
        "template_id": str(uuid.uuid4()),
        "name": "ATR Volatility",
        "description": "Volatility-based strategy. Buy when close is above EMA(20) with ATR confirming volatility. ATR-based stop loss.",
        "category": "Volatility",
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": {"symbol": "RELIANCE", "base": None, "quote": None},
        "timeframe": {"interval": "1d", "candle_count": None},
        "entry_conditions": [
            {"name": "EMA", "params": {"short": 9, "long": 20}, "operator": "crosses_above"}
        ],
        "exit_conditions": [
            {"name": "EMA", "params": {"short": 9, "long": 20}, "operator": "crosses_below"}
        ],
        "filters": [
            {"name": "ATR", "params": {"period": 14}, "operator": ">", "value": 15}
        ],
        "risk_management": {
            "stop_loss": {"type": "atr_multiple", "value": 1.5},
            "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
            "target_profit": None,
            "time_based_exit": {"enabled": False, "exit_time": "15:10"},
            "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
            "position_sizing": {"method": "fixed_quantity", "value": 1},
        },
    },
    {
        "template_id": str(uuid.uuid4()),
        "name": "CCI Breakout",
        "description": "Momentum breakout using CCI. Buy when CCI crosses above +100 (strong uptrend), exit below -100.",
        "category": "Momentum",
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": {"symbol": "RELIANCE", "base": None, "quote": None},
        "timeframe": {"interval": "1d", "candle_count": None},
        "entry_conditions": [
            {"name": "CCI", "params": {"period": 20}, "operator": "cross_above", "value": 100}
        ],
        "exit_conditions": [
            {"name": "CCI", "params": {"period": 20}, "operator": "<", "value": -100}
        ],
        "filters": [],
        "risk_management": {
            "stop_loss": {"type": "percentage", "value": 3.0},
            "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
            "target_profit": None,
            "time_based_exit": {"enabled": False, "exit_time": "15:10"},
            "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
            "position_sizing": {"method": "fixed_quantity", "value": 1},
        },
    },
    {
        "template_id": str(uuid.uuid4()),
        "name": "Supertrend + RSI",
        "description": "Combined strategy: Supertrend buy signal confirmed by RSI above 50 (momentum filter). Trailing stop for exits.",
        "category": "Combined",
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": {"symbol": "RELIANCE", "base": None, "quote": None},
        "timeframe": {"interval": "1d", "candle_count": None},
        "entry_conditions": [
            {"name": "Supertrend", "params": {"period": 10, "multiplier": 3.0}, "operator": "buy_signal"}
        ],
        "exit_conditions": [
            {"name": "Supertrend", "params": {"period": 10, "multiplier": 3.0}, "operator": "sell_signal"}
        ],
        "filters": [
            {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 50}
        ],
        "risk_management": {
            "stop_loss": None,
            "trailing_stop_loss": {"enabled": True, "type": "percentage", "value": 2.0, "activation_profit": 0},
            "target_profit": None,
            "time_based_exit": {"enabled": False, "exit_time": "15:10"},
            "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
            "position_sizing": {"method": "fixed_quantity", "value": 1},
        },
    },
    {
        "template_id": str(uuid.uuid4()),
        "name": "EMA Ribbon",
        "description": "Trend confirmation using EMA ribbon. Buy when EMA(9) crosses above EMA(21) with EMA(21) > EMA(55) confirming uptrend.",
        "category": "Trend",
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": {"symbol": "RELIANCE", "base": None, "quote": None},
        "timeframe": {"interval": "1d", "candle_count": None},
        "entry_conditions": [
            {"name": "EMA", "params": {"short": 9, "long": 21}, "operator": "crosses_above"}
        ],
        "exit_conditions": [
            {"name": "EMA", "params": {"short": 9, "long": 21}, "operator": "crosses_below"}
        ],
        "filters": [
            {"name": "EMA", "params": {"short": 21, "long": 55}, "operator": "crosses_above"}
        ],
        "risk_management": {
            "stop_loss": {"type": "percentage", "value": 2.5},
            "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
            "target_profit": None,
            "time_based_exit": {"enabled": False, "exit_time": "15:10"},
            "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
            "position_sizing": {"method": "fixed_quantity", "value": 1},
        },
    },
]


def seed_templates():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    col = db.strategy_templates

    now = datetime.now(timezone.utc).isoformat()

    # Clear existing templates
    existing = col.count_documents({})
    if existing > 0:
        col.delete_many({})
        print(f"Cleared {existing} existing templates.")

    for t in TEMPLATES:
        t["created_at"] = now
        t["updated_at"] = now
        t["clone_count"] = 0
        t["is_featured"] = True

    col.insert_many(TEMPLATES)
    col.create_index("template_id", unique=True)
    col.create_index("category")

    print(f"Seeded {len(TEMPLATES)} strategy templates.")
    for t in TEMPLATES:
        print(f"  [{t['category']}] {t['name']} - {t['template_id'][:8]}...")

    client.close()


if __name__ == "__main__":
    seed_templates()
