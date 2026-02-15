INDICATOR_REGISTRY = {
    "RSI": {
        "params": {"period": int},
        "operators": [">", "<", ">=", "<=", "==", "crosses_above", "crosses_below"],
        "has_value": True
    },
    "SMA": {
        "params": {"short": int, "long": int},
        "operators": ["crosses_above", "crosses_below"],
        "has_value": False
    },
    "EMA": {
        "params": {"short": int, "long": int},
        "operators": ["crosses_above", "crosses_below"],
        "has_value": False
    },
    "MACD": {
        "params": {"fast": int, "slow": int, "signal": int},
        "operators": ["bullish_cross", "bearish_cross"],
        "has_value": False
    }
}

def validate_strategy_json(data):
    if not isinstance(data, dict):
        return False
    
    # Check required fields
    required = ["entry_conditions", "risk_management"]
    for field in required:
        if field not in data:
            return False
    
    # Check entry_conditions not empty
    if not data.get("entry_conditions"):
        return False
    
    # Validate conditions
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
    
    # Check indicator exists in registry
    name = cond.get("name")
    if name not in INDICATOR_REGISTRY:
        return False
    
    registry = INDICATOR_REGISTRY[name]
    
    # Check operator allowed
    operator = cond.get("operator")
    if operator not in registry["operators"]:
        return False
    
    # Check params allowed
    params = cond.get("params", {})
    allowed_params = registry["params"]
    
    for key, val in params.items():
        if key not in allowed_params:
            return False
        expected_type = allowed_params[key]
        if not isinstance(val, expected_type):
            return False
    
    return True
