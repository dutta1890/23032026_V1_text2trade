INDICATORS = {
    "RSI": {
        "params": ["period", "overbought", "oversold"],
        "operators": ["<", ">", "cross"]
    },
    "SMA": {
        "params": ["period", "short", "long"],
        "operators": ["cross_above", "cross_below"]
    },
    "EMA": {
        "params": ["period", "short", "long"],
        "operators": ["cross_above", "cross_below"]
    },
    "MACD": {
        "params": ["fast", "slow", "signal"],
        "operators": ["bullish_cross", "bearish_cross"]
    },
    "Stochastic": {
        "params": ["k_period", "d_period", "overbought", "oversold"],
        "operators": ["cross_above", "cross_below"]
    },
    "ADX": {
        "params": ["period"],
        "operators": [">", "<"]
    },
    "ATR": {
        "params": ["period"],
        "operators": ["atr_multiple"]
    }
}

def validate_strategy_json(data):
    # check required fields
    if not isinstance(data, dict):
        return False
    if "entry_conditions" not in data:
        return False
    if "risk_management" not in data:
        return False
    if not data.get("entry_conditions"):
        return False
    
    # check indicator exists in registry
    # check params allowed
    for cond in data.get("entry_conditions", []):
        if not validate_condition(cond):
            return False
    for cond in data.get("exit_conditions", []):
        if not validate_condition(cond):
            return False
    for cond in data.get("filters", []):
        if not validate_condition(cond):
            return False
    
    # return True/False
    return True


def validate_condition(cond):
    # check indicator exists in registry
    name = cond.get("name")
    if name not in INDICATORS:
        return False
    
    # check operator allowed
    if cond.get("operator") not in INDICATORS[name]["operators"]:
        return False
    
    # check params allowed
    for key in cond.get("params", {}).keys():
        if key not in INDICATORS[name]["params"]:
            return False
    
    return True
