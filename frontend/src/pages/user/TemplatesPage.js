import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Copy, Loader2, TrendingUp, Activity, ArrowDown, ArrowUp,
  Zap, Target, Clock, Layers, CheckCircle, BookOpen
} from "lucide-react";

const ICONS = { "Trend": TrendingUp, "Mean Reversion": ArrowDown, "Momentum": Zap, "Intraday": Clock, "Breakout": ArrowUp, "Volatility": Activity, "Combined": Layers };
const COLORS = { "Trend": "bg-blue-500/20 text-blue-400 border-blue-500/30", "Mean Reversion": "bg-purple-500/20 text-purple-400 border-purple-500/30", "Momentum": "bg-orange-500/20 text-orange-400 border-orange-500/30", "Intraday": "bg-yellow-500/20 text-yellow-400 border-yellow-500/30", "Breakout": "bg-primary/20 text-primary border-primary/30", "Volatility": "bg-red-500/20 text-red-400 border-red-500/30", "Combined": "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" };

const fmtConds = (c) => c?.map((x) => `${x.name} ${x.operator}${x.value != null ? ` ${x.value}` : ""}`).join(" + ") || "—";
const fmtRisk = (rm) => {
  const p = [];
  if (rm?.stop_loss) p.push(`SL: ${rm.stop_loss.value}%`);
  if (rm?.trailing_stop_loss?.enabled) p.push(`TSL: ${rm.trailing_stop_loss.value}%`);
  if (rm?.target_profit) p.push(`TP: ${rm.target_profit.value}%`);
  if (rm?.time_based_exit?.enabled) p.push(`Exit: ${rm.time_based_exit.exit_time}`);
  return p.join(" · ") || "None";
};

export default function TemplatesPage() {
  const api = useApi();
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [cloning, setCloning] = useState(null);
  const [cloned, setCloned] = useState({});
  const [symbols, setSymbols] = useState({});

  useEffect(() => {
    api.get("/templates").then((r) => setTemplates(r.data.templates || [])).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleClone = async (t) => {
    const sym = symbols[t.template_id] || t.instrument?.symbol || "RELIANCE";
    setCloning(t.template_id);
    try {
      const res = await api.post(`/template/${t.template_id}/clone`, { symbol: sym });
      if (res.data.success) {
        setCloned((p) => ({ ...p, [t.template_id]: res.data.strategy_id }));
      }
    } catch { /* ignore */ } finally { setCloning(null); }
  };

  const handleUseTemplate = (t) => {
    const sid = cloned[t.template_id];
    if (sid) navigate(`/backtest/${sid}`);
    else handleClone(t);
  };

  const categories = ["all", ...new Set(templates.map((t) => t.category))];
  const filtered = filter === "all" ? templates : templates.filter((t) => t.category === filter);

  if (loading) return <div className="flex items-center justify-center py-32"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-6" data-testid="templates-page">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Strategy Templates</h1>
        <p className="text-sm text-muted-foreground mt-1">Pre-built equity strategies. Clone and customize.</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2" data-testid="template-filters">
        {categories.map((c) => (
          <button key={c} onClick={() => setFilter(c)} className={`px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider border transition-colors ${filter === c ? "bg-primary/20 text-primary border-primary/30" : "bg-secondary/30 text-muted-foreground border-border hover:text-foreground"}`} data-testid={`filter-${c.toLowerCase().replace(/\s+/g, "-")}`}>
            {c === "all" ? `All (${templates.length})` : `${c} (${templates.filter((t) => t.category === c).length})`}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((t) => {
          const Icon = ICONS[t.category] || Target;
          const color = COLORS[t.category] || "bg-secondary text-muted-foreground border-border";
          const isCloned = !!cloned[t.template_id];

          return (
            <Card key={t.template_id} className="border-border bg-card hover:border-primary/30 transition-colors" data-testid={`tmpl-card-${t.template_id?.slice(0, 8)}`}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 flex items-center justify-center border ${color}`}><Icon className="w-4 h-4" /></div>
                    <div>
                      <h3 className="font-mono font-bold text-sm text-foreground">{t.name}</h3>
                      <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 border ${color}`}>{t.category}</span>
                    </div>
                  </div>
                  {t.clone_count > 0 && <span className="text-[10px] font-mono text-muted-foreground">{t.clone_count} clones</span>}
                </div>
                <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{t.description}</p>
                <div className="space-y-1 mb-3 text-xs font-mono">
                  <div className="flex gap-2"><span className="mono-label text-[10px] w-10">ENTRY</span><span className="text-foreground truncate">{fmtConds(t.entry_conditions)}</span></div>
                  <div className="flex gap-2"><span className="mono-label text-[10px] w-10">EXIT</span><span className="text-foreground truncate">{fmtConds(t.exit_conditions)}</span></div>
                  <div className="flex gap-2"><span className="mono-label text-[10px] w-10">RISK</span><span className="text-muted-foreground truncate">{fmtRisk(t.risk_management)}</span></div>
                </div>
                <div className="flex items-center gap-2 pt-3 border-t border-border/50">
                  <Select value={symbols[t.template_id] || t.instrument?.symbol || "RELIANCE"} onValueChange={(v) => setSymbols((p) => ({ ...p, [t.template_id]: v }))}>
                    <SelectTrigger className="h-8 font-mono text-xs w-28"><SelectValue /></SelectTrigger>
                    <SelectContent>{["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"].map((s) => <SelectItem key={s} value={s} className="font-mono text-xs">{s}</SelectItem>)}</SelectContent>
                  </Select>
                  <Button size="sm" className="flex-1 font-mono text-[10px] uppercase gap-1.5 h-8" onClick={() => handleUseTemplate(t)} disabled={cloning === t.template_id} data-testid={`use-tmpl-${t.template_id?.slice(0, 8)}`}>
                    {isCloned ? <><CheckCircle className="w-3 h-3" /> Open</> : cloning === t.template_id ? <Loader2 className="w-3 h-3 animate-spin" /> : <><Copy className="w-3 h-3" /> Use Template</>}
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
