import { useState, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  ArrowLeft, GitCompare, TrendingUp, TrendingDown,
  CheckCircle2, XCircle, Equal,
} from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";
const fmt = (v, d = 2) => v != null ? Number(v).toFixed(d) : "\u2014";

function DiffRow({ label, diff }) {
  if (!diff) return null;
  const delta = diff.delta || 0;
  const improved = delta > 0;
  const unchanged = Math.abs(delta) < 0.01;
  return (
    <div className="flex items-center justify-between py-2.5 px-3 border-b border-border/30 last:border-0" data-testid={`diff-${label.toLowerCase().replace(/\s/g, '-')}`}>
      <span className="text-xs font-mono text-muted-foreground w-40">{label}</span>
      <span className="text-xs font-mono text-foreground tabular-nums w-24 text-right">{fmt(diff.a)}</span>
      <span className="text-xs font-mono text-foreground tabular-nums w-24 text-right">{fmt(diff.b)}</span>
      <div className="flex items-center gap-1 w-28 justify-end">
        {unchanged ? (
          <Equal className="w-3 h-3 text-muted-foreground" />
        ) : improved ? (
          <TrendingUp className="w-3 h-3 text-emerald-400" />
        ) : (
          <TrendingDown className="w-3 h-3 text-red-400" />
        )}
        <span className={`text-xs font-mono font-bold tabular-nums ${unchanged ? "text-muted-foreground" : improved ? "text-emerald-400" : "text-red-400"}`}>
          {delta > 0 ? "+" : ""}{fmt(delta)}
        </span>
      </div>
    </div>
  );
}

export default function BacktestComparePage() {
  const [params] = useSearchParams();
  const a = params.get("a");
  const b = params.get("b");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    document.title = "Compare Backtests | Text2trade";
    if (!a || !b) { setError("Two snapshot IDs required (?a=...&b=...)"); setLoading(false); return; }
    axios.get(`${API}/backtest/compare-snapshots?a=${a}&b=${b}`)
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.detail || "Comparison failed"))
      .finally(() => setLoading(false));
  }, [a, b]);

  if (loading) return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="w-5 h-5 border-2 border-primary border-t-transparent animate-spin rounded-full" />
    </div>
  );

  if (error) return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center">
        <p className="text-lg font-mono text-destructive mb-4">{error}</p>
        <Link to="/"><Button variant="outline" size="sm">Back to Home</Button></Link>
      </div>
    </div>
  );

  const sa = data.snapshot_a || {};
  const sb = data.snapshot_b || {};
  const md = data.metrics_diff || {};

  return (
    <div className="min-h-screen bg-background" data-testid="backtest-compare-page">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center gap-3 mb-6">
          <Link to="/">
            <Button variant="ghost" size="icon" className="h-8 w-8"><ArrowLeft className="w-4 h-4" /></Button>
          </Link>
          <div>
            <h1 className="text-xl sm:text-2xl font-mono font-bold text-foreground tracking-tight flex items-center gap-2">
              <GitCompare className="w-5 h-5 text-primary" />
              Compare Backtests
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">Side-by-side snapshot comparison</p>
          </div>
        </div>

        {/* Snapshot Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <Card className="border-border bg-card border-l-4 border-l-primary" data-testid="snapshot-a-info">
            <CardContent className="p-4">
              <p className="mono-label text-[10px] text-primary mb-2">SNAPSHOT A</p>
              <p className="font-mono text-sm font-bold text-foreground">{sa.strategy_name || "Strategy A"}</p>
              <div className="flex flex-wrap gap-2 mt-2">
                <span className="text-[10px] font-mono px-1.5 py-0.5 bg-secondary border border-border">{sa.symbol}</span>
                <span className="text-[10px] font-mono text-muted-foreground">v{sa.strategy_version}</span>
                <span className="text-[10px] font-mono text-muted-foreground">Engine {sa.engine_version}</span>
              </div>
              <p className="text-[10px] font-mono text-muted-foreground mt-2">{sa.snapshot_id?.slice(0, 8)}</p>
            </CardContent>
          </Card>
          <Card className="border-border bg-card border-l-4 border-l-amber-500" data-testid="snapshot-b-info">
            <CardContent className="p-4">
              <p className="mono-label text-[10px] text-amber-500 mb-2">SNAPSHOT B</p>
              <p className="font-mono text-sm font-bold text-foreground">{sb.strategy_name || "Strategy B"}</p>
              <div className="flex flex-wrap gap-2 mt-2">
                <span className="text-[10px] font-mono px-1.5 py-0.5 bg-secondary border border-border">{sb.symbol}</span>
                <span className="text-[10px] font-mono text-muted-foreground">v{sb.strategy_version}</span>
                <span className="text-[10px] font-mono text-muted-foreground">Engine {sb.engine_version}</span>
              </div>
              <p className="text-[10px] font-mono text-muted-foreground mt-2">{sb.snapshot_id?.slice(0, 8)}</p>
            </CardContent>
          </Card>
        </div>

        {/* Data/Engine match indicators */}
        <div className="flex gap-4 mb-6">
          <div className={`flex items-center gap-1.5 px-3 py-2 border text-[11px] font-mono ${data.same_data ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" : "bg-amber-500/10 border-amber-500/30 text-amber-400"}`} data-testid="same-data-badge">
            {data.same_data ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
            {data.same_data ? "Same Data" : "Different Data"}
          </div>
          <div className={`flex items-center gap-1.5 px-3 py-2 border text-[11px] font-mono ${data.same_engine ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" : "bg-amber-500/10 border-amber-500/30 text-amber-400"}`} data-testid="same-engine-badge">
            {data.same_engine ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
            {data.same_engine ? "Same Engine" : "Different Engine"}
          </div>
        </div>

        {/* Metrics Diff Table */}
        <Card className="border-border bg-card mb-6" data-testid="metrics-diff-card">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm font-mono">METRICS COMPARISON</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="flex items-center justify-between py-2 px-3 bg-secondary/50 border-b border-border">
              <span className="text-[10px] font-mono text-muted-foreground w-40">Metric</span>
              <span className="text-[10px] font-mono text-primary w-24 text-right">A</span>
              <span className="text-[10px] font-mono text-amber-500 w-24 text-right">B</span>
              <span className="text-[10px] font-mono text-muted-foreground w-28 text-right">Delta</span>
            </div>
            <DiffRow label="Total Trades" diff={md.total_trades} />
            <DiffRow label="Win Rate (%)" diff={md.win_rate} />
            <DiffRow label="Total P&L (%)" diff={md.total_pnl_pct} />
            <DiffRow label="Max Drawdown (%)" diff={md.max_drawdown_pct} />
            <DiffRow label="Sharpe Ratio" diff={md.sharpe_ratio} />
            <DiffRow label="Profit Factor" diff={md.profit_factor} />
            <DiffRow label="Avg P&L/Trade" diff={md.avg_pnl_per_trade} />
          </CardContent>
        </Card>

        {/* Links */}
        <div className="flex justify-center gap-3">
          {a && <Link to={`/backtest/snapshot/${a}`}>
            <Button variant="outline" size="sm" className="text-xs font-mono h-8">View Snapshot A</Button>
          </Link>}
          {b && <Link to={`/backtest/snapshot/${b}`}>
            <Button variant="outline" size="sm" className="text-xs font-mono h-8">View Snapshot B</Button>
          </Link>}
        </div>
      </div>
    </div>
  );
}
