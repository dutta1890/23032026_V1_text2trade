export function explainStrategy(strategy) {
  const lines = [];
  const { metadata, market, instrument, timeframe, entry_conditions, exit_conditions, risk_management } = strategy;

  lines.push(`Strategy: ${metadata?.name || "Unnamed"}`);
  
  if (market?.type && instrument?.symbol) {
    lines.push(`Trade ${instrument.symbol} on ${market.exchange || market.type}.`);
  }

  if (timeframe?.interval) {
    lines.push(`Using ${timeframe.interval} candles.`);
  }

  const formatCondition = (c, action) => {
    const op = formatOperator(c.operator);
    if (c.name === "RSI") {
      const period = c.params?.period || 14;
      return `${action} when RSI(${period}) is ${op} ${c.value}.`;
    } else if (c.name === "SMA" || c.name === "EMA") {
      const short = c.params?.short || c.params?.period || 9;
      const long = c.params?.long || 21;
      return `${action} when ${c.name}(${short}/${long}) ${op} price.`;
    } else if (c.name === "MACD") {
      const fast = c.params?.fast || 12;
      const slow = c.params?.slow || 26;
      const signal = c.params?.signal || 9;
      return `${action} on MACD(${fast}/${slow}/${signal}) ${op}.`;
    } else if (c.name === "Stochastic") {
      const k = c.params?.k_period || 14;
      const d = c.params?.d_period || 3;
      return `${action} when Stoch(%K${k}/%D${d}) ${op} ${c.value || ""}.`;
    }
    return `${action} on ${c.name} ${op}.`;
  };

  const formatFilter = (c) => {
    const op = formatOperator(c.operator);
    if (c.name === "ADX") {
      const period = c.params?.period || 14;
      return `Filter: ADX(${period}) ${op} ${c.value}.`;
    }
    return `Filter: ${c.name} ${op} ${c.value}.`;
  };

  entry_conditions?.forEach(c => lines.push(formatCondition(c, "Enter")));
  exit_conditions?.forEach(c => lines.push(formatCondition(c, "Exit")));
  strategy.filters?.forEach(c => lines.push(formatFilter(c)));

  if (risk_management?.stop_loss) {
    if (risk_management.stop_loss_type === "atr_multiple") {
      const atrPeriod = risk_management.stop_loss_atr_period || 14;
      lines.push(`Stop loss at ${risk_management.stop_loss}x ATR(${atrPeriod}).`);
    } else {
      lines.push(`Stop loss at ${risk_management.stop_loss}%.`);
    }
  }
  if (risk_management?.take_profit) {
    lines.push(`Take profit at ${risk_management.take_profit}%.`);
  }

  return lines.join(" ");
}

function formatOperator(op) {
  const map = {
    ">": "above",
    "<": "below",
    ">=": "at or above",
    "<=": "at or below",
    "==": "equal to",
    "crosses_above": "crossing above",
    "crosses_below": "crossing below",
    "bullish_cross": "bullish cross",
    "bearish_cross": "bearish cross"
  };
  return map[op] || op;
}
