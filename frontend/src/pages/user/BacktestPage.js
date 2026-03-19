import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import {
  Loader2, Activity, ArrowLeft, TrendingUp, TrendingDown,
  ChevronDown, ChevronUp
} from "lucide-react";
import MultiStockCompare from "@/components/MultiStockCompare";

const fmt = (v, d = 2) => v != null ? Number(v).toFixed(d) : "—";
const fmtCur = (v) => v != null ? `\u20B9${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—";

const MetricCard = ({ label, value, suffix = "", color = "text-foreground", testId }) => (
  <div className="p-3 bg-secondary/30 border border-border" data-testid={testId}>
    <p className="mono-label text-[10px] mb-1">{label}</p>
    <p className={`font-mono font-bold text-lg ${color} tabular-nums`}>{value}{suffix}</p>
  </div>
);

const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border p-2 text-xs font-mono shadow-lg">
      <p className="text-muted-foreground">{label}</p>
      <p className="text-primary">{fmtCur(payload[0]?.value)}</p>
    </div>
  );
};

export default function BacktestPage() {
  const { strategyId } = useParams();
  const api = useApi();
  const navigate = useNavigate();
  const [strategy, setStrategy] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showTrades, setShowTrades] = useState(false);
  const [deploying, setDeploying] = useState(false);

  useEffect(() => {
    document.title = "Backtest | Text2trade";
    runBacktest();
  }, [strategyId]);

  const runBacktest = async () => {
    setLoading(true);
    try {
      const sRes = await api.get(`/strategy/${strategyId}`);
      const strat = sRes.data.strategy || sRes.data;
      setStrategy(strat);
      if (strat?.metadata?.name) document.title = `Backtest: ${strat.metadata.name} | Text2trade`;
      const bRes = await api.post("/backtest", { strategy: strat });
      setResult(bRes.data);
    } catch (err) {
      setResult({ success: false, error: err.response?.data?.detail || "Backtest failed" });
    } finally {
      setLoading(false);
    }
  };

  const handleDeploy = async () => {
    if (!strategy) return;
    setDeploying(true);
    try {
      await api.post("/paper-trade/deploy", {
        strategy_id: strategyId,
        symbol: strategy.instrument?.symbol || "RELIANCE",
        timeframe: strategy.timeframe?.interval || "1d",
        initial_capital: 100000,
        lookback_days: 60,
      });
      navigate("/paper-trades");
    } catch { /* ignore */ } finally { setDeploying(false); }
  };

  if (loading) return <div className="flex items-center justify-center py-32"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;

  const m = result?.metrics || {};
  const trades = result?.trades || [];
  const equity = (result?.equity_curve || []).map((p) => ({ date: p.timestamp?.split("T")[0], equity: p.equity }));
  const pnl = m.total_pnl_pct || 0;
  const isUp = pnl >= 0;

  return (
    <div className="space-y-6" data-testid="backtest-page">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)} data-testid="back-btn"><ArrowLeft className="w-5 h-5" /></Button>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-foreground">{strategy?.metadata?.name || "Backtest"}</h1>
            <p className="text-xs text-muted-foreground font-mono">{strategy?.instrument?.symbol} · {strategy?.timeframe?.interval} · {result?.candles_processed || 0} candles</p>
          </div>
        </div>
        <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5" onClick={handleDeploy} disabled={deploying} data-testid="deploy-paper-trade-btn">
          <Activity className="w-3 h-3" /> {deploying ? "Deploying..." : "Paper Trade This Strategy"}
        </Button>
      </div>

      {result?.disclaimer && <p className="text-[11px] text-yellow-500/80 font-mono italic border-l-2 border-yellow-500/30 pl-3">{result.disclaimer}</p>}

      {/* Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
        <MetricCard label="NET P&L" value={`${isUp ? "+" : ""}${fmt(pnl)}`} suffix="%" color={isUp ? "text-primary" : "text-destructive"} testId="metric-pnl" />
        <MetricCard label="WIN RATE" value={fmt(m.win_rate)} suffix="%" testId="metric-winrate" />
        <MetricCard label="MAX DRAWDOWN" value={fmt(m.max_drawdown_pct)} suffix="%" color="text-destructive" testId="metric-drawdown" />
        <MetricCard label="SHARPE" value={fmt(m.sharpe_ratio)} color={m.sharpe_ratio >= 1 ? "text-primary" : "text-foreground"} testId="metric-sharpe" />
        <MetricCard label="PROFIT FACTOR" value={fmt(m.profit_factor)} color={m.profit_factor >= 1 ? "text-primary" : "text-destructive"} testId="metric-pf" />
      </div>

      {/* Equity Curve */}
      {equity.length > 1 && (
        <Card className="border-border bg-card">
          <CardHeader className="py-3 px-4"><CardTitle className="text-sm font-mono">EQUITY CURVE</CardTitle></CardHeader>
          <CardContent className="p-0 pb-2 pr-4">
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={equity} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                <defs><linearGradient id="eqG" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="hsl(156,100%,45%)" stopOpacity={0.3} /><stop offset="95%" stopColor="hsl(156,100%,45%)" stopOpacity={0} /></linearGradient></defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(240,4%,16%)" />
                <XAxis dataKey="date" tick={{ fill: "hsl(240,5%,65%)", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} axisLine={{ stroke: "hsl(240,4%,16%)" }} interval="preserveStartEnd" />
                <YAxis tick={{ fill: "hsl(240,5%,65%)", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} axisLine={{ stroke: "hsl(240,4%,16%)" }} tickFormatter={(v) => `\u20B9${(v / 1000).toFixed(0)}k`} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="equity" stroke="hsl(156,100%,45%)" strokeWidth={2} fill="url(#eqG)" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Extra metrics + costs side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="border-border bg-card">
          <CardHeader className="py-3 px-4"><CardTitle className="text-sm font-mono">DETAILS</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="grid grid-cols-2 gap-2">
              <MetricCard label="Total Trades" value={m.total_trades || 0} testId="metric-trades" />
              <MetricCard label="Wins/Losses" value={`${m.wins || 0}/${m.losses || 0}`} testId="metric-wl" />
              <MetricCard label="Avg P&L/Trade" value={fmt(m.avg_pnl_per_trade)} suffix="%" testId="metric-avg" />
              <MetricCard label="Best Trade" value={`+${fmt(m.best_trade)}`} suffix="%" color="text-primary" testId="metric-best" />
              <MetricCard label="Worst Trade" value={fmt(m.worst_trade)} suffix="%" color="text-destructive" testId="metric-worst" />
              <MetricCard label="Avg Holding" value={fmt(m.avg_holding_period, 0)} suffix=" bars" testId="metric-hold" />
            </div>
          </CardContent>
        </Card>
        <Card className="border-border bg-card">
          <CardHeader className="py-3 px-4"><CardTitle className="text-sm font-mono">COST BREAKDOWN</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4">
            {result?.costs && Object.keys(result.costs).length > 0 ? (
              <div className="space-y-2">
                {Object.entries(result.costs).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between py-1.5 border-b border-border/30 last:border-0">
                    <span className="text-xs font-mono text-muted-foreground uppercase">{k.replace(/_/g, " ")}</span>
                    <span className="text-xs font-mono font-bold text-foreground tabular-nums">{fmtCur(v)}</span>
                  </div>
                ))}
              </div>
            ) : <p className="text-xs text-muted-foreground">No cost data.</p>}
          </CardContent>
        </Card>
      </div>

      {/* Trade Table */}
      <Card className="border-border bg-card">
        <CardHeader className="py-3 px-4 cursor-pointer" onClick={() => setShowTrades(!showTrades)}>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-mono">TRADE LOG ({trades.length})</CardTitle>
            {showTrades ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
          </div>
        </CardHeader>
        {showTrades && trades.length > 0 && (
          <CardContent className="px-0 pb-2">
            <div className="overflow-x-auto">
              <table className="w-full text-left" data-testid="trade-table">
                <thead>
                  <tr className="border-b border-border bg-secondary/30">
                    {["#", "Entry", "Price", "Exit", "Price", "P&L", "Bars", "Reason"].map((h) => (
                      <th key={h} className="py-2 px-3 mono-label text-[10px]">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {trades.map((t, i) => (
                    <tr key={i} className="border-b border-border/50 hover:bg-secondary/20">
                      <td className="py-2 px-3 font-mono text-xs tabular-nums">{i + 1}</td>
                      <td className="py-2 px-3 font-mono text-xs tabular-nums">{t.entry_time?.split("T")[0]}</td>
                      <td className="py-2 px-3 font-mono text-xs tabular-nums">{fmt(t.entry_price)}</td>
                      <td className="py-2 px-3 font-mono text-xs tabular-nums">{t.exit_time?.split("T")[0]}</td>
                      <td className="py-2 px-3 font-mono text-xs tabular-nums">{fmt(t.exit_price)}</td>
                      <td className={`py-2 px-3 font-mono text-xs tabular-nums font-bold ${t.pnl_percent >= 0 ? "text-primary" : "text-destructive"}`}>{t.pnl_percent >= 0 ? "+" : ""}{fmt(t.pnl_percent)}%</td>
                      <td className="py-2 px-3 font-mono text-xs tabular-nums">{t.holding_candles}</td>
                      <td className="py-2 px-3"><span className={`text-[10px] font-mono uppercase px-1 py-0.5 ${t.exit_reason === "target_profit" ? "bg-primary/20 text-primary" : t.exit_reason === "stop_loss" ? "bg-destructive/20 text-destructive" : "bg-secondary text-muted-foreground"}`}>{t.exit_reason || "—"}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Multi-Stock Comparison */}
      {strategy && <MultiStockCompare strategy={strategy} />}
    </div>
  );
}
