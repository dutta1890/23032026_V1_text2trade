import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import {
  ArrowLeft, Shield, Download, Hash, Clock, Activity,
  TrendingUp, TrendingDown, ChevronDown, ChevronUp, GitBranch,
} from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

const fmt = (v, d = 2) => v != null ? Number(v).toFixed(d) : "\u2014";
const fmtCur = (v) => v != null ? `\u20B9${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "\u2014";

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

export default function BacktestSnapshotPage() {
  const { snapshotId } = useParams();
  const [snap, setSnap] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showTrades, setShowTrades] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    document.title = "Backtest Snapshot | Text2trade";
    axios.get(`${API}/backtest/snapshot/${snapshotId}`)
      .then((r) => setSnap(r.data))
      .catch(() => setError("Snapshot not found"))
      .finally(() => setLoading(false));
  }, [snapshotId]);

  if (loading) return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="w-5 h-5 border-2 border-primary border-t-transparent animate-spin rounded-full" />
    </div>
  );

  if (error || !snap) return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center">
        <p className="text-lg font-mono text-destructive mb-4">{error || "Not found"}</p>
        <Link to="/"><Button variant="outline" size="sm">Back to Home</Button></Link>
      </div>
    </div>
  );

  const m = snap.results?.metrics || {};
  const trades = snap.trades || [];
  const equity = (snap.equity_curve || []).map((p) => ({ date: p.timestamp?.split("T")[0], equity: p.equity }));
  const pnl = m.total_pnl_pct || 0;
  const isUp = pnl >= 0;
  const stratName = snap.strategy_json_snapshot?.metadata?.name || "Strategy";

  const handleDownload = () => {
    window.open(`${API}/backtest/snapshot/${snapshotId}/verify`, "_blank");
  };

  return (
    <div className="min-h-screen bg-background" data-testid="backtest-snapshot-page">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Link to="/">
            <Button variant="ghost" size="icon" className="h-8 w-8" data-testid="snapshot-back-btn">
              <ArrowLeft className="w-4 h-4" />
            </Button>
          </Link>
          <div className="flex-1">
            <h1 className="text-xl sm:text-2xl font-mono font-bold text-foreground tracking-tight">
              {stratName}
            </h1>
            <div className="flex flex-wrap items-center gap-2 mt-1">
              <span className="text-[10px] font-mono px-1.5 py-0.5 bg-primary/15 text-primary border border-primary/20">{snap.symbol}</span>
              <span className="text-[10px] font-mono text-muted-foreground">{snap.timeframe}</span>
              <span className="text-[10px] font-mono text-muted-foreground">v{snap.strategy_version}</span>
              <span className="text-[10px] font-mono text-muted-foreground">Engine v{snap.engine_version}</span>
            </div>
          </div>
          <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5" onClick={handleDownload} data-testid="verify-download-btn">
            <Download className="w-3 h-3" /> Verify This Backtest
          </Button>
        </div>

        {/* Snapshot metadata bar */}
        <div className="flex flex-wrap items-center gap-4 mb-6 p-3 bg-secondary/30 border border-border" data-testid="snapshot-meta">
          <div className="flex items-center gap-1.5">
            <Hash className="w-3 h-3 text-muted-foreground" />
            <span className="text-[10px] font-mono text-muted-foreground">ID: <span className="text-foreground">{snap.snapshot_id?.slice(0, 8)}</span></span>
          </div>
          <div className="flex items-center gap-1.5">
            <Shield className="w-3 h-3 text-muted-foreground" />
            <span className="text-[10px] font-mono text-muted-foreground">Hash: <span className="text-foreground">{snap.data_snapshot_hash?.slice(0, 12)}...</span></span>
          </div>
          <div className="flex items-center gap-1.5">
            <Clock className="w-3 h-3 text-muted-foreground" />
            <span className="text-[10px] font-mono text-muted-foreground">{snap.start_date} to {snap.end_date}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <GitBranch className="w-3 h-3 text-muted-foreground" />
            <span className="text-[10px] font-mono text-emerald-400">Immutable</span>
          </div>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 mb-6">
          <MetricCard label="NET P&L" value={`${isUp ? "+" : ""}${fmt(pnl)}`} suffix="%" color={isUp ? "text-primary" : "text-destructive"} testId="metric-pnl" />
          <MetricCard label="WIN RATE" value={fmt(m.win_rate)} suffix="%" testId="metric-winrate" />
          <MetricCard label="MAX DRAWDOWN" value={fmt(m.max_drawdown_pct)} suffix="%" color="text-destructive" testId="metric-drawdown" />
          <MetricCard label="SHARPE" value={fmt(m.sharpe_ratio)} color={(m.sharpe_ratio || 0) >= 1 ? "text-primary" : "text-foreground"} testId="metric-sharpe" />
          <MetricCard label="PROFIT FACTOR" value={fmt(m.profit_factor)} color={(m.profit_factor || 0) >= 1 ? "text-primary" : "text-destructive"} testId="metric-pf" />
        </div>

        {/* Equity Curve */}
        {equity.length > 1 && (
          <Card className="border-border bg-card mb-6">
            <CardHeader className="py-3 px-4"><CardTitle className="text-sm font-mono">EQUITY CURVE</CardTitle></CardHeader>
            <CardContent className="p-0 pb-2 pr-4">
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={equity} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                  <defs><linearGradient id="eqGS" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="hsl(156,100%,45%)" stopOpacity={0.3} /><stop offset="95%" stopColor="hsl(156,100%,45%)" stopOpacity={0} /></linearGradient></defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(240,4%,16%)" />
                  <XAxis dataKey="date" tick={{ fill: "hsl(240,5%,65%)", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} axisLine={{ stroke: "hsl(240,4%,16%)" }} interval="preserveStartEnd" />
                  <YAxis tick={{ fill: "hsl(240,5%,65%)", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} axisLine={{ stroke: "hsl(240,4%,16%)" }} tickFormatter={(v) => `\u20B9${(v / 1000).toFixed(0)}k`} />
                  <Tooltip content={<ChartTooltip />} />
                  <Area type="monotone" dataKey="equity" stroke="hsl(156,100%,45%)" strokeWidth={2} fill="url(#eqGS)" />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* Trade Table */}
        <Card className="border-border bg-card mb-6">
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
                      <tr key={`${t.entry_time}-${t.exit_time}-${i}`} className="border-b border-border/50 hover:bg-secondary/20">
                        <td className="py-2 px-3 font-mono text-xs tabular-nums">{i + 1}</td>
                        <td className="py-2 px-3 font-mono text-xs tabular-nums">{t.entry_time?.split("T")[0]}</td>
                        <td className="py-2 px-3 font-mono text-xs tabular-nums">{fmt(t.entry_price)}</td>
                        <td className="py-2 px-3 font-mono text-xs tabular-nums">{t.exit_time?.split("T")[0]}</td>
                        <td className="py-2 px-3 font-mono text-xs tabular-nums">{fmt(t.exit_price)}</td>
                        <td className={`py-2 px-3 font-mono text-xs tabular-nums font-bold ${t.pnl_percent >= 0 ? "text-primary" : "text-destructive"}`}>{t.pnl_percent >= 0 ? "+" : ""}{fmt(t.pnl_percent)}%</td>
                        <td className="py-2 px-3 font-mono text-xs tabular-nums">{t.holding_candles}</td>
                        <td className="py-2 px-3"><span className={`text-[10px] font-mono uppercase px-1 py-0.5 ${t.exit_reason === "target_profit" ? "bg-primary/20 text-primary" : t.exit_reason === "stop_loss" ? "bg-destructive/20 text-destructive" : "bg-secondary text-muted-foreground"}`}>{t.exit_reason || "\u2014"}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          )}
        </Card>

        {/* Footer */}
        <div className="text-center">
          <p className="text-[10px] text-muted-foreground font-mono">
            This is a permanent, immutable backtest record. Results cannot be modified.
          </p>
          <div className="flex justify-center gap-3 mt-3">
            <Link to="/benchmarks">
              <Button variant="outline" size="sm" className="text-xs font-mono h-8 gap-1.5">
                <Activity className="w-3 h-3" /> Engine Benchmarks
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
