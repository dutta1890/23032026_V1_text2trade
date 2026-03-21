import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from "recharts";
import {
  Loader2, Zap, AlertTriangle, ArrowLeft, TrendingUp, Target,
  ChevronRight, Award, BarChart3, Info, Sparkles
} from "lucide-react";
import { toast } from "sonner";
import { PageSkeleton } from "@/components/LoadingSkeleton";

const fmt = (v, d = 2) => (v != null ? Number(v).toFixed(d) : "—");

const ImpactTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div className="bg-card border border-border p-2 text-xs font-mono shadow-lg">
      <p className="text-foreground font-bold">{d?.label}</p>
      <p className="text-primary">Impact: {fmt(d?.impact, 4)}</p>
      {d?.best != null && <p className="text-muted-foreground">Best value: {d.best}</p>}
    </div>
  );
};

const ResultTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div className="bg-card border border-border p-2 text-xs font-mono shadow-lg">
      <p className="text-foreground font-bold">#{d?.rank}</p>
      <p className="text-primary">Sharpe: {fmt(d?.sharpe)}</p>
      <p className="text-muted-foreground">P&L: {fmt(d?.pnl_pct)}%</p>
      <p className="text-muted-foreground">Win Rate: {fmt(d?.win_rate)}%</p>
    </div>
  );
};

export default function OptimizerPage() {
  const api = useApi();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialStrategyId = searchParams.get("strategy");

  const [strategies, setStrategies] = useState([]);
  const [selectedId, setSelectedId] = useState(initialStrategyId || "");
  const [tunables, setTunables] = useState([]);
  const [paramRanges, setParamRanges] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [optimizing, setOptimizing] = useState(false);

  useEffect(() => {
    document.title = "Optimizer | Text2trade";
    api.get("/strategies")
      .then((r) => {
        const strats = r.data.strategies || [];
        setStrategies(strats);
        if (initialStrategyId) detectParams(initialStrategyId);
      })
      .finally(() => setLoading(false));
  }, []);

  const detectParams = async (stratId) => {
    setDetecting(true);
    setTunables([]);
    setParamRanges([]);
    setResults(null);
    try {
      const res = await api.post("/optimizer/detect-params", { strategy_id: stratId });
      const t = res.data.tunables || [];
      setTunables(t);
      setParamRanges(t.map((p) => ({
        path: p.path,
        label: p.label,
        min: p.min,
        max: p.max,
        steps: 5,
        step_type: p.step_type,
        current: p.current,
      })));
    } catch (err) {
      toast.error("Failed to detect parameters");
    } finally {
      setDetecting(false);
    }
  };

  const handleSelectStrategy = (id) => {
    setSelectedId(id);
    if (id) detectParams(id);
  };

  const updateRange = (i, field, val) => {
    setParamRanges((p) => {
      const next = [...p];
      next[i] = { ...next[i], [field]: val };
      return next;
    });
  };

  const toggleParam = (i) => {
    setParamRanges((p) => {
      const next = [...p];
      next[i] = { ...next[i], _enabled: !next[i]._enabled };
      return next;
    });
  };

  const enabledParams = paramRanges.filter((p) => p._enabled !== false);

  const totalCombos = enabledParams.reduce((acc, p) => acc * (p.steps || 5), 1);

  const handleOptimize = async () => {
    if (!selectedId || enabledParams.length === 0) return;
    if (totalCombos > 500) {
      toast.error("Too many combinations. Reduce steps or parameters.");
      return;
    }
    setOptimizing(true);
    setResults(null);
    try {
      const res = await api.post("/optimizer/run", {
        strategy_id: selectedId,
        param_ranges: enabledParams.map((p) => ({
          path: p.path,
          label: p.label,
          min: p.min,
          max: p.max,
          steps: p.steps,
          step_type: p.step_type,
        })),
      });
      setResults(res.data);
      toast.success(`Optimization complete — ${res.data.total_combinations} combinations in ${res.data.elapsed_seconds}s`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Optimization failed");
    } finally {
      setOptimizing(false);
    }
  };

  if (loading) return <PageSkeleton />;

  const selectedStrat = strategies.find((s) => s.id === selectedId);

  // Charts data
  const top10 = (results?.results || []).slice(0, 10).map((r) => ({
    rank: r.rank,
    label: `#${r.rank}`,
    sharpe: r.sharpe,
    pnl_pct: r.pnl_pct,
    win_rate: r.win_rate,
  }));

  const impactData = (results?.param_impact || []).map((p) => ({
    label: p.label.length > 18 ? p.label.slice(0, 18) + "..." : p.label,
    impact: p.impact_score,
    best: p.best_value,
  }));

  return (
    <div className="space-y-6" data-testid="optimizer-page">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate("/dashboard")} data-testid="back-btn">
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Strategy Optimizer</h1>
          <p className="text-sm text-muted-foreground mt-1">Sweep parameter ranges to find the best combination.</p>
        </div>
      </div>

      {/* Strategy Selector */}
      <Card className="border-border bg-card" data-testid="strategy-selector">
        <CardContent className="p-5 space-y-4">
          <h3 className="mono-label text-[10px]">SELECT STRATEGY</h3>
          <Select value={selectedId} onValueChange={handleSelectStrategy}>
            <SelectTrigger className="font-mono text-xs" data-testid="strategy-select">
              <SelectValue placeholder="Choose a strategy to optimize..." />
            </SelectTrigger>
            <SelectContent>
              {strategies.map((s) => (
                <SelectItem key={s.id} value={s.id} className="font-mono text-xs">
                  {s.metadata?.name || "Unnamed"} — {s.instrument?.symbol || "—"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {selectedStrat && (
            <div className="flex flex-wrap gap-2 text-[10px] font-mono text-muted-foreground">
              <span className="px-1.5 py-0.5 bg-primary/10 text-primary border border-primary/20">{selectedStrat.instrument?.symbol}</span>
              <span>{selectedStrat.timeframe?.interval}</span>
              <span>{selectedStrat.entry_conditions?.length || 0} entry conditions</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Parameter Ranges */}
      {detecting && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" /> Detecting tunable parameters...
        </div>
      )}

      {paramRanges.length > 0 && (
        <Card className="border-border bg-card" data-testid="param-ranges">
          <CardHeader className="py-3 px-5 border-b border-border">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Target className="w-4 h-4 text-primary" /> PARAMETER RANGES
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-4">
            {paramRanges.map((pr, i) => (
              <div
                key={pr.path}
                className={`p-4 border transition-colors ${pr._enabled !== false ? "border-primary/30 bg-primary/5" : "border-border bg-secondary/10 opacity-60"}`}
                data-testid={`param-range-${i}`}
              >
                <div className="flex items-center justify-between mb-3">
                  <label className="flex items-center gap-2 cursor-pointer" onClick={() => toggleParam(i)}>
                    <input
                      type="checkbox"
                      checked={pr._enabled !== false}
                      onChange={() => toggleParam(i)}
                      className="accent-primary"
                      data-testid={`param-toggle-${i}`}
                    />
                    <span className="font-mono text-sm font-bold text-foreground">{pr.label}</span>
                  </label>
                  <span className="text-[10px] font-mono text-muted-foreground">
                    Current: <span className="text-primary">{pr.current}</span>
                  </span>
                </div>
                {pr._enabled !== false && (
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="mono-label text-[10px] mb-1 block">Min</label>
                      <Input type="number" step="0.1" className="h-8 font-mono text-xs" value={pr.min}
                        onChange={(e) => updateRange(i, "min", parseFloat(e.target.value) || 0)}
                        data-testid={`param-min-${i}`}
                      />
                    </div>
                    <div>
                      <label className="mono-label text-[10px] mb-1 block">Max</label>
                      <Input type="number" step="0.1" className="h-8 font-mono text-xs" value={pr.max}
                        onChange={(e) => updateRange(i, "max", parseFloat(e.target.value) || 0)}
                        data-testid={`param-max-${i}`}
                      />
                    </div>
                    <div>
                      <label className="mono-label text-[10px] mb-1 block">Steps</label>
                      <Input type="number" min={2} max={10} className="h-8 font-mono text-xs" value={pr.steps}
                        onChange={(e) => updateRange(i, "steps", Math.min(10, Math.max(2, parseInt(e.target.value) || 5)))}
                        data-testid={`param-steps-${i}`}
                      />
                    </div>
                  </div>
                )}
              </div>
            ))}

            {/* Combo count + Run button */}
            <div className="flex items-center justify-between pt-2">
              <div className="text-xs font-mono text-muted-foreground">
                <span className={totalCombos > 500 ? "text-destructive font-bold" : "text-foreground font-bold"}>{totalCombos}</span> combinations
                {totalCombos > 500 && <span className="text-destructive ml-2">(max 500)</span>}
              </div>
              <Button
                onClick={handleOptimize}
                disabled={!selectedId || enabledParams.length === 0 || optimizing || totalCombos > 500}
                className="font-mono text-xs uppercase gap-2"
                data-testid="run-optimizer-btn"
              >
                {optimizing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                {optimizing ? "Optimizing..." : "Run Optimizer"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {paramRanges.length === 0 && selectedId && !detecting && (
        <Card className="border-border border-dashed bg-card/50">
          <CardContent className="p-6 text-center">
            <Info className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm font-mono text-foreground mb-1">No tunable parameters detected</p>
            <p className="text-xs text-muted-foreground">This strategy has no numeric indicator params or risk values to optimize.</p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {results && (
        <div className="space-y-6" data-testid="optimizer-results">
          {/* Warnings */}
          {results.warnings?.length > 0 && (
            <div className="space-y-2">
              {results.warnings.map((w, i) => (
                <div key={i} className="flex items-start gap-2 px-4 py-3 bg-yellow-500/10 border border-yellow-500/30">
                  <AlertTriangle className="w-4 h-4 text-yellow-500 shrink-0 mt-0.5" />
                  <p className="text-xs font-mono text-yellow-500">{w}</p>
                </div>
              ))}
            </div>
          )}

          {/* Summary Banner */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3" data-testid="optimizer-summary">
            <Card className="border-border bg-card">
              <CardContent className="p-4">
                <p className="mono-label text-[10px]">COMBINATIONS</p>
                <p className="text-xl font-mono font-bold text-foreground tabular-nums">{results.total_combinations}</p>
                <p className="text-[10px] text-muted-foreground">{results.elapsed_seconds}s elapsed</p>
              </CardContent>
            </Card>
            <Card className="border-border bg-card">
              <CardContent className="p-4">
                <p className="mono-label text-[10px]">BASELINE SHARPE</p>
                <p className="text-xl font-mono font-bold text-muted-foreground tabular-nums">{fmt(results.baseline?.sharpe)}</p>
              </CardContent>
            </Card>
            <Card className="border-primary/30 bg-primary/5">
              <CardContent className="p-4">
                <p className="mono-label text-[10px] text-primary">BEST SHARPE</p>
                <p className="text-xl font-mono font-bold text-primary tabular-nums">{fmt(results.results?.[0]?.sharpe)}</p>
              </CardContent>
            </Card>
            <Card className="border-border bg-card">
              <CardContent className="p-4">
                <p className="mono-label text-[10px]">IMPROVEMENT</p>
                {(() => {
                  const base = results.baseline?.sharpe || 0;
                  const best = results.results?.[0]?.sharpe || 0;
                  const diff = best - base;
                  return (
                    <p className={`text-xl font-mono font-bold tabular-nums ${diff > 0 ? "text-primary" : diff < 0 ? "text-destructive" : "text-foreground"}`}>
                      {diff > 0 ? "+" : ""}{fmt(diff)}
                    </p>
                  );
                })()}
              </CardContent>
            </Card>
          </div>

          {/* Top 10 Sharpe Chart */}
          {top10.length > 0 && (
            <Card className="border-border bg-card">
              <CardHeader className="py-3 px-4 border-b border-border">
                <CardTitle className="text-sm font-mono flex items-center gap-2">
                  <Award className="w-4 h-4 text-primary" /> TOP 10 BY SHARPE RATIO
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4">
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={top10} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(240,4%,16%)" />
                      <XAxis dataKey="label" tick={{ fill: "hsl(240,5%,65%)", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} />
                      <YAxis tick={{ fill: "hsl(240,5%,65%)", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} />
                      <Tooltip content={<ResultTooltip />} />
                      <Bar dataKey="sharpe" radius={[2, 2, 0, 0]}>
                        {top10.map((d, i) => (
                          <Cell key={i} fill={i === 0 ? "hsl(156,100%,45%)" : "hsl(240,4%,46%)"} fillOpacity={0.8} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Parameter Impact */}
          {impactData.length > 1 && (
            <Card className="border-border bg-card">
              <CardHeader className="py-3 px-4 border-b border-border">
                <CardTitle className="text-sm font-mono flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-primary" /> PARAMETER IMPACT
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4">
                <p className="text-[10px] text-muted-foreground font-mono mb-3">Which parameter moves the needle most on Sharpe ratio.</p>
                <div className="h-[160px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={impactData} layout="vertical" margin={{ top: 5, right: 5, left: 80, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(240,4%,16%)" />
                      <XAxis type="number" tick={{ fill: "hsl(240,5%,65%)", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} />
                      <YAxis type="category" dataKey="label" tick={{ fill: "hsl(240,5%,65%)", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} width={80} />
                      <Tooltip content={<ImpactTooltip />} />
                      <Bar dataKey="impact" radius={[0, 2, 2, 0]} fill="hsl(156,100%,45%)" fillOpacity={0.7} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Results Table */}
          <Card className="border-border bg-card">
            <CardHeader className="py-3 px-4 border-b border-border">
              <CardTitle className="text-sm font-mono">RANKED RESULTS (TOP {results.results?.length})</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left" data-testid="optimizer-results-table">
                  <thead>
                    <tr className="border-b border-border bg-secondary/30">
                      <th className="py-2 px-3 mono-label text-[10px]">Rank</th>
                      <th className="py-2 px-3 mono-label text-[10px]">Sharpe</th>
                      <th className="py-2 px-3 mono-label text-[10px]">P&L %</th>
                      <th className="py-2 px-3 mono-label text-[10px]">Win Rate</th>
                      <th className="py-2 px-3 mono-label text-[10px]">Max DD</th>
                      <th className="py-2 px-3 mono-label text-[10px]">Trades</th>
                      <th className="py-2 px-3 mono-label text-[10px]">Parameters</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Baseline row */}
                    <tr className="border-b border-yellow-500/30 bg-yellow-500/5" data-testid="baseline-row">
                      <td className="py-2 px-3 font-mono text-xs text-yellow-500">BASE</td>
                      <td className="py-2 px-3 font-mono text-xs tabular-nums text-yellow-500">{fmt(results.baseline?.sharpe)}</td>
                      <td className="py-2 px-3 font-mono text-xs tabular-nums text-yellow-500">{fmt(results.baseline?.pnl_pct)}%</td>
                      <td className="py-2 px-3 font-mono text-xs tabular-nums">{fmt(results.baseline?.win_rate)}%</td>
                      <td className="py-2 px-3 font-mono text-xs tabular-nums">{fmt(results.baseline?.max_drawdown)}%</td>
                      <td className="py-2 px-3 font-mono text-xs tabular-nums">{results.baseline?.total_trades}</td>
                      <td className="py-2 px-3 font-mono text-[10px] text-muted-foreground italic">Original params</td>
                    </tr>
                    {(results.results || []).slice(0, 20).map((r, i) => {
                      const isBest = r.rank === 1;
                      return (
                        <tr key={i} className={`border-b border-border/50 hover:bg-secondary/20 ${isBest ? "bg-primary/5" : ""}`} data-testid={`result-row-${i}`}>
                          <td className="py-2 px-3 font-mono text-xs font-bold tabular-nums">
                            {isBest && <Award className="w-3 h-3 text-primary inline mr-1" />}
                            {r.rank}
                          </td>
                          <td className={`py-2 px-3 font-mono text-xs font-bold tabular-nums ${isBest ? "text-primary" : "text-foreground"}`}>{fmt(r.sharpe)}</td>
                          <td className={`py-2 px-3 font-mono text-xs tabular-nums ${r.pnl_pct >= 0 ? "text-primary" : "text-destructive"}`}>
                            {r.pnl_pct >= 0 ? "+" : ""}{fmt(r.pnl_pct)}%
                          </td>
                          <td className="py-2 px-3 font-mono text-xs tabular-nums">{fmt(r.win_rate)}%</td>
                          <td className="py-2 px-3 font-mono text-xs tabular-nums text-destructive">{fmt(r.max_drawdown)}%</td>
                          <td className="py-2 px-3 font-mono text-xs tabular-nums">{r.total_trades}</td>
                          <td className="py-2 px-3">
                            <div className="flex flex-wrap gap-1">
                              {Object.entries(r.params || {}).map(([k, v]) => (
                                <span key={k} className="text-[10px] font-mono px-1 py-0.5 bg-secondary text-muted-foreground border border-border">
                                  {k}: {typeof v === "number" ? v.toFixed(2) : v}
                                </span>
                              ))}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Apply Best Params CTA */}
          {results.results?.length > 0 && results.results[0].sharpe > (results.baseline?.sharpe || 0) && (
            <Card className="border-primary/30 bg-primary/5" data-testid="apply-best-card">
              <CardContent className="p-5 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-primary" />
                    <p className="font-mono text-sm font-bold text-foreground">Better parameters found</p>
                  </div>
                  <p className="text-xs text-muted-foreground font-mono">
                    Sharpe improved from {fmt(results.baseline?.sharpe)} to {fmt(results.results[0].sharpe)} ({fmt((results.results[0].sharpe - (results.baseline?.sharpe || 0)), 2)} improvement)
                  </p>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {Object.entries(results.results[0].params || {}).map(([k, v]) => (
                      <span key={k} className="text-[10px] font-mono px-1.5 py-0.5 bg-primary/15 text-primary border border-primary/20">
                        {k}: {typeof v === "number" ? v.toFixed(2) : v}
                      </span>
                    ))}
                  </div>
                </div>
                <Button
                  size="sm"
                  className="font-mono text-[10px] uppercase gap-1.5 shrink-0 ml-4"
                  onClick={() => {
                    toast.success("Best params applied! Edit your strategy to save changes.", { duration: 4000 });
                    navigate(`/build?edit=${selectedId}`);
                  }}
                  data-testid="apply-best-btn"
                >
                  <ChevronRight className="w-3 h-3" /> Apply & Edit
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
