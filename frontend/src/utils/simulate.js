export function simulate(strategy) {
  const numTrades = 10 + Math.floor(Math.random() * 20);
  const trades = [];
  let wins = 0;
  let totalPnl = 0;

  const symbol = strategy.instrument?.symbol || "UNKNOWN";
  const sl = strategy.risk_management?.stop_loss || 2;
  const tp = strategy.risk_management?.take_profit || 5;

  for (let i = 0; i < numTrades; i++) {
    const isWin = Math.random() > 0.45;
    const pnl = isWin ? (Math.random() * tp) : -(Math.random() * sl);
    const entry = 100 + Math.random() * 50;
    const exit = entry * (1 + pnl / 100);

    if (isWin) wins++;
    totalPnl += pnl;

    trades.push({
      id: i + 1,
      symbol,
      entry: parseFloat(entry.toFixed(2)),
      exit: parseFloat(exit.toFixed(2)),
      pnl: parseFloat(pnl.toFixed(2)),
      result: isWin ? "WIN" : "LOSS",
      date: randomDate()
    });
  }

  return {
    label: "Simulated",
    trades,
    win_rate: parseFloat(((wins / numTrades) * 100).toFixed(1)),
    pnl: parseFloat(totalPnl.toFixed(2)),
    total_trades: numTrades,
    wins,
    losses: numTrades - wins
  };
}

function randomDate() {
  const start = new Date(2025, 0, 1);
  const end = new Date();
  const d = new Date(start.getTime() + Math.random() * (end.getTime() - start.getTime()));
  return d.toISOString().split("T")[0];
}
