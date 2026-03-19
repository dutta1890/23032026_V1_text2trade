import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import {
  Play, Pause, Square, Loader2, TrendingUp, TrendingDown,
  Activity, RefreshCw, ChevronDown, ChevronUp
} from "lucide-react";
import axios from "axios";
import BacktestResultsPanel from "./BacktestResultsPanel";

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const getAuthHeaders = () => {
  const token = localStorage.getItem("accessToken");
  return { headers: { Authorization: `Bearer ${token}` } };
};

const StatusBadge = ({ status }) => {
  const styles = {
    running: "bg-primary/20 text-primary",
    paused: "bg-yellow-500/20 text-yellow-500",
    completed: "bg-blue-500/20 text-blue-400",
    stopped: "bg-destructive/20 text-destructive",
  };
  return (
    <span className={`text-[10px] font-mono uppercase px-2 py-0.5 ${styles[status] || "bg-secondary text-muted-foreground"}`} data-testid={`status-badge-${status}`}>
      {status}
    </span>
  );
};

const DeployForm = ({ strategies, onDeploy, deploying }) => {
  const [selectedStrategy, setSelectedStrategy] = useState("");
  const [symbol, setSymbol] = useState("RELIANCE");
  const [lookbackDays, setLookbackDays] = useState("60");

  const handleDeploy = () => {
    if (!selectedStrategy) return;
    onDeploy({
      strategy_id: selectedStrategy,
      symbol,
      timeframe: "1d",
      initial_capital: 100000,
      lookback_days: parseInt(lookbackDays),
      slippage_pct: 0.05,
    });
  };

  return (
    <Card className="border-border bg-card border-dashed" data-testid="deploy-form">
      <CardContent className="p-6">
        <h3 className="font-mono font-bold text-foreground mb-4">Deploy Paper Trade</h3>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
          <div className="sm:col-span-1">
            <label className="mono-label text-[10px] mb-1 block">Strategy</label>
            <Select value={selectedStrategy} onValueChange={setSelectedStrategy}>
              <SelectTrigger className="font-mono text-sm" data-testid="select-strategy">
                <SelectValue placeholder="Select..." />
              </SelectTrigger>
              <SelectContent>
                {strategies.map((s) => (
                  <SelectItem key={s.id} value={s.id} className="font-mono text-sm">
                    {s.metadata?.name || s.id.slice(0, 8)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="mono-label text-[10px] mb-1 block">Symbol</label>
            <Select value={symbol} onValueChange={setSymbol}>
              <SelectTrigger className="font-mono text-sm" data-testid="select-symbol">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "KOTAKBANK", "LT"].map((s) => (
                  <SelectItem key={s} value={s} className="font-mono text-sm">{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="mono-label text-[10px] mb-1 block">Lookback</label>
            <Select value={lookbackDays} onValueChange={setLookbackDays}>
              <SelectTrigger className="font-mono text-sm" data-testid="select-lookback">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["30", "60", "90", "180", "365"].map((d) => (
                  <SelectItem key={d} value={d} className="font-mono text-sm">{d} days</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={handleDeploy} disabled={!selectedStrategy || deploying} className="font-mono text-xs uppercase gap-2" data-testid="deploy-paper-trade-btn">
            {deploying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {deploying ? "Deploying..." : "Deploy"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

const PaperTradeCard = ({ trade, onPause, onStop, onExpand, expanded }) => {
  const pnl = trade.metrics?.total_pnl_pct || 0;
  const isProfit = pnl >= 0;

  return (
    <Card className="border-border bg-card" data-testid={`paper-trade-card-${trade.paper_trade_id?.slice(0, 8)}`}>
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-8 h-8 flex items-center justify-center ${isProfit ? "bg-primary/20" : "bg-destructive/20"}`}>
              {isProfit ? <TrendingUp className="w-4 h-4 text-primary" /> : <TrendingDown className="w-4 h-4 text-destructive" />}
            </div>
            <div>
              <p className="font-mono text-sm font-bold text-foreground">
                {trade.settings?.symbol || "—"} · {trade.settings?.timeframe || "—"}
              </p>
              <p className="text-[10px] text-muted-foreground font-mono">
                ID: {trade.paper_trade_id?.slice(0, 12)}... · {trade.total_trades || 0} trades
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className={`font-mono text-lg font-bold tabular-nums ${isProfit ? "text-primary" : "text-destructive"}`}>
                {isProfit ? "+" : ""}{pnl.toFixed(2)}%
              </p>
              <p className="text-[10px] text-muted-foreground font-mono">
                Equity: ₹{(trade.final_equity || trade.settings?.initial_capital || 0).toLocaleString("en-IN")}
              </p>
            </div>
            <StatusBadge status={trade.status} />
            <div className="flex gap-1">
              {trade.status === "running" && (
                <Button variant="outline" size="icon" className="h-7 w-7" onClick={() => onPause(trade.paper_trade_id)} data-testid={`pause-btn-${trade.paper_trade_id?.slice(0, 8)}`}>
                  <Pause className="w-3 h-3" />
                </Button>
              )}
              {(trade.status === "running" || trade.status === "paused") && (
                <Button variant="outline" size="icon" className="h-7 w-7 hover:border-destructive hover:text-destructive" onClick={() => onStop(trade.paper_trade_id)} data-testid={`stop-btn-${trade.paper_trade_id?.slice(0, 8)}`}>
                  <Square className="w-3 h-3" />
                </Button>
              )}
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => onExpand(trade.paper_trade_id)} data-testid={`expand-btn-${trade.paper_trade_id?.slice(0, 8)}`}>
                {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </Button>
            </div>
          </div>
        </div>
        {trade.current_position && (
          <div className="mt-3 p-2 bg-yellow-500/10 border border-yellow-500/20">
            <p className="text-[10px] font-mono text-yellow-500 uppercase">Open Position</p>
            <p className="text-xs font-mono text-foreground">
              Entry: ₹{trade.current_position.entry_price} · Current: ₹{trade.current_position.current_price} ·
              <span className={trade.current_position.unrealized_pnl_pct >= 0 ? "text-primary" : "text-destructive"}>
                {" "}{trade.current_position.unrealized_pnl_pct >= 0 ? "+" : ""}{trade.current_position.unrealized_pnl_pct}%
              </span>
            </p>
          </div>
        )}
      </CardContent>
      {expanded && (
        <div className="border-t border-border p-4">
          <BacktestResultsPanel
            results={{
              ...trade,
              label: trade.label || "Paper Trade",
              data_source: "cached_nse",
              candles_processed: trade.equity_curve?.length || 0,
              success: true,
            }}
            onClose={() => onExpand(trade.paper_trade_id)}
          />
        </div>
      )}
    </Card>
  );
};

export default function PaperTradingContent({ strategies }) {
  const [paperTrades, setPaperTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deploying, setDeploying] = useState(false);
  const [expandedId, setExpandedId] = useState(null);

  const fetchPaperTrades = async () => {
    try {
      const res = await axios.get(`${API_URL}/v1/paper-trades`, getAuthHeaders());
      setPaperTrades(res.data.paper_trades || []);
    } catch (err) {
      console.error("Failed to fetch paper trades:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPaperTrades();
  }, []);

  const handleDeploy = async (params) => {
    setDeploying(true);
    try {
      await axios.post(`${API_URL}/v1/paper-trade/deploy`, params, getAuthHeaders());
      await fetchPaperTrades();
    } catch (err) {
      console.error("Deploy failed:", err);
    } finally {
      setDeploying(false);
    }
  };

  const handlePause = async (id) => {
    try {
      await axios.post(`${API_URL}/v1/paper-trade/${id}/pause`, {}, getAuthHeaders());
      await fetchPaperTrades();
    } catch (err) {
      console.error("Pause failed:", err);
    }
  };

  const handleStop = async (id) => {
    try {
      await axios.post(`${API_URL}/v1/paper-trade/${id}/stop`, {}, getAuthHeaders());
      await fetchPaperTrades();
    } catch (err) {
      console.error("Stop failed:", err);
    }
  };

  const handleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="space-y-6" data-testid="paper-trading-content">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Paper Trading</h1>
          <p className="text-muted-foreground mt-2">Simulate live execution using cached market data.</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchPaperTrades} className="font-mono text-xs uppercase gap-2" data-testid="refresh-paper-trades">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </Button>
      </div>

      {/* Deploy Form */}
      {strategies.length > 0 && (
        <DeployForm strategies={strategies} onDeploy={handleDeploy} deploying={deploying} />
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        <Card className="border-border bg-card" data-testid="pt-stat-total">
          <CardContent className="p-4">
            <span className="mono-label text-[10px]">Total</span>
            <p className="text-2xl font-mono font-bold text-foreground mt-1">{paperTrades.length}</p>
          </CardContent>
        </Card>
        <Card className="border-border bg-card" data-testid="pt-stat-running">
          <CardContent className="p-4">
            <span className="mono-label text-[10px]">Running</span>
            <p className="text-2xl font-mono font-bold text-primary mt-1">{paperTrades.filter(t => t.status === "running").length}</p>
          </CardContent>
        </Card>
        <Card className="border-border bg-card" data-testid="pt-stat-completed">
          <CardContent className="p-4">
            <span className="mono-label text-[10px]">Completed</span>
            <p className="text-2xl font-mono font-bold text-foreground mt-1">{paperTrades.filter(t => t.status === "completed").length}</p>
          </CardContent>
        </Card>
        <Card className="border-border bg-card" data-testid="pt-stat-stopped">
          <CardContent className="p-4">
            <span className="mono-label text-[10px]">Stopped</span>
            <p className="text-2xl font-mono font-bold text-muted-foreground mt-1">{paperTrades.filter(t => t.status === "stopped").length}</p>
          </CardContent>
        </Card>
      </div>

      {/* Paper Trades List */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      ) : paperTrades.length === 0 ? (
        <Card className="border-border border-dashed bg-card/50">
          <CardContent className="p-12 text-center">
            <Activity className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="font-mono font-bold text-lg text-foreground mb-2">No Paper Trades</h3>
            <p className="text-sm text-muted-foreground">Deploy a strategy above to start simulated trading.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {paperTrades.map((t) => (
            <PaperTradeCard
              key={t.paper_trade_id}
              trade={t}
              onPause={handlePause}
              onStop={handleStop}
              onExpand={handleExpand}
              expanded={expandedId === t.paper_trade_id}
            />
          ))}
        </div>
      )}
    </div>
  );
}
