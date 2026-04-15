"""Benchmark Test Runner — validates the backtest engine against 10 known strategies.

Usage:
    cd /app/backend && python tests/benchmarks/run_benchmarks.py

Loads strategy configs from strategies.json, runs each via the backtest engine,
and validates results against expected ranges.
"""

import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from backtest.engine import run_backtest


def load_benchmark_strategies():
    config_path = Path(__file__).parent / "strategies.json"
    with open(config_path) as f:
        return json.load(f)


def run_single_benchmark(bench):
    """Run a single benchmark and return result dict."""
    strategy_json = bench["strategy"]
    symbol = bench["symbol"]
    timeframe = bench["timeframe"]
    expected = bench["expected"]

    start_time = time.time()
    try:
        result = run_backtest(
            strategy_json, symbol, timeframe,
            slippage_pct=0.05, initial_capital=100000,
        )
    except Exception as e:
        return {
            "id": bench["id"],
            "name": bench["name"],
            "symbol": symbol,
            "category": bench["category"],
            "status": "ERROR",
            "error": str(e),
            "duration_ms": round((time.time() - start_time) * 1000),
            "checks": [],
        }

    duration_ms = round((time.time() - start_time) * 1000)
    checks = []
    all_pass = True

    # Check: success
    passed = bool(result.get("success")) == bool(expected.get("success", True))
    checks.append({"check": "success", "expected": bool(expected.get("success", True)),
                    "actual": bool(result.get("success")), "passed": passed})
    if not passed:
        all_pass = False

    if result.get("success"):
        metrics = result.get("metrics", {})
        total_trades = int(metrics.get("total_trades", 0))
        win_rate = float(metrics.get("win_rate", 0))

        # Check: trade count range
        t_min = expected.get("total_trades_min", 0)
        t_max = expected.get("total_trades_max", 999)
        in_range = t_min <= total_trades <= t_max
        checks.append({
            "check": "total_trades_in_range",
            "expected": f"{t_min}-{t_max}",
            "actual": total_trades,
            "passed": bool(in_range),
        })
        if not in_range:
            all_pass = False

        # Check: win rate range
        wr_min = expected.get("win_rate_min", 0)
        wr_max = expected.get("win_rate_max", 100)
        wr_ok = wr_min <= win_rate <= wr_max
        checks.append({
            "check": "win_rate_in_range",
            "expected": f"{wr_min}-{wr_max}%",
            "actual": f"{win_rate}%",
            "passed": bool(wr_ok),
        })
        if not wr_ok:
            all_pass = False

        # Check: deterministic (run twice, compare)
        result2 = run_backtest(
            strategy_json, symbol, timeframe,
            slippage_pct=0.05, initial_capital=100000,
        )
        m2 = result2.get("metrics", {})
        deterministic = bool(
            metrics.get("total_trades") == m2.get("total_trades")
            and metrics.get("win_rate") == m2.get("win_rate")
            and metrics.get("total_pnl_pct") == m2.get("total_pnl_pct")
        )
        checks.append({"check": "deterministic", "expected": True,
                        "actual": deterministic, "passed": deterministic})
        if not deterministic:
            all_pass = False

        # Check: valid trade chronology
        trades = result.get("trades", [])
        chrono_ok = bool(all(t["entry_time"] <= t["exit_time"] for t in trades))
        checks.append({"check": "chronological_trades", "expected": True,
                        "actual": chrono_ok, "passed": chrono_ok})
        if not chrono_ok:
            all_pass = False

    return {
        "id": bench["id"],
        "name": bench["name"],
        "symbol": symbol,
        "category": bench["category"],
        "description": bench["description"],
        "status": "PASS" if all_pass else "FAIL",
        "duration_ms": duration_ms,
        "checks": checks,
        "total_trades": int(metrics.get("total_trades", 0)) if result.get("success") else 0,
        "win_rate": float(metrics.get("win_rate", 0)) if result.get("success") else 0,
        "total_pnl_pct": float(metrics.get("total_pnl_pct", 0)) if result.get("success") else 0,
    }


def run_all_benchmarks():
    """Run all benchmark strategies and return summary."""
    strategies = load_benchmark_strategies()
    results = []

    for bench in strategies:
        result = run_single_benchmark(bench)
        results.append(result)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    return {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "all_pass": passed == len(results),
        "results": results,
    }


if __name__ == "__main__":
    print("=" * 70)
    print("BENCHMARK TEST RUNNER — Text2trade Backtest Engine")
    print("=" * 70)

    summary = run_all_benchmarks()

    for r in summary["results"]:
        status_icon = "PASS" if r["status"] == "PASS" else "FAIL" if r["status"] == "FAIL" else "ERR "
        print(f"\n[{status_icon}] {r['name']} ({r['symbol']})")
        print(f"       Trades: {r.get('total_trades', '?')} | "
              f"Win Rate: {r.get('win_rate', '?')}% | "
              f"PnL: {r.get('total_pnl_pct', '?')}% | "
              f"Duration: {r['duration_ms']}ms")
        for c in r["checks"]:
            mark = "ok" if c["passed"] else "FAIL"
            print(f"       [{mark}] {c['check']}: expected={c['expected']} actual={c['actual']}")

    print(f"\n{'=' * 70}")
    print(f"SUMMARY: {summary['passed']}/{summary['total']} PASSED, "
          f"{summary['failed']} FAILED, {summary['errors']} ERRORS")
    print(f"{'=' * 70}")

    sys.exit(0 if summary["all_pass"] else 1)
