import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from "recharts";
import { Loader2, GitCompare, X } from "lucide-react";

const SYMBOLS = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "ITC", "HINDUNILVR"];
const fmt = (v) => v != null ? Number(v).toFixed(2) : "—";

const CompareTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div className="bg-card border border-border p-2 text-xs font-mono shadow-lg">
      <p className="text-foreground font-bold">{d?.name}</p>
      <p className="text-primary">Sharpe: {fmt(d?.sharpe)}</p>
      <p className="text-muted-foreground">P&L: {fmt(d?.pnl)}%</p>
    </div>
  );
};

export default function StrategyCompare({ strategies = [], onClose }) {
  const api = useApi();
  const [symbol, setSymbol] = useState("RELIANCE");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleCompare = async () => {
    if (strategies.length < 2) return;
    setLoading(true);
    setResults(null);
    try {
      const res = await api.post("/backtest/compare", {
        strategies: strategies.map((s) => ({
          ...s,
          instrument: { ...(s.instrument || {}), symbol },
        })),
        symbol,
        timeframe: strategies[0]?.timeframe?.interval || "1d",
        initial_capital: 100000,
      });
      setResults(res.data);
    } catch (err) {
      setResults({ error: err.response?.data?.detail || "Comparison failed", results: [] });
    } finally {
      setLoading(false);
    }
  };

  const chartData = results?.results
    ?.filter((r) => r.success !== false)
    ?.map((r) => ({
      name: r.strategy_name?.length > 14 ? r.strategy_name.slice(0, 14) + "..." : r.strategy_name,
      sharpe: r.metrics?.sharpe_ratio || 0,
      pnl: r.metrics?.total_pnl_pct || 0,
      rank: r.rank,
    })) || [];

  return (
    <Card className="border-primary/30 bg-card" data-testid="strategy-compare">
      <CardHeader className="py-3 px-4 border-b border-border">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-mono flex items-center gap-2">
            <GitCompare className="w-4 h-4 text-primary" /> COMPARE {strategies.length} STRATEGIES
          </CardTitle>
          {onClose && (
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onClose} data-testid="close-compare-btn">
              <X className="w-3 h-3" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="p-4 space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          {strategies.map((s, i) => (
            <span key={s.id || i} className="text-[10px] font-mono px-2 py-1 bg-primary/10 text-primary border border-primary/20">
              {s.metadata?.name || `Strategy ${i + 1}`}
            </span>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <Select value={symbol} onValueChange={setSymbol}>
            <SelectTrigger className="font-mono text-xs h-8 w-[140px]" data-testid="compare-symbol-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SYMBOLS.map((s) => <SelectItem key={s} value={s} className="font-mono text-xs">{s}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button size="sm" onClick={handleCompare} disabled={loading} className="font-mono text-xs uppercase gap-2" data-testid="run-strategy-compare-btn">
            {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <GitCompare className="w-3 h-3" />}
            {loading ? "Comparing..." : "Run Comparison"}
          </Button>
        </div>

        {results && !results.error && (
          <>
            {results.best_strategy && (
              <p className="text-xs font-mono text-primary">
                Best: <span className="font-bold">{results.best_strategy}</span> (Sharpe: {fmt(results.best_sharpe)})
              </p>
            )}

            {chartData.length > 0 && (
              <div className="h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(240,4%,16%)" />
                    <XAxis dataKey="name" tick={{ fill: "hsl(240,5%,65%)", fontSize: 9, fontFamily: "JetBrains Mono" }} tickLine={false} />
                    <YAxis tick={{ fill: "hsl(240,5%,65%)", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} />
                    <Tooltip content={<CompareTooltip />} />
                    <Bar dataKey="sharpe" radius={[2, 2, 0, 0]}>
                      {chartData.map((d, i) => (
                        <Cell key={i} fill={d.rank === 1 ? "hsl(156,100%,45%)" : "hsl(240,4%,46%)"} fillOpacity={0.8} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full text-left" data-testid="compare-results-table">
                <thead>
                  <tr className="border-b border-border bg-secondary/30">
                    {["Rank", "Strategy", "Sharpe", "P&L %", "Win Rate", "Max DD", "Trades"].map((h) => (
                      <th key={h} className="py-2 px-3 mono-label text-[10px]">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {results.results.map((r, i) => {
                    const m = r.metrics || {};
                    const pnl = m.total_pnl_pct || 0;
                    return (
                      <tr key={i} className={`border-b border-border/50 hover:bg-secondary/20 ${r.rank === 1 ? "bg-primary/5" : ""}`} data-testid={`compare-row-${i}`}>
                        <td className="py-2 px-3 font-mono text-xs font-bold tabular-nums">{r.rank || "—"}</td>
                        <td className="py-2 px-3 font-mono text-xs text-foreground">{r.strategy_name}</td>
                        <td className={`py-2 px-3 font-mono text-xs font-bold tabular-nums ${(m.sharpe_ratio || 0) >= 1 ? "text-primary" : "text-foreground"}`}>{fmt(m.sharpe_ratio)}</td>
                        <td className={`py-2 px-3 font-mono text-xs font-bold tabular-nums ${pnl >= 0 ? "text-primary" : "text-destructive"}`}>{pnl >= 0 ? "+" : ""}{fmt(pnl)}%</td>
                        <td className="py-2 px-3 font-mono text-xs tabular-nums">{fmt(m.win_rate)}%</td>
                        <td className="py-2 px-3 font-mono text-xs tabular-nums text-destructive">{fmt(m.max_drawdown_pct)}%</td>
                        <td className="py-2 px-3 font-mono text-xs tabular-nums">{m.total_trades || 0}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}

        {results?.error && <p className="text-sm text-destructive font-mono">{results.error}</p>}
      </CardContent>
    </Card>
  );
}
