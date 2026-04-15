import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import {
  Loader2, Copy, Shield, TrendingUp, Target, Clock, Eye, Users,
  Download, FileText, AlertTriangle, ArrowRight, ChevronDown,
} from "lucide-react";
import { toast } from "sonner";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";
const fmt = (v, d = 2) => v != null ? Number(v).toFixed(d) : "\u2014";

const ConditionRow = ({ cond, index }) => (
  <div className="flex items-center gap-3 py-2.5 px-3 bg-secondary/20 border border-border">
    <span className="text-[10px] font-mono text-muted-foreground w-5 tabular-nums">{index + 1}</span>
    <span className="font-mono text-sm font-bold text-primary">{cond.name || "\u2014"}</span>
    {cond.params && Object.keys(cond.params).length > 0 && (
      <span className="text-[10px] font-mono text-muted-foreground">
        ({Object.entries(cond.params).map(([k, v]) => `${k}=${v}`).join(", ")})
      </span>
    )}
    <span className="font-mono text-xs text-foreground">{cond.operator}</span>
    {cond.value != null && <span className="font-mono text-sm font-bold text-foreground tabular-nums">{cond.value}</span>}
  </div>
);

const MetricCard = ({ label, value, color = "text-foreground" }) => (
  <div className="p-3 bg-secondary/30 border border-border">
    <p className="mono-label text-[10px] mb-1">{label}</p>
    <p className={`font-mono font-bold text-lg ${color} tabular-nums`}>{value}</p>
  </div>
);

const BROKERS = ["zerodha", "angel_one", "upstox", "dhan", "groww", "5paisa"];
const BROKER_NAMES = { zerodha: "Zerodha Kite", angel_one: "Angel One", upstox: "Upstox", dhan: "Dhan", groww: "Groww", "5paisa": "5paisa" };

export default function ShareViewPage() {
  const { shareId } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated, token } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [cloning, setCloning] = useState(false);
  const [broker, setBroker] = useState(null);
  const [brokerData, setBrokerData] = useState(null);
  const [brokerLoading, setBrokerLoading] = useState(false);

  useEffect(() => {
    document.title = "Shared Strategy | Text2trade";
    axios.get(`${API}/s/${shareId}`)
      .then((r) => {
        setData(r.data);
        const name = r.data.strategy?.metadata?.name;
        if (name) document.title = `${name} | Text2trade`;
      })
      .catch(() => toast.error("Shared strategy not found"))
      .finally(() => setLoading(false));
  }, [shareId]);

  const handleClone = async () => {
    if (!isAuthenticated) {
      toast("Sign up to clone this strategy", { action: { label: "Sign Up", onClick: () => navigate("/register") } });
      return;
    }
    setCloning(true);
    try {
      const res = await axios.post(`${API}/s/${shareId}/clone`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.data.success) {
        toast.success("Strategy cloned to your account!");
        navigate(`/strategy/${res.data.strategy_id}`);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Clone failed");
    } finally {
      setCloning(false);
    }
  };

  const handleCopyText = async () => {
    try {
      const res = await axios.get(`${API}/s/${shareId}/copy-text`);
      await navigator.clipboard.writeText(res.data.text);
      toast.success("Copied to clipboard!");
    } catch {
      toast.error("Copy failed");
    }
  };

  const handlePdf = () => {
    window.open(`${API}/s/${shareId}/pdf`, "_blank");
  };

  const handleBroker = async (b) => {
    setBroker(b);
    setBrokerLoading(true);
    try {
      const res = await axios.get(`${API}/s/${shareId}/broker-instructions/${b}`);
      setBrokerData(res.data);
    } catch {
      toast.error("Failed to load broker instructions");
    } finally {
      setBrokerLoading(false);
    }
  };

  if (loading) return <div className="min-h-screen bg-background flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  if (!data) return null;

  const s = data.strategy || {};
  const entry = s.entry_conditions || [];
  const exit = s.exit_conditions || [];
  const rm = s.risk_management || {};
  const meta = s.metadata || {};
  const bt = data.backtest;
  const m = bt?.metrics || {};
  const equity = (bt?.equity_curve || []).map((p) => ({ date: p.timestamp?.split("T")[0], equity: p.equity }));

  return (
    <div className="min-h-screen bg-background" data-testid="share-view-page">
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-mono text-muted-foreground mb-1">SHARED STRATEGY</p>
            <h1 className="text-2xl font-bold text-foreground" data-testid="share-strategy-name">{meta.name || "Unnamed"}</h1>
            <div className="flex flex-wrap items-center gap-3 mt-2 text-[10px] font-mono text-muted-foreground">
              <span className="px-1.5 py-0.5 bg-primary/10 text-primary border border-primary/20">{s.instrument?.symbol || "\u2014"}</span>
              <span>{s.timeframe?.interval || "\u2014"}</span>
              <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {data.view_count} views</span>
              <span className="flex items-center gap-1"><Users className="w-3 h-3" /> {data.clone_count} clones</span>
              {data.strategy_version && <span>v{data.strategy_version}</span>}
            </div>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5" onClick={handleCopyText} data-testid="copy-text-btn">
              <Copy className="w-3 h-3" /> Copy Text
            </Button>
            <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5" onClick={handlePdf} data-testid="download-pdf-btn">
              <Download className="w-3 h-3" /> PDF
            </Button>
            <Button onClick={handleClone} disabled={cloning} className="font-mono text-[10px] uppercase gap-1.5" data-testid="clone-btn">
              {cloning ? <Loader2 className="w-3 h-3 animate-spin" /> : <Copy className="w-3 h-3" />}
              {isAuthenticated ? "Clone to My Account" : "Sign Up to Clone"}
            </Button>
          </div>
        </div>

        {meta.description && <p className="text-sm text-muted-foreground">{meta.description}</p>}

        {/* Strategy details */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="border-border bg-card lg:col-span-2">
            <CardHeader className="py-3 px-4 border-b border-border">
              <CardTitle className="text-sm font-mono flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary" /> ENTRY CONDITIONS
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-2">
              {entry.length > 0 ? entry.map((c, i) => <ConditionRow key={`entry-${c.name}-${i}`} cond={c} index={i} />) : <p className="text-xs text-muted-foreground">None</p>}
            </CardContent>
          </Card>
          <Card className="border-border bg-card">
            <CardHeader className="py-3 px-4 border-b border-border">
              <CardTitle className="text-sm font-mono flex items-center gap-2">
                <Shield className="w-4 h-4 text-primary" /> RISK
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-2">
              {rm.stop_loss && <div className="p-2 bg-secondary/20 border border-border"><p className="mono-label text-[10px]">STOP LOSS</p><p className="font-mono text-sm font-bold text-destructive">{rm.stop_loss.value}%</p></div>}
              {rm.target_profit && <div className="p-2 bg-secondary/20 border border-border"><p className="mono-label text-[10px]">TARGET</p><p className="font-mono text-sm font-bold text-primary">{rm.target_profit.value}%</p></div>}
              {rm.trailing_stop_loss?.enabled && <div className="p-2 bg-secondary/20 border border-border"><p className="mono-label text-[10px]">TRAILING SL</p><p className="font-mono text-sm font-bold text-yellow-500">{rm.trailing_stop_loss.value}%</p></div>}
              {!rm.stop_loss && !rm.target_profit && <p className="text-xs text-muted-foreground">No risk controls</p>}
            </CardContent>
          </Card>
        </div>

        {exit.length > 0 && (
          <Card className="border-border bg-card">
            <CardHeader className="py-3 px-4 border-b border-border"><CardTitle className="text-sm font-mono">EXIT CONDITIONS</CardTitle></CardHeader>
            <CardContent className="p-4 space-y-2">
              {exit.map((c, i) => <ConditionRow key={`exit-${c.name}-${i}`} cond={c} index={i} />)}
            </CardContent>
          </Card>
        )}

        {/* Backtest Results */}
        {bt && m.total_trades > 0 && (
          <>
            <Card className="border-border bg-card" data-testid="share-backtest-results">
              <CardHeader className="py-3 px-4 border-b border-border">
                <CardTitle className="text-sm font-mono">LATEST BACKTEST RESULTS</CardTitle>
              </CardHeader>
              <CardContent className="p-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <MetricCard label="TRADES" value={m.total_trades} />
                  <MetricCard label="WIN RATE" value={`${fmt(m.win_rate)}%`} />
                  <MetricCard label="TOTAL P&L" value={`${(m.total_pnl_pct || 0) >= 0 ? "+" : ""}${fmt(m.total_pnl_pct)}%`} color={(m.total_pnl_pct || 0) >= 0 ? "text-primary" : "text-destructive"} />
                  <MetricCard label="DRAWDOWN" value={`${fmt(m.max_drawdown_pct)}%`} color="text-destructive" />
                </div>
              </CardContent>
            </Card>
            {equity.length > 1 && (
              <Card className="border-border bg-card">
                <CardHeader className="py-3 px-4"><CardTitle className="text-sm font-mono">EQUITY CURVE</CardTitle></CardHeader>
                <CardContent className="p-0 pb-2 pr-4">
                  <ResponsiveContainer width="100%" height={180}>
                    <AreaChart data={equity} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                      <defs><linearGradient id="eqSh" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="hsl(156,100%,45%)" stopOpacity={0.3} /><stop offset="95%" stopColor="hsl(156,100%,45%)" stopOpacity={0} /></linearGradient></defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(240,4%,16%)" />
                      <XAxis dataKey="date" tick={{ fill: "hsl(240,5%,65%)", fontSize: 10 }} tickLine={false} axisLine={{ stroke: "hsl(240,4%,16%)" }} interval="preserveStartEnd" />
                      <YAxis tick={{ fill: "hsl(240,5%,65%)", fontSize: 10 }} tickLine={false} axisLine={{ stroke: "hsl(240,4%,16%)" }} tickFormatter={(v) => `\u20B9${(v / 1000).toFixed(0)}k`} />
                      <Tooltip />
                      <Area type="monotone" dataKey="equity" stroke="hsl(156,100%,45%)" strokeWidth={2} fill="url(#eqSh)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            )}
          </>
        )}

        {/* Broker Instructions */}
        <Card className="border-border bg-card" data-testid="broker-section">
          <CardHeader className="py-3 px-4 border-b border-border">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <FileText className="w-4 h-4 text-primary" /> HOW TO EXECUTE THIS STRATEGY
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground mb-3">Select your broker to get step-by-step execution instructions:</p>
            <div className="flex flex-wrap gap-2 mb-4">
              {BROKERS.map((b) => (
                <Button key={b} size="sm" variant={broker === b ? "default" : "outline"}
                  className="font-mono text-[10px] uppercase h-8"
                  onClick={() => handleBroker(b)}
                  data-testid={`broker-btn-${b}`}
                >
                  {BROKER_NAMES[b]}
                </Button>
              ))}
            </div>
            {brokerLoading && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
            {brokerData && !brokerLoading && (
              <div className="p-4 bg-secondary/30 border border-border space-y-3" data-testid="broker-instructions">
                <p className="text-sm font-mono font-bold text-foreground">How to place this trade on {brokerData.broker_name}:</p>
                <ol className="space-y-2">
                  {brokerData.steps.map((step, i) => (
                    <li key={`step-${i}`} className="flex gap-2 text-xs font-mono">
                      <span className="text-primary shrink-0">{i + 1}.</span>
                      <span className="text-foreground">{step}</span>
                    </li>
                  ))}
                </ol>
                {brokerData.note && (
                  <p className="text-[10px] font-mono text-muted-foreground italic border-l-2 border-primary/30 pl-2">{brokerData.note}</p>
                )}
                {brokerData.help_url && (
                  <a href={brokerData.help_url} target="_blank" rel="noopener noreferrer" className="text-[10px] font-mono text-primary hover:underline flex items-center gap-1">
                    Broker help documentation <ArrowRight className="w-3 h-3" />
                  </a>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Limitations Banner */}
        <Card className="border-amber-500/30 bg-amber-500/5" data-testid="limitations-banner">
          <CardContent className="p-4 flex gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-mono font-semibold text-amber-400 mb-1">What We Don't Handle</p>
              <ul className="text-xs text-muted-foreground space-y-1">
                <li>No live order execution — you must place orders manually on your broker</li>
                <li>Backtests use historical data with simplified fill assumptions</li>
                <li>Past performance does not guarantee future results</li>
                <li>No liquidity or market impact modeling</li>
                <li>This is for educational purposes only and is not financial advice</li>
              </ul>
              <Link to="/compliance" className="text-[10px] font-mono text-primary hover:underline mt-2 inline-block">
                Read our full methodology and compliance info
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* CTA */}
        {!isAuthenticated && (
          <Card className="border-primary/30 bg-primary/5" data-testid="signup-cta">
            <CardContent className="p-5 text-center">
              <p className="font-mono text-sm text-foreground mb-2">Want to use this strategy?</p>
              <p className="text-xs text-muted-foreground mb-3">Sign up to clone, backtest, and paper trade this strategy for free</p>
              <div className="flex justify-center gap-3">
                <Button asChild className="font-mono text-xs uppercase"><Link to="/register">Sign Up Free</Link></Button>
                <Button asChild variant="outline" className="font-mono text-xs uppercase"><Link to="/login">Login</Link></Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
