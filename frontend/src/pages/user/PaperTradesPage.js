import { useState, useEffect } from "react";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Play, Pause, Square, Loader2, TrendingUp, TrendingDown,
  Activity, RefreshCw, ChevronDown, ChevronUp
} from "lucide-react";

const StatusBadge = ({ status }) => {
  const s = { running: "bg-primary/20 text-primary", paused: "bg-yellow-500/20 text-yellow-500", completed: "bg-blue-500/20 text-blue-400", stopped: "bg-destructive/20 text-destructive" };
  return <span className={`text-[10px] font-mono uppercase px-2 py-0.5 ${s[status] || "bg-secondary text-muted-foreground"}`} data-testid={`badge-${status}`}>{status}</span>;
};

export default function PaperTradesPage() {
  const api = useApi();
  const [paperTrades, setPaperTrades] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deploying, setDeploying] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [selStrategy, setSelStrategy] = useState("");
  const [selSymbol, setSelSymbol] = useState("RELIANCE");
  const [selLookback, setSelLookback] = useState("60");

  const fetchAll = async () => {
    const [ptRes, sRes] = await Promise.all([
      api.get("/paper-trades").catch(() => ({ data: { paper_trades: [] } })),
      api.get("/strategies").catch(() => ({ data: { strategies: [] } })),
    ]);
    setPaperTrades(ptRes.data.paper_trades || []);
    setStrategies(sRes.data.strategies || []);
    setLoading(false);
  };

  useEffect(() => { fetchAll(); // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDeploy = async () => {
    if (!selStrategy) return;
    setDeploying(true);
    try {
      await api.post("/paper-trade/deploy", { strategy_id: selStrategy, symbol: selSymbol, timeframe: "1d", initial_capital: 100000, lookback_days: parseInt(selLookback) });
      await fetchAll();
    } catch { /* ignore */ } finally { setDeploying(false); }
  };

  const handlePause = async (id) => { await api.post(`/paper-trade/${id}/pause`, {}); fetchAll(); };
  const handleStop = async (id) => { await api.post(`/paper-trade/${id}/stop`, {}); fetchAll(); };

  const running = paperTrades.filter((t) => t.status === "running").length;
  const completed = paperTrades.filter((t) => t.status === "completed").length;

  if (loading) return <div className="flex items-center justify-center py-32"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-6" data-testid="paper-trades-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Paper Trades</h1>
          <p className="text-sm text-muted-foreground mt-1">Simulate live execution using cached market data.</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchAll} className="font-mono text-xs uppercase gap-2" data-testid="refresh-btn"><RefreshCw className="w-3.5 h-3.5" /> Refresh</Button>
      </div>

      {/* Deploy Form */}
      {strategies.length > 0 && (
        <Card className="border-border border-dashed bg-card" data-testid="deploy-form">
          <CardContent className="p-5">
            <h3 className="font-mono font-bold text-foreground text-sm mb-3">Deploy Paper Trade</h3>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
              <Select value={selStrategy} onValueChange={setSelStrategy}>
                <SelectTrigger className="font-mono text-xs" data-testid="pt-select-strategy"><SelectValue placeholder="Strategy..." /></SelectTrigger>
                <SelectContent>{strategies.map((s) => <SelectItem key={s.id} value={s.id} className="font-mono text-xs">{s.metadata?.name || s.id.slice(0, 8)}</SelectItem>)}</SelectContent>
              </Select>
              <Select value={selSymbol} onValueChange={setSelSymbol}>
                <SelectTrigger className="font-mono text-xs" data-testid="pt-select-symbol"><SelectValue /></SelectTrigger>
                <SelectContent>{["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN"].map((s) => <SelectItem key={s} value={s} className="font-mono text-xs">{s}</SelectItem>)}</SelectContent>
              </Select>
              <Select value={selLookback} onValueChange={setSelLookback}>
                <SelectTrigger className="font-mono text-xs" data-testid="pt-select-lookback"><SelectValue /></SelectTrigger>
                <SelectContent>{["30", "60", "90", "180"].map((d) => <SelectItem key={d} value={d} className="font-mono text-xs">{d} days</SelectItem>)}</SelectContent>
              </Select>
              <Button onClick={handleDeploy} disabled={!selStrategy || deploying} className="font-mono text-xs uppercase gap-2" data-testid="pt-deploy-btn">
                {deploying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />} Deploy
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="border-border bg-card" data-testid="pt-stat-total"><CardContent className="p-4"><span className="mono-label text-[10px]">Total</span><p className="text-2xl font-mono font-bold text-foreground mt-1">{paperTrades.length}</p></CardContent></Card>
        <Card className="border-border bg-card" data-testid="pt-stat-running"><CardContent className="p-4"><span className="mono-label text-[10px]">Running</span><p className="text-2xl font-mono font-bold text-primary mt-1">{running}</p></CardContent></Card>
        <Card className="border-border bg-card" data-testid="pt-stat-completed"><CardContent className="p-4"><span className="mono-label text-[10px]">Completed</span><p className="text-2xl font-mono font-bold text-foreground mt-1">{completed}</p></CardContent></Card>
        <Card className="border-border bg-card" data-testid="pt-stat-stopped"><CardContent className="p-4"><span className="mono-label text-[10px]">Stopped</span><p className="text-2xl font-mono font-bold text-muted-foreground mt-1">{paperTrades.filter((t) => t.status === "stopped").length}</p></CardContent></Card>
      </div>

      {/* List */}
      {paperTrades.length === 0 ? (
        <Card className="border-border border-dashed bg-card/50"><CardContent className="p-10 text-center"><Activity className="w-10 h-10 text-muted-foreground mx-auto mb-3" /><h3 className="font-mono font-bold text-foreground mb-1">No Paper Trades</h3><p className="text-xs text-muted-foreground">Deploy a strategy to start.</p></CardContent></Card>
      ) : (
        <div className="space-y-3">
          {paperTrades.map((pt) => {
            const pnl = pt.metrics?.total_pnl_pct || 0;
            const isUp = pnl >= 0;
            const isExpanded = expandedId === pt.paper_trade_id;
            return (
              <Card key={pt.paper_trade_id} className="border-border bg-card" data-testid={`pt-card-${pt.paper_trade_id?.slice(0, 8)}`}>
                <CardContent className="p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="font-mono text-sm font-bold text-foreground">{pt.settings?.symbol || "—"} · {pt.settings?.timeframe || "—"}</p>
                      <p className="text-[10px] text-muted-foreground font-mono">{pt.total_trades || 0} trades · ID: {pt.paper_trade_id?.slice(0, 12)}...</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <div className="flex items-center gap-1">{isUp ? <TrendingUp className="w-3.5 h-3.5 text-primary" /> : <TrendingDown className="w-3.5 h-3.5 text-destructive" />}<span className={`font-mono font-bold tabular-nums ${isUp ? "text-primary" : "text-destructive"}`}>{isUp ? "+" : ""}{pnl.toFixed(2)}%</span></div>
                        <p className="text-[10px] text-muted-foreground font-mono">Eq: {"\u20B9"}{(pt.final_equity || pt.settings?.initial_capital || 0).toLocaleString("en-IN")}</p>
                      </div>
                      <StatusBadge status={pt.status} />
                      <div className="flex gap-1">
                        {pt.status === "running" && <Button variant="outline" size="icon" className="h-7 w-7" onClick={() => handlePause(pt.paper_trade_id)} data-testid={`pause-${pt.paper_trade_id?.slice(0, 8)}`}><Pause className="w-3 h-3" /></Button>}
                        {(pt.status === "running" || pt.status === "paused") && <Button variant="outline" size="icon" className="h-7 w-7" onClick={() => handleStop(pt.paper_trade_id)} data-testid={`stop-${pt.paper_trade_id?.slice(0, 8)}`}><Square className="w-3 h-3" /></Button>}
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setExpandedId(isExpanded ? null : pt.paper_trade_id)} data-testid={`expand-${pt.paper_trade_id?.slice(0, 8)}`}>{isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}</Button>
                      </div>
                    </div>
                  </div>
                  {pt.current_position && (
                    <div className="mt-3 p-2 bg-yellow-500/10 border border-yellow-500/20">
                      <p className="text-[10px] font-mono text-yellow-500 uppercase">Open Position</p>
                      <p className="text-xs font-mono text-foreground">Entry: {"\u20B9"}{pt.current_position.entry_price} · Unrealized: <span className={pt.current_position.unrealized_pnl_pct >= 0 ? "text-primary" : "text-destructive"}>{pt.current_position.unrealized_pnl_pct >= 0 ? "+" : ""}{pt.current_position.unrealized_pnl_pct}%</span></p>
                    </div>
                  )}
                </CardContent>
                {isExpanded && pt.equity_curve?.length > 0 && (
                  <div className="border-t border-border p-4">
                    <h4 className="mono-label text-[10px] mb-2">EQUITY CURVE</h4>
                    <ResponsiveContainer width="100%" height={160}>
                      <AreaChart data={pt.equity_curve.map((e) => ({ date: e.timestamp?.split("T")[0], equity: e.equity }))} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(240,4%,16%)" />
                        <XAxis dataKey="date" tick={{ fill: "hsl(240,5%,65%)", fontSize: 9 }} tickLine={false} interval="preserveStartEnd" />
                        <YAxis tick={{ fill: "hsl(240,5%,65%)", fontSize: 9 }} tickLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                        <Area type="monotone" dataKey="equity" stroke="hsl(156,100%,45%)" strokeWidth={1.5} fill="hsl(156,100%,45%)" fillOpacity={0.1} />
                      </AreaChart>
                    </ResponsiveContainer>
                    {pt.trades?.length > 0 && (
                      <div className="mt-3">
                        <h4 className="mono-label text-[10px] mb-2">TRADES ({pt.trades.length})</h4>
                        <div className="overflow-x-auto">
                          <table className="w-full text-left"><thead><tr className="border-b border-border">{["#", "Entry", "Exit", "P&L", "Reason"].map((h) => <th key={h} className="py-1 px-2 mono-label text-[10px]">{h}</th>)}</tr></thead>
                            <tbody>{pt.trades.slice(0, 10).map((t, i) => <tr key={i} className="border-b border-border/30"><td className="py-1 px-2 font-mono text-[10px]">{i + 1}</td><td className="py-1 px-2 font-mono text-[10px]">{t.entry_time?.split("T")[0]}</td><td className="py-1 px-2 font-mono text-[10px]">{t.exit_time?.split("T")[0]}</td><td className={`py-1 px-2 font-mono text-[10px] ${t.pnl_percent >= 0 ? "text-primary" : "text-destructive"}`}>{t.pnl_percent >= 0 ? "+" : ""}{t.pnl_percent?.toFixed(2)}%</td><td className="py-1 px-2 font-mono text-[10px] text-muted-foreground">{t.exit_reason}</td></tr>)}</tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
