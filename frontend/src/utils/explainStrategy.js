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

  // Entry conditions
  entry_conditions?.forEach(c => {
    const op = formatOperator(c.operator);
    if (c.name === "RSI") {
      const period = c.params?.period || 14;
      lines.push(`Enter when RSI(${period}) is ${op} ${c.value}.`);
    } else if (c.name === "SMA" || c.name === "EMA") {
      const short = c.params?.short || c.params?.period || 9;
      const long = c.params?.long || 21;
      lines.push(`Enter when ${c.name}(${short}/${long}) ${op} price.`);
    }
  });

  // Exit conditions
  exit_conditions?.forEach(c => {
    const op = formatOperator(c.operator);
    if (c.name === "RSI") {
      const period = c.params?.period || 14;
      lines.push(`Exit when RSI(${period}) is ${op} ${c.value}.`);
    } else if (c.name === "SMA" || c.name === "EMA") {
      const short = c.params?.short || c.params?.period || 9;
      const long = c.params?.long || 21;
      lines.push(`Exit when ${c.name}(${short}/${long}) ${op} price.`);
    }
  });

  if (risk_management?.stop_loss) {
    lines.push(`Stop loss at ${risk_management.stop_loss}%.`);
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
    "crosses_below": "crossing below"
  };
  return map[op] || op;
}
