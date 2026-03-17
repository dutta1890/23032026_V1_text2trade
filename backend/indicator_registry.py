INDICATORS = {
    "RSI": {
        "params": ["period"],
        "operators": ["<", ">", ">=", "<=", "cross_above", "cross_below"]
    },
    "SMA": {
        "params": ["period", "short", "long"],
        "operators": ["<", ">", "cross_above", "cross_below", "crosses_above", "crosses_below"]
    },
    "EMA": {
        "params": ["period", "short", "long"],
        "operators": ["<", ">", "cross_above", "cross_below", "crosses_above", "crosses_below"]
    },
    "MACD": {
        "params": ["fast", "slow", "signal"],
        "operators": ["bullish_cross", "bearish_cross"]
    },
    "Bollinger": {
        "params": ["period", "std_dev"],
        "operators": [">", "<", ">=", "<=", "upper_touch", "lower_touch"]
    },
    "Stochastic": {
        "params": ["k_period", "d_period"],
        "operators": ["<", ">", "cross_above", "cross_below", "crosses_above", "crosses_below"]
    },
    "ADX": {
        "params": ["period"],
        "operators": [">", "<", ">=", "<="]
    },
    "ATR": {
        "params": ["period"],
        "operators": [">", "<", ">=", "<=", "atr_multiple"]
    },
    "Supertrend": {
        "params": ["period", "multiplier"],
        "operators": ["buy_signal", "sell_signal", ">", "<"]
    },
    "VWAP": {
        "params": [],
        "operators": [">", "<", "cross_above", "cross_below"]
    },
    "PivotPoints": {
        "params": ["method"],
        "operators": [">", "<", ">=", "<=", "above_r1", "below_s1", "above_r2", "below_s2"]
    },
    "PSAR": {
        "params": ["af_start", "af_increment", "af_max"],
        "operators": [">", "<", "cross_above", "cross_below"]
    },
    "CCI": {
        "params": ["period"],
        "operators": [">", "<", ">=", "<=", "cross_above", "cross_below"]
    },
    "WilliamsR": {
        "params": ["period"],
        "operators": [">", "<", ">=", "<=", "cross_above", "cross_below"]
    },
    "OBV": {
        "params": [],
        "operators": [">", "<", "cross_above", "cross_below"]
    },
}


def validate_strategy_json(data):
    if not isinstance(data, dict):
        return False
    if "entry_conditions" not in data:
        return False
    if "risk_management" not in data:
        return False
    if not data.get("entry_conditions"):
        return False

    for cond in data.get("entry_conditions", []):
        if not validate_condition(cond):
            return False
    for cond in data.get("exit_conditions", []):
        if not validate_condition(cond):
            return False
    for cond in data.get("filters", []):
        if not validate_condition(cond):
            return False

    return True


def validate_condition(cond):
    name = cond.get("name")
    if name not in INDICATORS:
        return False
    if cond.get("operator") not in INDICATORS[name]["operators"]:
        return False
    for key in cond.get("params", {}).keys():
        if key not in INDICATORS[name]["params"]:
            return False
    return True
