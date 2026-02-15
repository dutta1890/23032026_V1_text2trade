INDICATORS = {
    "RSI": {
        "params": ["period", "overbought", "oversold"],
        "operators": ["<", ">", "cross"]
    },
    "SMA": {
        "params": ["period"],
        "operators": ["cross_above", "cross_below"]
    },
    "EMA": {
        "params": ["period"],
        "operators": ["cross_above", "cross_below"]
    },
    "MACD": {
        "params": ["fast", "slow", "signal"],
        "operators": ["bullish_cross", "bearish_cross"]
    }
}

def validate_strategy_json(data):
    if not isinstance(data, dict):
        return False
    
    # Check required fields
    if "entry_conditions" not in data:
        return False
    if "risk_management" not in data:
        return False
    
    # Check entry_conditions not empty
    if not data.get("entry_conditions"):
        return False
    
    # Validate all conditions
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
    if not isinstance(cond, dict):
        return False
    
    # Check indicator exists
    name = cond.get("name")
    if name not in INDICATORS:
        return False
    
    indicator = INDICATORS[name]
    
    # Check operator allowed
    operator = cond.get("operator")
    if operator not in indicator["operators"]:
        return False
    
    # Check params allowed
    params = cond.get("params", {})
    allowed_params = indicator["params"]
    
    for key in params.keys():
        if key not in allowed_params:
            return False
    
    return True
