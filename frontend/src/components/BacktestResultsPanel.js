import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell
} from "recharts";
import {
  TrendingUp, TrendingDown, X, ChevronDown, ChevronUp,
  ArrowUpRight, ArrowDownRight, Activity, Target, Shield
} from "lucide-react";

const formatNumber = (v, decimals = 2) => {
  if (v === null || v === undefined) return "—";
  return Number(v).toFixed(decimals);
};

const formatCurrency = (v) => {
  if (v === null || v === undefined) return "—";
  return `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const MetricCard = ({ label, value, suffix = "", color = "text-foreground", small = false }) => (
  <div className={`p-3 bg-secondary/30 border border-border ${small ? "" : ""}`} data-testid={`metric-${label.toLowerCase().replace(/\s+/g, "-")}`}>
    <p className="mono-label text-[10px] mb-1">{label}</p>
    <p className={`font-mono font-bold ${small ? "text-sm" : "text-lg"} ${color} tabular-nums`}>
      {value}{suffix}
    </p>
  </div>
);

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border p-3 shadow-lg">
      <p className="mono-label text-[10px] mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="text-xs font-mono tabular-nums" style={{ color: p.color }}>
          {p.name}: {p.name === "drawdown_pct" ? `-${formatNumber(p.value)}%` : formatCurrency(p.value)}
        </p>
      ))}
    </div>
  );
};

const TradeRow = ({ trade, index }) => {
  const isWin = trade.pnl_percent >= 0;
  return (
    <tr className="border-b border-border/50 hover:bg-secondary/20 transition-colors" data-testid={`trade-row-${index}`}>
      <td className="py-2 px-3 font-mono text-xs tabular-nums">{index + 1}</td>
      <td className="py-2 px-3 font-mono text-xs tabular-nums">{trade.entry_time?.split("T")[0] || trade.entry_time}</td>
      <td className="py-2 px-3 font-mono text-xs tabular-nums">{formatNumber(trade.entry_price)}</td>
      <td className="py-2 px-3 font-mono text-xs tabular-nums">{trade.exit_time?.split("T")[0] || trade.exit_time}</td>
      <td className="py-2 px-3 font-mono text-xs tabular-nums">{formatNumber(trade.exit_price)}</td>
      <td className={`py-2 px-3 font-mono text-xs tabular-nums font-bold ${isWin ? "text-primary" : "text-destructive"}`}>
        {isWin ? "+" : ""}{formatNumber(trade.pnl_percent)}%
      </td>
      <td className="py-2 px-3 font-mono text-xs tabular-nums">{trade.holding_candles}</td>
      <td className="py-2 px-3">
        <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 ${
          trade.exit_reason === "target_profit" ? "bg-primary/20 text-primary" :
          trade.exit_reason === "stop_loss" ? "bg-destructive/20 text-destructive" :
          "bg-secondary text-muted-foreground"
        }`}>{trade.exit_reason || "—"}</span>
      </td>
    </tr>
  );
};

export default function BacktestResultsPanel({ results, onClose }) {
  const [showTrades, setShowTrades] = useState(false);

  if (!results) return null;

  const { metrics = {}, costs = {}, equity_curve = [], trades = [], warnings = [], label, disclaimer, data_source, candles_processed } = results;
  const totalPnl = metrics.total_pnl_pct || 0;
  const isProfit = totalPnl >= 0;

  // Prepare equity curve data for chart
  const chartData = equity_curve.map((p) => ({
    date: p.timestamp?.split("T")[0] || p.timestamp,
    equity: p.equity,
    drawdown_pct: p.drawdown_pct || 0,
  }));

  return (
    <div className="space-y-4 animate-in slide-in-from-bottom-4 duration-300" data-testid="backtest-results-panel">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 flex items-center justify-center ${isProfit ? "bg-primary/20" : "bg-destructive/20"}`}>
            {isProfit ? <TrendingUp className="w-5 h-5 text-primary" /> : <TrendingDown className="w-5 h-5 text-destructive" />}
          </div>
          <div>
            <h2 className="text-lg font-mono font-bold text-foreground">{label || "Backtest Results"}</h2>
            <p className="text-xs text-muted-foreground">
              {candles_processed} candles · {data_source} · {trades.length} trades
            </p>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} data-testid="close-backtest-panel">
          <X className="w-5 h-5" />
        </Button>
      </div>

      {/* Disclaimer */}
      {disclaimer && (
        <p className="text-[11px] text-yellow-500/80 font-mono italic border-l-2 border-yellow-500/30 pl-3">{disclaimer}</p>
      )}

      {/* Key Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2">
        <MetricCard label="Total P&L" value={`${isProfit ? "+" : ""}${formatNumber(totalPnl)}`} suffix="%" color={isProfit ? "text-primary" : "text-destructive"} />
        <MetricCard label="P&L (Abs)" value={formatCurrency(metrics.total_pnl_abs)} color={metrics.total_pnl_abs >= 0 ? "text-primary" : "text-destructive"} />
        <MetricCard label="Win Rate" value={formatNumber(metrics.win_rate)} suffix="%" />
        <MetricCard label="Sharpe Ratio" value={formatNumber(metrics.sharpe_ratio)} color={metrics.sharpe_ratio >= 1 ? "text-primary" : metrics.sharpe_ratio >= 0 ? "text-foreground" : "text-destructive"} />
        <MetricCard label="Max Drawdown" value={formatNumber(metrics.max_drawdown_pct)} suffix="%" color="text-destructive" />
        <MetricCard label="Profit Factor" value={formatNumber(metrics.profit_factor)} color={metrics.profit_factor >= 1 ? "text-primary" : "text-destructive"} />
      </div>

      {/* Equity Curve Chart */}
      {chartData.length > 1 && (
        <Card className="border-border bg-card">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Activity className="w-4 h-4 text-primary" /> EQUITY CURVE
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 pb-2 pr-4">
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                <defs>
                  <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(156, 100%, 45%)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(156, 100%, 45%)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(240, 4%, 16%)" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "hsl(240, 5%, 65%)", fontSize: 10, fontFamily: "JetBrains Mono" }}
                  tickLine={false}
                  axisLine={{ stroke: "hsl(240, 4%, 16%)" }}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fill: "hsl(240, 5%, 65%)", fontSize: 10, fontFamily: "JetBrains Mono" }}
                  tickLine={false}
                  axisLine={{ stroke: "hsl(240, 4%, 16%)" }}
                  tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="equity"
                  stroke="hsl(156, 100%, 45%)"
                  strokeWidth={2}
                  fill="url(#equityGrad)"
                  name="Equity"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Detailed Metrics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Performance */}
        <Card className="border-border bg-card">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Target className="w-4 h-4 text-primary" /> PERFORMANCE
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="grid grid-cols-2 gap-2">
              <MetricCard label="Total Trades" value={metrics.total_trades} small />
              <MetricCard label="Wins / Losses" value={`${metrics.wins || 0} / ${metrics.losses || 0}`} small />
              <MetricCard label="Avg P&L/Trade" value={formatNumber(metrics.avg_pnl_per_trade)} suffix="%" small />
              <MetricCard label="Best Trade" value={`+${formatNumber(metrics.best_trade)}`} suffix="%" color="text-primary" small />
              <MetricCard label="Worst Trade" value={formatNumber(metrics.worst_trade)} suffix="%" color="text-destructive" small />
              <MetricCard label="Avg Holding" value={formatNumber(metrics.avg_holding_period, 0)} suffix=" bars" small />
              <MetricCard label="Consec. Wins" value={metrics.max_consecutive_wins || 0} small />
              <MetricCard label="Consec. Losses" value={metrics.max_consecutive_losses || 0} small />
              <MetricCard label="DD Duration" value={formatNumber(metrics.max_drawdown_duration, 0)} suffix=" bars" small />
            </div>
          </CardContent>
        </Card>

        {/* Costs Breakdown */}
        <Card className="border-border bg-card">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Shield className="w-4 h-4 text-primary" /> COST BREAKDOWN
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {costs && Object.keys(costs).length > 0 ? (
              <div className="space-y-2">
                {Object.entries(costs).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between py-1.5 border-b border-border/30 last:border-0">
                    <span className="text-xs font-mono text-muted-foreground uppercase">{key.replace(/_/g, " ")}</span>
                    <span className="text-xs font-mono font-bold text-foreground tabular-nums">{formatCurrency(val)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No cost data available.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="p-3 bg-yellow-500/10 border border-yellow-500/30">
          <p className="mono-label text-yellow-500 text-[10px] mb-1">WARNINGS</p>
          {warnings.map((w, i) => (
            <p key={i} className="text-xs text-yellow-500/80 font-mono">{w}</p>
          ))}
        </div>
      )}

      {/* Trade List */}
      <Card className="border-border bg-card">
        <CardHeader className="py-3 px-4 cursor-pointer" onClick={() => setShowTrades(!showTrades)}>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-mono">TRADE LOG ({trades.length})</CardTitle>
            {showTrades ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
          </div>
        </CardHeader>
        {showTrades && (
          <CardContent className="px-0 pb-2">
            {trades.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left" data-testid="trade-log-table">
                  <thead>
                    <tr className="border-b border-border bg-secondary/30">
                      <th className="py-2 px-3 mono-label text-[10px]">#</th>
                      <th className="py-2 px-3 mono-label text-[10px]">Entry Date</th>
                      <th className="py-2 px-3 mono-label text-[10px]">Entry Price</th>
                      <th className="py-2 px-3 mono-label text-[10px]">Exit Date</th>
                      <th className="py-2 px-3 mono-label text-[10px]">Exit Price</th>
                      <th className="py-2 px-3 mono-label text-[10px]">P&L</th>
                      <th className="py-2 px-3 mono-label text-[10px]">Bars</th>
                      <th className="py-2 px-3 mono-label text-[10px]">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t, i) => <TradeRow key={i} trade={t} index={i} />)}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground px-4 pb-2">No trades executed during this period.</p>
            )}
          </CardContent>
        )}
      </Card>
    </div>
  );
}
