"""Brokerage and transaction cost model for Indian equity markets.

Default: Zerodha-like flat brokerage + statutory charges.
"""

from dataclasses import dataclass


@dataclass
class CostConfig:
    """Transaction cost configuration."""
    slippage_pct: float = 0.05       # 0.05% default slippage per side
    brokerage_per_order: float = 20  # Rs 20 flat per order (Zerodha)
    stt_delivery_pct: float = 0.1    # STT 0.1% sell-side for delivery
    stt_intraday_pct: float = 0.025  # STT 0.025% sell-side for intraday
    exchange_charges_pct: float = 0.00345  # NSE transaction charges
    is_intraday: bool = False


def apply_slippage(price: float, slippage_pct: float, is_entry: bool) -> float:
    """Apply slippage to a price. Entry: price goes up. Exit: price goes down."""
    if is_entry:
        return price * (1 + slippage_pct / 100)
    else:
        return price * (1 - slippage_pct / 100)


def calculate_trade_costs(
    entry_price: float,
    exit_price: float,
    quantity: int,
    config: CostConfig,
) -> dict:
    """Calculate all transaction costs for a single round-trip trade.

    Returns dict with individual cost components and total.
    """
    buy_value = entry_price * quantity
    sell_value = exit_price * quantity

    # Brokerage: flat per order, 2 orders per round trip
    brokerage = config.brokerage_per_order * 2

    # STT: sell-side only
    stt_rate = config.stt_intraday_pct if config.is_intraday else config.stt_delivery_pct
    stt = sell_value * (stt_rate / 100)

    # Exchange charges: both sides
    exchange = (buy_value + sell_value) * (config.exchange_charges_pct / 100)

    # SEBI charges: 0.0001% (negligible but included for completeness)
    sebi = (buy_value + sell_value) * 0.000001

    # GST on brokerage + exchange charges (18%)
    gst = (brokerage + exchange) * 0.18

    # Stamp duty: 0.015% buy-side for delivery, 0.003% for intraday
    stamp_rate = 0.003 if config.is_intraday else 0.015
    stamp = buy_value * (stamp_rate / 100)

    total = round(brokerage + stt + exchange + sebi + gst + stamp, 2)

    return {
        "brokerage": round(brokerage, 2),
        "stt": round(stt, 2),
        "exchange_charges": round(exchange, 2),
        "gst": round(gst, 2),
        "stamp_duty": round(stamp, 2),
        "sebi_charges": round(sebi, 4),
        "total": total,
    }


def calculate_all_costs(
    trades: list,
    initial_capital: float,
    config: CostConfig,
) -> dict:
    """Calculate aggregate costs for all trades.

    trades: list of trade dicts with entry_price, exit_price.
    Returns summary with per-trade and total costs.
    """
    if not trades:
        return {
            "total_costs": 0,
            "total_brokerage": 0,
            "total_stt": 0,
            "total_exchange": 0,
            "total_gst": 0,
            "total_stamp": 0,
            "cost_per_trade_avg": 0,
            "costs_as_pct_of_capital": 0,
            "config": {
                "slippage_pct": config.slippage_pct,
                "brokerage_per_order": config.brokerage_per_order,
                "stt_rate_pct": config.stt_intraday_pct if config.is_intraday else config.stt_delivery_pct,
                "exchange_charges_pct": config.exchange_charges_pct,
                "is_intraday": config.is_intraday,
            },
        }

    totals = {
        "brokerage": 0, "stt": 0, "exchange_charges": 0,
        "gst": 0, "stamp_duty": 0, "total": 0,
    }

    # Estimate quantity per trade based on capital allocation (full capital per trade)
    for t in trades:
        entry_price = t["entry_price"]
        if entry_price <= 0:
            continue
        qty = max(1, int(initial_capital / entry_price))
        costs = calculate_trade_costs(entry_price, t["exit_price"], qty, config)
        for k in totals:
            totals[k] += costs.get(k, 0)

    return {
        "total_costs": round(totals["total"], 2),
        "total_brokerage": round(totals["brokerage"], 2),
        "total_stt": round(totals["stt"], 2),
        "total_exchange": round(totals["exchange_charges"], 2),
        "total_gst": round(totals["gst"], 2),
        "total_stamp": round(totals["stamp_duty"], 2),
        "cost_per_trade_avg": round(totals["total"] / len(trades), 2),
        "costs_as_pct_of_capital": round((totals["total"] / initial_capital) * 100, 2),
        "config": {
            "slippage_pct": config.slippage_pct,
            "brokerage_per_order": config.brokerage_per_order,
            "stt_rate_pct": config.stt_intraday_pct if config.is_intraday else config.stt_delivery_pct,
            "exchange_charges_pct": config.exchange_charges_pct,
            "is_intraday": config.is_intraday,
        },
    }
