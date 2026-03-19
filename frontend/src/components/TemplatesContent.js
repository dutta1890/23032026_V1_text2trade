import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import {
  Copy, Loader2, TrendingUp, Activity, ArrowDown, ArrowUp,
  Zap, Target, BarChart3, Clock, Layers, CheckCircle
} from "lucide-react";
import axios from "axios";

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const getAuthHeaders = () => {
  const token = localStorage.getItem("accessToken");
  return { headers: { Authorization: `Bearer ${token}` } };
};

const CATEGORY_ICONS = {
  "Trend": TrendingUp,
  "Mean Reversion": ArrowDown,
  "Momentum": Zap,
  "Intraday": Clock,
  "Breakout": ArrowUp,
  "Volatility": Activity,
  "Combined": Layers,
};

const CATEGORY_COLORS = {
  "Trend": "bg-blue-500/20 text-blue-400 border-blue-500/30",
  "Mean Reversion": "bg-purple-500/20 text-purple-400 border-purple-500/30",
  "Momentum": "bg-orange-500/20 text-orange-400 border-orange-500/30",
  "Intraday": "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  "Breakout": "bg-primary/20 text-primary border-primary/30",
  "Volatility": "bg-red-500/20 text-red-400 border-red-500/30",
  "Combined": "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
};

const formatConditions = (conditions) => {
  if (!conditions || conditions.length === 0) return "—";
  return conditions.map(c => {
    const name = c.name || "?";
    const op = c.operator || "";
    const val = c.value !== undefined && c.value !== null ? ` ${c.value}` : "";
    return `${name} ${op}${val}`;
  }).join(" + ");
};

const formatRisk = (rm) => {
  const parts = [];
  if (rm?.stop_loss) parts.push(`SL: ${rm.stop_loss.value}% (${rm.stop_loss.type})`);
  if (rm?.trailing_stop_loss?.enabled) parts.push(`TSL: ${rm.trailing_stop_loss.value}%`);
  if (rm?.target_profit) parts.push(`TP: ${rm.target_profit.value}%`);
  if (rm?.time_based_exit?.enabled) parts.push(`Exit: ${rm.time_based_exit.exit_time}`);
  return parts.length > 0 ? parts.join(" · ") : "No risk controls";
};

const TemplateCard = ({ template, onClone, cloning }) => {
  const [selectedSymbol, setSelectedSymbol] = useState(template.instrument?.symbol || "RELIANCE");
  const [cloned, setCloned] = useState(false);
  const Icon = CATEGORY_ICONS[template.category] || BarChart3;
  const colorClass = CATEGORY_COLORS[template.category] || "bg-secondary text-muted-foreground border-border";

  const handleClone = async () => {
    const result = await onClone(template.template_id, selectedSymbol);
    if (result) setCloned(true);
  };

  return (
    <Card className="border-border bg-card hover:border-primary/30 transition-colors" data-testid={`template-card-${template.template_id?.slice(0, 8)}`}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 flex items-center justify-center border ${colorClass}`}>
              <Icon className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-mono font-bold text-foreground text-sm">{template.name}</h3>
              <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 border ${colorClass}`}>
                {template.category}
              </span>
            </div>
          </div>
          {template.clone_count > 0 && (
            <span className="text-[10px] font-mono text-muted-foreground">{template.clone_count} clones</span>
          )}
        </div>

        <p className="text-xs text-muted-foreground mb-3">{template.description}</p>

        <div className="space-y-1.5 mb-3">
          <div className="flex items-center gap-2">
            <span className="mono-label text-[10px] w-12">ENTRY</span>
            <span className="text-xs font-mono text-foreground">{formatConditions(template.entry_conditions)}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="mono-label text-[10px] w-12">EXIT</span>
            <span className="text-xs font-mono text-foreground">{formatConditions(template.exit_conditions)}</span>
          </div>
          {template.filters?.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="mono-label text-[10px] w-12">FILTER</span>
              <span className="text-xs font-mono text-foreground">{formatConditions(template.filters)}</span>
            </div>
          )}
          <div className="flex items-center gap-2">
            <span className="mono-label text-[10px] w-12">RISK</span>
            <span className="text-xs font-mono text-muted-foreground">{formatRisk(template.risk_management)}</span>
          </div>
        </div>

        <div className="flex items-center gap-2 pt-3 border-t border-border/50">
          <Select value={selectedSymbol} onValueChange={setSelectedSymbol}>
            <SelectTrigger className="h-8 font-mono text-xs w-32" data-testid={`template-symbol-${template.template_id?.slice(0, 8)}`}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "KOTAKBANK", "LT", "WIPRO", "TATAMOTORS"].map((s) => (
                <SelectItem key={s} value={s} className="font-mono text-xs">{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            onClick={handleClone}
            disabled={cloning || cloned}
            className="flex-1 font-mono text-[10px] uppercase gap-1.5 h-8"
            data-testid={`clone-btn-${template.template_id?.slice(0, 8)}`}
          >
            {cloned ? <><CheckCircle className="w-3 h-3" /> Cloned</> :
             cloning ? <Loader2 className="w-3 h-3 animate-spin" /> :
             <><Copy className="w-3 h-3" /> Clone to My Strategies</>}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default function TemplatesContent({ onStrategyCreated }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [cloning, setCloning] = useState(null);
  const [filterCategory, setFilterCategory] = useState("all");

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const res = await axios.get(`${API_URL}/v1/templates`);
      setTemplates(res.data.templates || []);
    } catch (err) {
      console.error("Failed to fetch templates:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleClone = async (templateId, symbol) => {
    setCloning(templateId);
    try {
      const res = await axios.post(
        `${API_URL}/v1/template/${templateId}/clone`,
        { symbol },
        getAuthHeaders()
      );
      if (res.data.success) {
        if (onStrategyCreated) onStrategyCreated();
        return true;
      }
    } catch (err) {
      console.error("Clone failed:", err);
    } finally {
      setCloning(null);
    }
    return false;
  };

  const categories = ["all", ...new Set(templates.map(t => t.category))];
  const filtered = filterCategory === "all" ? templates : templates.filter(t => t.category === filterCategory);

  return (
    <div className="space-y-6" data-testid="templates-content">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Strategy Templates</h1>
        <p className="text-muted-foreground mt-2">Pre-built strategies you can clone and customize. All equity-focused.</p>
      </div>

      {/* Category Filter */}
      <div className="flex flex-wrap gap-2" data-testid="template-filters">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setFilterCategory(cat)}
            className={`px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider border transition-colors ${
              filterCategory === cat
                ? "bg-primary/20 text-primary border-primary/30"
                : "bg-secondary/30 text-muted-foreground border-border hover:text-foreground"
            }`}
            data-testid={`filter-${cat.toLowerCase().replace(/\s+/g, "-")}`}
          >
            {cat === "all" ? `All (${templates.length})` : `${cat} (${templates.filter(t => t.category === cat).length})`}
          </button>
        ))}
      </div>

      {/* Template Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((t) => (
            <TemplateCard
              key={t.template_id}
              template={t}
              onClone={handleClone}
              cloning={cloning === t.template_id}
            />
          ))}
        </div>
      )}
    </div>
  );
}
