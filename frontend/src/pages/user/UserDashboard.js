import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Hammer, BookOpen, Search, FolderOpen, Activity, BarChart3,
  TrendingUp, TrendingDown, Loader2, Play, PlusCircle, ArrowRight
} from "lucide-react";

const StatCard = ({ label, value, sub, color = "text-foreground", testId }) => (
  <Card className="border-border bg-card" data-testid={testId}>
    <CardContent className="p-4">
      <span className="mono-label text-[10px]">{label}</span>
      <p className={`text-2xl font-mono font-bold ${color} mt-1 tabular-nums`}>{value}</p>
      {sub && <p className="text-[10px] text-muted-foreground mt-0.5">{sub}</p>}
    </CardContent>
  </Card>
);

export default function UserDashboard() {
  const api = useApi();
  const navigate = useNavigate();
  const [strategies, setStrategies] = useState([]);
  const [paperTrades, setPaperTrades] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/strategies").catch(() => ({ data: { strategies: [] } })),
      api.get("/paper-trades").catch(() => ({ data: { paper_trades: [] } })),
    ]).then(([sRes, pRes]) => {
      setStrategies(sRes.data.strategies || []);
      setPaperTrades(pRes.data.paper_trades || []);
    }).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activePT = paperTrades.filter((t) => t.status === "running");
  const completedPT = paperTrades.filter((t) => t.status === "completed");

  if (loading) {
    return <div className="flex items-center justify-center py-32"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-8" data-testid="user-dashboard">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">Your strategy development hub.</p>
      </div>

      {/* Quick Start */}
      <div data-testid="quick-start">
        <h2 className="mono-label text-[10px] mb-3">QUICK START</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Button variant="outline" className="h-auto p-4 justify-start gap-3 font-mono text-xs" onClick={() => navigate("/build")} data-testid="qs-build">
            <Hammer className="w-5 h-5 text-primary" />
            <div className="text-left">
              <p className="font-bold text-foreground">Build New Strategy</p>
              <p className="text-muted-foreground font-normal">AI-assisted strategy builder</p>
            </div>
          </Button>
          <Button variant="outline" className="h-auto p-4 justify-start gap-3 font-mono text-xs" onClick={() => navigate("/templates")} data-testid="qs-templates">
            <BookOpen className="w-5 h-5 text-primary" />
            <div className="text-left">
              <p className="font-bold text-foreground">Browse Templates</p>
              <p className="text-muted-foreground font-normal">12 pre-built strategies</p>
            </div>
          </Button>
          <Button variant="outline" className="h-auto p-4 justify-start gap-3 font-mono text-xs" onClick={() => navigate("/build?tab=screener")} data-testid="qs-scan">
            <Search className="w-5 h-5 text-primary" />
            <div className="text-left">
              <p className="font-bold text-foreground">Scan Stocks</p>
              <p className="text-muted-foreground font-normal">Screen with indicators</p>
            </div>
          </Button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="STRATEGIES" value={strategies.length} testId="stat-strategies" />
        <StatCard label="PAPER TRADES" value={paperTrades.length} testId="stat-paper-trades" />
        <StatCard label="ACTIVE TRADES" value={activePT.length} color={activePT.length > 0 ? "text-primary" : "text-foreground"} testId="stat-active" />
        <StatCard label="COMPLETED" value={completedPT.length} testId="stat-completed" />
      </div>

      {/* Your Strategies */}
      <div data-testid="strategies-section">
        <div className="flex items-center justify-between mb-3">
          <h2 className="mono-label text-[10px]">YOUR STRATEGIES</h2>
          <Link to="/build" className="text-[10px] font-mono text-primary flex items-center gap-1 hover:underline">New <ArrowRight className="w-3 h-3" /></Link>
        </div>
        {strategies.length === 0 ? (
          <Card className="border-border border-dashed bg-card/50" data-testid="empty-strategies">
            <CardContent className="p-8 text-center">
              <FolderOpen className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
              <h3 className="font-mono font-bold text-foreground mb-1">No strategies yet</h3>
              <p className="text-xs text-muted-foreground mb-4">Build your first strategy or clone a template.</p>
              <div className="flex gap-2 justify-center">
                <Button size="sm" className="font-mono text-[10px] uppercase gap-1.5" onClick={() => navigate("/build")} data-testid="cta-build-first">
                  <PlusCircle className="w-3 h-3" /> Build Strategy
                </Button>
                <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5" onClick={() => navigate("/templates")} data-testid="cta-browse-templates">
                  <BookOpen className="w-3 h-3" /> Browse Templates
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {strategies.slice(0, 8).map((s, i) => (
              <Card key={s.id || i} className="border-border bg-card hover:border-primary/30 transition-colors" data-testid={`strategy-row-${i}`}>
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="font-mono font-bold text-sm text-foreground truncate">{s.metadata?.name || "Unnamed"}</p>
                    <p className="text-[10px] text-muted-foreground font-mono">
                      {s.instrument?.symbol || "—"} · {s.timeframe?.interval || "—"} · {s.entry_conditions?.length || 0} conditions
                    </p>
                  </div>
                  <div className="flex items-center gap-2 ml-2">
                    <Button variant="outline" size="sm" className="h-7 font-mono text-[10px] gap-1" onClick={() => navigate(`/backtest/${s.id}`)} data-testid={`backtest-link-${i}`}>
                      <Play className="w-3 h-3" /> Backtest
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
            {strategies.length > 8 && (
              <p className="text-xs text-muted-foreground text-center mt-2">+ {strategies.length - 8} more strategies</p>
            )}
          </div>
        )}
      </div>

      {/* Paper Trades */}
      <div data-testid="paper-trades-section">
        <div className="flex items-center justify-between mb-3">
          <h2 className="mono-label text-[10px]">PAPER TRADES</h2>
          <Link to="/paper-trades" className="text-[10px] font-mono text-primary flex items-center gap-1 hover:underline">View all <ArrowRight className="w-3 h-3" /></Link>
        </div>
        {paperTrades.length === 0 ? (
          <Card className="border-border border-dashed bg-card/50">
            <CardContent className="p-6 text-center">
              <Activity className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-xs text-muted-foreground">No paper trades yet. Deploy a strategy to start simulated trading.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {paperTrades.slice(0, 4).map((pt) => {
              const pnl = pt.metrics?.total_pnl_pct || 0;
              const isUp = pnl >= 0;
              return (
                <Card key={pt.paper_trade_id} className="border-border bg-card" data-testid={`pt-card-${pt.paper_trade_id?.slice(0, 8)}`}>
                  <CardContent className="p-4 flex items-center justify-between">
                    <div>
                      <p className="font-mono text-sm font-bold text-foreground">{pt.settings?.symbol || "—"}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 ${pt.status === "running" ? "bg-primary/20 text-primary" : pt.status === "completed" ? "bg-blue-500/20 text-blue-400" : "bg-secondary text-muted-foreground"}`}>
                          {pt.status}
                        </span>
                        <span className="text-[10px] text-muted-foreground font-mono">{pt.total_trades || 0} trades</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center gap-1">
                        {isUp ? <TrendingUp className="w-3.5 h-3.5 text-primary" /> : <TrendingDown className="w-3.5 h-3.5 text-destructive" />}
                        <span className={`font-mono font-bold tabular-nums ${isUp ? "text-primary" : "text-destructive"}`}>
                          {isUp ? "+" : ""}{pnl.toFixed(2)}%
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
