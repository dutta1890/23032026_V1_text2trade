import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Area, AreaChart,
} from "recharts";
import {
  TrendingUp, TrendingDown, BarChart3, Target, Trophy,
  AlertTriangle, ArrowUpRight, ArrowDownRight, Clock, RefreshCw,
  ChevronRight, Flame, Shield,
} from "lucide-react";
import { PageSkeleton } from "@/components/LoadingSkeleton";

const StatCard = ({ label, value, sub, icon: Icon, positive, testId }) => (
  <Card className="border-border bg-card" data-testid={testId}>
    <CardContent className="p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="mono-label text-[10px] text-muted-foreground">{label}</span>
        {Icon && <Icon className="w-3.5 h-3.5 text-muted-foreground" />}
      </div>
      <p className={`text-xl font-mono font-bold tabular-nums ${positive === true ? "text-primary" : positive === false ? "text-destructive" : "text-foreground"}`}>
        {value}
      </p>
      {sub && <p className="text-[10px] text-muted-foreground mt-1 font-mono">{sub}</p>}
    </CardContent>
  </Card>
);

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border p-2.5 font-mono text-xs">
      <p className="text-muted-foreground mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="text-foreground">
          <span className="text-primary">{p.name}:</span>{" "}
          <span className="tabular-nums font-bold">{typeof p.value === "number" ? p.value.toFixed(2) : p.value}%</span>
        </p>
      ))}
    </div>
  );
};

export default function TrackerPage() {
  const api = useApi();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = () => {
    setLoading(true);
    setError(null);
    api.get("/tracker/dashboard")
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.detail || "Failed to load tracker data"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    document.title = "Performance Tracker | Text2trade";
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) return <PageSkeleton />;

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20" data-testid="tracker-error">
        <AlertTriangle className="w-10 h-10 text-destructive mb-3" />
        <p className="text-sm text-muted-foreground mb-4">{error}</p>
        <Button variant="outline" size="sm" onClick={fetchData} className="font-mono text-xs gap-2">
          <RefreshCw className="w-3.5 h-3.5" /> Retry
        </Button>
      </div>
    );
  }

  const isEmpty = !data || data.total_records === 0;

  if (isEmpty) {
    return (
      <div className="space-y-6" data-testid="tracker-page">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Performance Tracker</h1>
          <p className="text-sm text-muted-foreground mt-1">Track your cumulative strategy performance over time.</p>
        </div>
        <Card className="border-border border-dashed bg-card/50" data-testid="tracker-empty">
          <CardContent className="p-10 text-center">
            <BarChart3 className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="font-mono font-bold text-foreground mb-2">No Performance Data Yet</h3>
            <p className="text-xs text-muted-foreground mb-5 max-w-md mx-auto">
              Run backtests on your strategies to start building your track record. Each backtest result is automatically recorded here.
            </p>
            <div className="flex gap-3 justify-center">
              <Button size="sm" className="font-mono text-[10px] uppercase gap-1.5" onClick={() => navigate("/build")} data-testid="tracker-cta-build">
                <Target className="w-3 h-3" /> Build Strategy
              </Button>
              <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5" onClick={() => navigate("/templates")} data-testid="tracker-cta-templates">
                <Trophy className="w-3 h-3" /> Browse Templates
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { avg_sharpe, avg_pnl, avg_win_rate, best_strategy, worst_strategy, cumulative_pnl, strategy_rankings, improvement, recent_activity, total_records, total_backtests, total_paper_trades } = data;

  return (
    <div className="space-y-8" data-testid="tracker-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Performance Tracker</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total_records} run{total_records !== 1 ? "s" : ""} tracked
            {total_backtests > 0 && <span> &middot; {total_backtests} backtest{total_backtests !== 1 ? "s" : ""}</span>}
            {total_paper_trades > 0 && <span> &middot; {total_paper_trades} paper trade{total_paper_trades !== 1 ? "s" : ""}</span>}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchData} className="font-mono text-[10px] gap-1.5" data-testid="tracker-refresh">
          <RefreshCw className="w-3 h-3" /> Refresh
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3" data-testid="tracker-stats">
        <StatCard label="AVG SHARPE" value={avg_sharpe?.toFixed(2) || "0.00"} icon={BarChart3} positive={avg_sharpe > 0} testId="stat-avg-sharpe" />
        <StatCard label="AVG P&L" value={`${avg_pnl >= 0 ? "+" : ""}${avg_pnl?.toFixed(2) || "0.00"}%`} icon={TrendingUp} positive={avg_pnl >= 0} testId="stat-avg-pnl" />
        <StatCard label="AVG WIN RATE" value={`${avg_win_rate?.toFixed(1) || "0.0"}%`} icon={Target} positive={avg_win_rate >= 50} testId="stat-avg-winrate" />
        <StatCard label="TOTAL RUNS" value={total_records} icon={Flame} testId="stat-total-runs" />
      </div>

      {/* Cumulative P&L Chart */}
      {cumulative_pnl && cumulative_pnl.length > 1 && (
        <Card className="border-border bg-card" data-testid="tracker-chart">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="mono-label text-[10px]">CUMULATIVE P&L CURVE</h2>
              <span className={`font-mono text-xs font-bold tabular-nums ${cumulative_pnl[cumulative_pnl.length - 1]?.cumulative_pnl >= 0 ? "text-primary" : "text-destructive"}`}>
                {cumulative_pnl[cumulative_pnl.length - 1]?.cumulative_pnl >= 0 ? "+" : ""}
                {cumulative_pnl[cumulative_pnl.length - 1]?.cumulative_pnl?.toFixed(2)}%
              </span>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={cumulative_pnl} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
                  <defs>
                    <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(156, 100%, 45%)" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="hsl(156, 100%, 45%)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(240, 4%, 16%)" />
                  <XAxis dataKey="date" tick={{ fill: "hsl(240, 5%, 65%)", fontSize: 10, fontFamily: "monospace" }} tickLine={false} axisLine={{ stroke: "hsl(240, 4%, 16%)" }} />
                  <YAxis tick={{ fill: "hsl(240, 5%, 65%)", fontSize: 10, fontFamily: "monospace" }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}%`} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="cumulative_pnl" name="Cumulative P&L" stroke="hsl(156, 100%, 45%)" fill="url(#pnlGrad)" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: "hsl(156, 100%, 45%)" }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Best & Worst + Improvement */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {best_strategy && (
          <Card className="border-border bg-card" data-testid="tracker-best">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <Trophy className="w-4 h-4 text-primary" />
                <span className="mono-label text-[10px]">BEST PERFORMER</span>
              </div>
              <p className="font-mono font-bold text-sm text-foreground truncate">{best_strategy.name}</p>
              <div className="flex items-center gap-3 mt-2">
                <span className="text-primary font-mono text-sm font-bold tabular-nums">
                  {best_strategy.pnl_pct >= 0 ? "+" : ""}{best_strategy.pnl_pct?.toFixed(2)}%
                </span>
                <span className="text-[10px] text-muted-foreground font-mono">Sharpe {best_strategy.sharpe?.toFixed(2)}</span>
                <Badge variant="outline" className="text-[9px] font-mono">{best_strategy.symbol}</Badge>
              </div>
            </CardContent>
          </Card>
        )}

        {worst_strategy && (
          <Card className="border-border bg-card" data-testid="tracker-worst">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-destructive" />
                <span className="mono-label text-[10px]">WORST PERFORMER</span>
              </div>
              <p className="font-mono font-bold text-sm text-foreground truncate">{worst_strategy.name}</p>
              <div className="flex items-center gap-3 mt-2">
                <span className="text-destructive font-mono text-sm font-bold tabular-nums">
                  {worst_strategy.pnl_pct >= 0 ? "+" : ""}{worst_strategy.pnl_pct?.toFixed(2)}%
                </span>
                <span className="text-[10px] text-muted-foreground font-mono">Sharpe {worst_strategy.sharpe?.toFixed(2)}</span>
                <Badge variant="outline" className="text-[9px] font-mono">{worst_strategy.symbol}</Badge>
              </div>
            </CardContent>
          </Card>
        )}

        {improvement && (
          <Card className="border-border bg-card" data-testid="tracker-improvement">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <Shield className="w-4 h-4 text-muted-foreground" />
                <span className="mono-label text-[10px]">IMPROVEMENT TREND</span>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-muted-foreground font-mono">Sharpe trend</span>
                  <div className="flex items-center gap-1">
                    {improvement.sharpe_change_pct >= 0
                      ? <ArrowUpRight className="w-3 h-3 text-primary" />
                      : <ArrowDownRight className="w-3 h-3 text-destructive" />}
                    <span className={`font-mono text-xs font-bold tabular-nums ${improvement.sharpe_change_pct >= 0 ? "text-primary" : "text-destructive"}`}>
                      {improvement.sharpe_change_pct >= 0 ? "+" : ""}{improvement.sharpe_change_pct?.toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-muted-foreground font-mono">P&L trend</span>
                  <div className="flex items-center gap-1">
                    {improvement.pnl_change_pct >= 0
                      ? <ArrowUpRight className="w-3 h-3 text-primary" />
                      : <ArrowDownRight className="w-3 h-3 text-destructive" />}
                    <span className={`font-mono text-xs font-bold tabular-nums ${improvement.pnl_change_pct >= 0 ? "text-primary" : "text-destructive"}`}>
                      {improvement.pnl_change_pct >= 0 ? "+" : ""}{improvement.pnl_change_pct?.toFixed(1)}%
                    </span>
                  </div>
                </div>
                <p className="text-[9px] text-muted-foreground font-mono mt-1">
                  Based on first {improvement.early_count} vs latest {improvement.recent_count} runs
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Strategy Rankings */}
      {strategy_rankings && strategy_rankings.length > 0 && (
        <div data-testid="tracker-rankings">
          <h2 className="mono-label text-[10px] mb-3">STRATEGY RANKINGS</h2>
          <div className="space-y-2">
            {strategy_rankings.map((s, i) => (
              <Card key={i} className="border-border bg-card hover:border-primary/30 transition-colors" data-testid={`ranking-row-${i}`}>
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <span className={`font-mono text-xs font-bold w-6 text-center ${s.rank === 1 ? "text-primary" : s.rank === 2 ? "text-blue-400" : "text-muted-foreground"}`}>
                      #{s.rank}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="font-mono font-bold text-sm text-foreground truncate">{s.strategy_name}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-muted-foreground font-mono">{s.run_count} run{s.run_count !== 1 ? "s" : ""}</span>
                        <span className="text-[10px] text-muted-foreground font-mono">{s.total_trades} trades</span>
                        {s.symbols && s.symbols.length > 0 && (
                          <span className="text-[10px] text-muted-foreground font-mono">{s.symbols.join(", ")}</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 ml-2">
                    <div className="text-right">
                      <p className="text-[10px] text-muted-foreground font-mono">Sharpe</p>
                      <p className={`font-mono text-xs font-bold tabular-nums ${s.avg_sharpe > 0 ? "text-primary" : s.avg_sharpe < 0 ? "text-destructive" : "text-foreground"}`}>
                        {s.avg_sharpe?.toFixed(2)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-muted-foreground font-mono">Avg P&L</p>
                      <p className={`font-mono text-xs font-bold tabular-nums ${s.avg_pnl >= 0 ? "text-primary" : "text-destructive"}`}>
                        {s.avg_pnl >= 0 ? "+" : ""}{s.avg_pnl?.toFixed(2)}%
                      </p>
                    </div>
                    <div className="text-right hidden sm:block">
                      <p className="text-[10px] text-muted-foreground font-mono">Win Rate</p>
                      <p className="font-mono text-xs font-bold tabular-nums text-foreground">
                        {s.avg_win_rate?.toFixed(1)}%
                      </p>
                    </div>
                    {s.strategy_id && (
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => navigate(`/strategy/${s.strategy_id}`)} data-testid={`ranking-view-${i}`}>
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      {recent_activity && recent_activity.length > 0 && (
        <div data-testid="tracker-recent">
          <h2 className="mono-label text-[10px] mb-3">RECENT ACTIVITY</h2>
          <Card className="border-border bg-card">
            <CardContent className="p-0">
              <div className="divide-y divide-border">
                {recent_activity.map((r, i) => (
                  <div key={i} className="px-4 py-3 flex items-center justify-between" data-testid={`recent-row-${i}`}>
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <Clock className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                      <div className="min-w-0">
                        <p className="font-mono text-xs text-foreground truncate">{r.strategy_name}</p>
                        <p className="text-[10px] text-muted-foreground font-mono">
                          {r.symbol} &middot; {r.source} &middot; {r.total_trades} trades
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 ml-2">
                      <div className="text-right">
                        <span className={`font-mono text-xs font-bold tabular-nums ${r.pnl_pct >= 0 ? "text-primary" : "text-destructive"}`}>
                          {r.pnl_pct >= 0 ? "+" : ""}{r.pnl_pct?.toFixed(2)}%
                        </span>
                      </div>
                      <span className="text-[10px] text-muted-foreground font-mono">{r.recorded_at?.slice(0, 10)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
