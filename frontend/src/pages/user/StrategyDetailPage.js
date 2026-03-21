import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Loader2, ArrowLeft, Play, Activity, Pencil, Trash2,
  ChevronRight, Shield, Clock, Target, TrendingUp, Zap
} from "lucide-react";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { toast } from "sonner";

const ConditionRow = ({ cond, index }) => {
  const name = cond.name || "—";
  const op = cond.operator || "—";
  const val = cond.value;
  const params = cond.params || {};
  const paramStr = Object.entries(params).map(([k, v]) => `${k}=${v}`).join(", ");

  return (
    <div className="flex items-center gap-3 py-2.5 px-3 bg-secondary/20 border border-border" data-testid={`condition-row-${index}`}>
      <span className="text-[10px] font-mono text-muted-foreground w-5 tabular-nums">{index + 1}</span>
      <span className="font-mono text-sm font-bold text-primary">{name}</span>
      {paramStr && <span className="text-[10px] font-mono text-muted-foreground">({paramStr})</span>}
      <span className="font-mono text-xs text-foreground">{op}</span>
      {val !== undefined && val !== null && <span className="font-mono text-sm font-bold text-foreground tabular-nums">{val}</span>}
    </div>
  );
};

const RiskItem = ({ label, value, icon: Icon, color = "text-foreground" }) => (
  <div className="flex items-center gap-3 py-2 px-3 bg-secondary/20 border border-border">
    {Icon && <Icon className={`w-4 h-4 ${color}`} />}
    <div>
      <p className="mono-label text-[10px]">{label}</p>
      <p className={`font-mono text-sm font-bold ${color}`}>{value}</p>
    </div>
  </div>
);

export default function StrategyDetailPage() {
  const { strategyId } = useParams();
  const api = useApi();
  const navigate = useNavigate();
  const [strategy, setStrategy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    document.title = "Strategy | Text2trade";
    api.get(`/strategy/${strategyId}`)
      .then((r) => {
        const s = r.data.strategy || r.data;
        setStrategy(s);
        if (s?.metadata?.name) document.title = `${s.metadata.name} | Text2trade`;
      })
      .catch(() => {
        toast.error("Strategy not found");
        navigate("/dashboard");
      })
      .finally(() => setLoading(false));
  }, [strategyId]);

  const handleDelete = async () => {
    if (!window.confirm("Delete this strategy? This cannot be undone.")) return;
    setDeleting(true);
    try {
      await api.del(`/strategy/${strategyId}`);
      toast.success("Strategy deleted");
      navigate("/dashboard");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Delete failed");
    } finally {
      setDeleting(false);
    }
  };

  if (loading) return <PageSkeleton />;
  if (!strategy) return null;

  const rm = strategy.risk_management || {};
  const entry = strategy.entry_conditions || [];
  const exit = strategy.exit_conditions || [];
  const instrument = strategy.instrument || {};
  const timeframe = strategy.timeframe || {};
  const meta = strategy.metadata || {};

  return (
    <div className="space-y-6" data-testid="strategy-detail-page">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/dashboard")} data-testid="back-btn">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-foreground">{meta.name || "Unnamed Strategy"}</h1>
            <div className="flex flex-wrap items-center gap-2 mt-1">
              <span className="text-[10px] font-mono px-1.5 py-0.5 bg-primary/15 text-primary border border-primary/20">{instrument.symbol || "—"}</span>
              <span className="text-[10px] font-mono text-muted-foreground">{timeframe.interval || "—"}</span>
              {strategy.version && <span className="text-[10px] font-mono text-muted-foreground">v{strategy.version}</span>}
              {meta.created_at && <span className="text-[10px] font-mono text-muted-foreground">{new Date(meta.created_at).toLocaleDateString()}</span>}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button size="sm" className="font-mono text-[10px] uppercase gap-1.5" onClick={() => navigate(`/backtest/${strategyId}`)} data-testid="run-backtest-btn">
            <Play className="w-3 h-3" /> Run Backtest
          </Button>
          <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5" onClick={() => navigate(`/optimizer?strategy=${strategyId}`)} data-testid="optimize-btn">
            <Zap className="w-3 h-3" /> Optimize
          </Button>
          <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5" onClick={() => navigate(`/build?edit=${strategyId}`)} data-testid="edit-btn">
            <Pencil className="w-3 h-3" /> Edit
          </Button>
          <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5 text-destructive hover:text-destructive" onClick={handleDelete} disabled={deleting} data-testid="delete-btn">
            {deleting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />} Delete
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Entry Conditions */}
        <Card className="border-border bg-card lg:col-span-2">
          <CardHeader className="py-3 px-4 border-b border-border">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" /> ENTRY CONDITIONS
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-2">
            {entry.length > 0 ? entry.map((c, i) => (
              <ConditionRow key={i} cond={c} index={i} />
            )) : (
              <p className="text-xs text-muted-foreground py-2">No entry conditions defined.</p>
            )}
          </CardContent>
        </Card>

        {/* Risk Management */}
        <Card className="border-border bg-card">
          <CardHeader className="py-3 px-4 border-b border-border">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Shield className="w-4 h-4 text-primary" /> RISK MANAGEMENT
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-2">
            {rm.stop_loss && (
              <RiskItem label="STOP LOSS" value={`${rm.stop_loss.value}% (${rm.stop_loss.type})`} icon={Target} color="text-destructive" />
            )}
            {rm.target_profit && (
              <RiskItem label="TARGET PROFIT" value={`${rm.target_profit.value}% (${rm.target_profit.type})`} icon={Target} color="text-primary" />
            )}
            {rm.trailing_stop_loss?.enabled && (
              <RiskItem label="TRAILING STOP" value={`${rm.trailing_stop_loss.value}%`} icon={TrendingUp} color="text-yellow-500" />
            )}
            {rm.time_based_exit?.enabled && (
              <RiskItem label="TIME EXIT" value={rm.time_based_exit.exit_time || "15:10"} icon={Clock} />
            )}
            {!rm.stop_loss && !rm.target_profit && !rm.trailing_stop_loss?.enabled && !rm.time_based_exit?.enabled && (
              <p className="text-xs text-muted-foreground py-2">No risk controls configured.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Exit Conditions */}
      {exit.length > 0 && (
        <Card className="border-border bg-card">
          <CardHeader className="py-3 px-4 border-b border-border">
            <CardTitle className="text-sm font-mono">EXIT CONDITIONS</CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-2">
            {exit.map((c, i) => <ConditionRow key={i} cond={c} index={i} />)}
          </CardContent>
        </Card>
      )}

      {/* Raw JSON Preview */}
      <Card className="border-border bg-card">
        <CardHeader className="py-3 px-4 border-b border-border cursor-pointer" data-testid="json-toggle">
          <CardTitle className="text-sm font-mono text-muted-foreground flex items-center gap-2">
            RAW STRATEGY JSON
            <ChevronRight className="w-3 h-3" />
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <pre className="text-[10px] font-mono text-muted-foreground overflow-auto whitespace-pre-wrap max-h-64 p-3 bg-secondary/20 border border-border" data-testid="strategy-json">
            {JSON.stringify(strategy, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
