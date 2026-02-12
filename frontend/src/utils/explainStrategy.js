export function explainStrategy(strategy) {
  const lines = [];
  const { metadata, market, instrument, timeframe, entry_conditions, exit_conditions, risk_management } = strategy;

  // Header
  lines.push(`Strategy: ${metadata?.name || "Unnamed"}`);
  
  // Market info
  if (market?.type && instrument?.symbol) {
    lines.push(`Trade ${instrument.symbol} on ${market.exchange || market.type}.`);
  }

  // Timeframe
  if (timeframe?.interval) {
    lines.push(`Using ${timeframe.interval} candles.`);
  }

  // Entry conditions (RSI)
  const entryRSI = entry_conditions?.find(c => c.name === "RSI");
  if (entryRSI) {
    const period = entryRSI.params?.period || 14;
    const op = formatOperator(entryRSI.operator);
    lines.push(`Enter when RSI(${period}) is ${op} ${entryRSI.value}.`);
  }

  // Exit conditions (RSI)
  const exitRSI = exit_conditions?.find(c => c.name === "RSI");
  if (exitRSI) {
    const period = exitRSI.params?.period || 14;
    const op = formatOperator(exitRSI.operator);
    lines.push(`Exit when RSI(${period}) is ${op} ${exitRSI.value}.`);
  }

  // Risk management
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
