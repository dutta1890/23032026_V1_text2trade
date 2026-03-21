"""Strategy Optimizer Engine — parameter sweep with ranked backtest results."""
import copy
import itertools
import logging
import time
from typing import List, Dict, Any, Optional

from backtest.engine import run_backtest

logger = logging.getLogger(__name__)

MAX_COMBINATIONS = 500
DEFAULT_STEPS = 5


def _linspace(start: float, end: float, steps: int) -> List[float]:
    if steps <= 1:
        return [start]
    step_size = (end - start) / (steps - 1)
    return [round(start + i * step_size, 4) for i in range(steps)]


def _detect_tunable_params(strategy: dict) -> List[Dict[str, Any]]:
    """Auto-detect tunable parameters from a strategy."""
    tunables = []

    # Entry/exit condition params
    for cond_key in ("entry_conditions", "exit_conditions"):
        for i, cond in enumerate(strategy.get(cond_key, [])):
            name = cond.get("name", "")
            params = cond.get("params", {})
            value = cond.get("value")

            # Tunable: indicator params (period, short, long, etc.)
            for pk, pv in params.items():
                if isinstance(pv, (int, float)) and pv > 0:
                    lo = max(2, round(pv * 0.5))
                    hi = round(pv * 2.0)
                    tunables.append({
                        "path": f"{cond_key}[{i}].params.{pk}",
                        "label": f"{name} {pk}",
                        "current": pv,
                        "min": lo, "max": hi,
                        "step_type": "int" if isinstance(pv, int) else "float",
                    })

            # Tunable: threshold value
            if value is not None and isinstance(value, (int, float)):
                lo = max(0, round(value * 0.5, 2))
                hi = round(value * 1.5, 2)
                tunables.append({
                    "path": f"{cond_key}[{i}].value",
                    "label": f"{name} threshold",
                    "current": value,
                    "min": lo, "max": hi,
                    "step_type": "float",
                })

    # Risk management params
    rm = strategy.get("risk_management", {})
    sl = rm.get("stop_loss")
    if sl and isinstance(sl, dict) and sl.get("value"):
        v = sl["value"]
        tunables.append({
            "path": "risk_management.stop_loss.value",
            "label": "Stop Loss %",
            "current": v,
            "min": max(0.5, round(v * 0.5, 1)),
            "max": round(v * 2.5, 1),
            "step_type": "float",
        })

    tp = rm.get("target_profit")
    if tp and isinstance(tp, dict) and tp.get("value"):
        v = tp["value"]
        tunables.append({
            "path": "risk_management.target_profit.value",
            "label": "Target Profit %",
            "current": v,
            "min": max(0.5, round(v * 0.5, 1)),
            "max": round(v * 2.5, 1),
            "step_type": "float",
        })

    tsl = rm.get("trailing_stop_loss")
    if tsl and isinstance(tsl, dict) and tsl.get("enabled") and tsl.get("value"):
        v = tsl["value"]
        tunables.append({
            "path": "risk_management.trailing_stop_loss.value",
            "label": "Trailing SL %",
            "current": v,
            "min": max(0.3, round(v * 0.5, 1)),
            "max": round(v * 2.5, 1),
            "step_type": "float",
        })

    return tunables


def _set_nested(obj: dict, path: str, value) -> dict:
    """Set a nested value in a dict using dot/bracket notation."""
    parts = []
    current = path
    while current:
        if "[" in current:
            idx_start = current.index("[")
            if idx_start > 0:
                parts.append(("key", current[:idx_start]))
            idx_end = current.index("]")
            parts.append(("index", int(current[idx_start+1:idx_end])))
            current = current[idx_end+1:]
            if current.startswith("."):
                current = current[1:]
        elif "." in current:
            dot_idx = current.index(".")
            parts.append(("key", current[:dot_idx]))
            current = current[dot_idx+1:]
        else:
            parts.append(("key", current))
            current = ""

    ref = obj
    for i, (ptype, pval) in enumerate(parts[:-1]):
        if ptype == "key":
            ref = ref[pval]
        else:
            ref = ref[pval]

    last_type, last_val = parts[-1]
    if last_type == "key":
        ref[last_val] = value
    else:
        ref[last_val] = value
    return obj


def _get_nested(obj: dict, path: str):
    """Get a nested value from a dict using dot/bracket notation."""
    parts = []
    current = path
    while current:
        if "[" in current:
            idx_start = current.index("[")
            if idx_start > 0:
                parts.append(("key", current[:idx_start]))
            idx_end = current.index("]")
            parts.append(("index", int(current[idx_start+1:idx_end])))
            current = current[idx_end+1:]
            if current.startswith("."):
                current = current[1:]
        elif "." in current:
            dot_idx = current.index(".")
            parts.append(("key", current[:dot_idx]))
            current = current[dot_idx+1:]
        else:
            parts.append(("key", current))
            current = ""

    ref = obj
    for ptype, pval in parts:
        if ptype == "key":
            ref = ref[pval]
        else:
            ref = ref[pval]
    return ref


def run_optimization(
    strategy: dict,
    param_ranges: List[Dict[str, Any]],
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    initial_capital: float = 100000,
    max_combos: int = MAX_COMBINATIONS,
) -> Dict[str, Any]:
    """
    Run a parameter sweep optimization.

    param_ranges: list of {path, min, max, steps}
    Returns ranked results with baseline comparison.
    """
    start_time = time.time()
    sym = symbol or strategy.get("instrument", {}).get("symbol", "RELIANCE")
    tf = timeframe or strategy.get("timeframe", {}).get("interval", "1d")

    # Generate value grids for each param
    grids = []
    param_labels = []
    for pr in param_ranges:
        steps = pr.get("steps", DEFAULT_STEPS)
        lo, hi = pr["min"], pr["max"]
        step_type = pr.get("step_type", "float")
        values = _linspace(lo, hi, steps)
        if step_type == "int":
            values = sorted(set(int(round(v)) for v in values))
        grids.append(values)
        param_labels.append({
            "path": pr["path"],
            "label": pr.get("label", pr["path"]),
            "values": values,
        })

    # Generate combinations (capped)
    all_combos = list(itertools.product(*grids))
    total_possible = len(all_combos)
    if len(all_combos) > max_combos:
        # Sample evenly
        step = len(all_combos) / max_combos
        indices = [int(i * step) for i in range(max_combos)]
        all_combos = [all_combos[i] for i in indices]

    logger.info(f"Optimizer: {len(all_combos)} combinations (of {total_possible} possible) for {sym}/{tf}")

    # Run baseline first
    baseline_result = run_backtest(strategy, symbol=sym, timeframe=tf, initial_capital=initial_capital)
    baseline_metrics = baseline_result.get("metrics", {})

    # Run all combinations
    results = []
    errors = 0
    for combo_idx, combo in enumerate(all_combos):
        strat_copy = copy.deepcopy(strategy)
        param_values = {}
        for i, pr in enumerate(param_ranges):
            val = combo[i]
            if pr.get("step_type") == "int":
                val = int(round(val))
            _set_nested(strat_copy, pr["path"], val)
            param_values[pr.get("label", pr["path"])] = val

        try:
            bt = run_backtest(strat_copy, symbol=sym, timeframe=tf, initial_capital=initial_capital)
            m = bt.get("metrics", {})
            results.append({
                "params": param_values,
                "sharpe": m.get("sharpe_ratio") or 0,
                "pnl_pct": m.get("total_pnl_pct") or 0,
                "win_rate": m.get("win_rate") or 0,
                "max_drawdown": m.get("max_drawdown_pct") or 0,
                "total_trades": m.get("total_trades") or 0,
                "profit_factor": m.get("profit_factor") or 0,
                "avg_pnl": m.get("avg_pnl_per_trade") or 0,
                "success": True,
            })
        except Exception as e:
            errors += 1
            results.append({
                "params": param_values,
                "sharpe": 0, "pnl_pct": 0, "win_rate": 0,
                "max_drawdown": 0, "total_trades": 0,
                "profit_factor": 0, "avg_pnl": 0,
                "success": False, "error": str(e),
            })

    # Sort by Sharpe (primary), then P&L (secondary)
    results.sort(key=lambda r: (r["sharpe"], r["pnl_pct"]), reverse=True)

    # Add rank
    for i, r in enumerate(results):
        r["rank"] = i + 1

    # Compute parameter impact (variance of Sharpe per parameter)
    param_impact = []
    for i, pr in enumerate(param_ranges):
        label = pr.get("label", pr["path"])
        values = param_labels[i]["values"]
        # Group results by this param's value
        groups = {}
        for r in results:
            if not r["success"]:
                continue
            pval = r["params"].get(label)
            if pval not in groups:
                groups[pval] = []
            groups[pval].append(r["sharpe"])

        # Calculate avg sharpe per value
        avg_sharpes = {}
        for val, sharpes in groups.items():
            avg_sharpes[val] = sum(sharpes) / len(sharpes) if sharpes else 0

        if avg_sharpes:
            all_avg = list(avg_sharpes.values())
            impact = max(all_avg) - min(all_avg) if len(all_avg) > 1 else 0
        else:
            impact = 0

        param_impact.append({
            "label": label,
            "path": pr["path"],
            "impact_score": round(impact, 4),
            "best_value": max(avg_sharpes, key=avg_sharpes.get) if avg_sharpes else None,
            "value_sharpes": {str(k): round(v, 4) for k, v in avg_sharpes.items()},
        })

    param_impact.sort(key=lambda x: x["impact_score"], reverse=True)

    # Overfitting warnings
    warnings = []
    if results and results[0]["success"]:
        best = results[0]
        if best["total_trades"] < 5:
            warnings.append("Best combination has very few trades (<5). Results may not be statistically significant.")
        if best["sharpe"] > 3.0:
            warnings.append("Unusually high Sharpe ratio (>3.0). Possible overfitting to historical data.")
        if best["total_trades"] < baseline_metrics.get("total_trades", 0) * 0.3:
            warnings.append("Best combo trades much less frequently. It may be over-filtering signals.")

    elapsed = round(time.time() - start_time, 2)

    return {
        "success": True,
        "symbol": sym,
        "timeframe": tf,
        "total_combinations": len(all_combos),
        "total_possible": total_possible,
        "successful_runs": len([r for r in results if r["success"]]),
        "errors": errors,
        "elapsed_seconds": elapsed,
        "baseline": {
            "sharpe": baseline_metrics.get("sharpe_ratio") or 0,
            "pnl_pct": baseline_metrics.get("total_pnl_pct") or 0,
            "win_rate": baseline_metrics.get("win_rate") or 0,
            "max_drawdown": baseline_metrics.get("max_drawdown_pct") or 0,
            "total_trades": baseline_metrics.get("total_trades") or 0,
            "profit_factor": baseline_metrics.get("profit_factor") or 0,
        },
        "results": results[:50],  # Top 50 only
        "param_impact": param_impact,
        "param_labels": param_labels,
        "warnings": warnings,
    }
