import { useState } from "react";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from "recharts";
import { Loader2, Plus, X, TrendingUp } from "lucide-react";

const SYMBOLS = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "ITC", "HINDUNILVR"];
const fmt = (v) => v != null ? Number(v).toFixed(2) : "—";

const ChartTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div className="bg-card border border-border p-2 text-xs font-mono shadow-lg">
      <p className="text-foreground font-bold">{d?.symbol}</p>
      <p className="text-primary">P&L: {fmt(d?.pnl)}%</p>
      <p className="text-muted-foreground">Sharpe: {fmt(d?.sharpe)}</p>
      <p className="text-muted-foreground">Win Rate: {fmt(d?.winRate)}%</p>
    </div>
  );
};

export default function MultiStockCompare({ strategy }) {
  const api = useApi();
  const [symbols, setSymbols] = useState([]);
  const [addSym, setAddSym] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const addSymbol = () => {
    if (addSym && !symbols.includes(addSym) && symbols.length < 10) {
      setSymbols((p) => [...p, addSym]);
      setAddSym("");
    }
  };

  const removeSymbol = (s) => setSymbols((p) => p.filter((x) => x !== s));

  const handleCompare = async () => {
    if (symbols.length < 2 || !strategy) return;
    setLoading(true);
    setResults(null);
    try {
      const res = await api.post("/backtest/multi", {
        strategy,
        symbols,
        timeframe: strategy?.timeframe?.interval || "1d",
        initial_capital: 100000,
      });
      setResults(res.data);
    } catch (err) {
      setResults({ error: err.response?.data?.detail || "Comparison failed", results: [] });
    } finally {
      setLoading(false);
    }
  };

  const available = SYMBOLS.filter((s) => !symbols.includes(s));

  const chartData = results?.results
    ?.filter((r) => r.success !== false)
    ?.map((r) => ({
      symbol: r.symbol,
      pnl: r.metrics?.total_pnl_pct || 0,
      sharpe: r.metrics?.sharpe_ratio || 0,
      winRate: r.metrics?.win_rate || 0,
      trades: r.metrics?.total_trades || 0,
    })) || [];

  return (
    <Card className="border-border bg-card" data-testid="multi-stock-compare">
      <CardHeader className="py-3 px-4 border-b border-border">
        <CardTitle className="text-sm font-mono flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-primary" /> COMPARE ACROSS STOCKS
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4 space-y-4">
        {/* Symbol Picker */}
        <div className="flex flex-wrap items-center gap-2">
          {symbols.map((s) => (
            <span key={s} className="inline-flex items-center gap-1 text-xs font-mono px-2 py-1 bg-primary/15 text-primary border border-primary/20">
              {s}
              <button onClick={() => removeSymbol(s)} className="hover:text-destructive" data-testid={`remove-symbol-${s}`}>
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
          {symbols.length < 10 && (
            <div className="flex items-center gap-1">
              <Select value={addSym} onValueChange={setAddSym}>
                <SelectTrigger className="font-mono text-xs h-7 w-[130px]" data-testid="add-symbol-select">
                  <SelectValue placeholder="Add symbol" />
                </SelectTrigger>
                <SelectContent>
                  {available.map((s) => <SelectItem key={s} value={s} className="font-mono text-xs">{s}</SelectItem>)}
                </SelectContent>
              </Select>
              <Button variant="outline" size="icon" className="h-7 w-7" onClick={addSymbol} disabled={!addSym} data-testid="add-symbol-btn">
                <Plus className="w-3 h-3" />
              </Button>
            </div>
          )}
        </div>
        <p className="text-[10px] text-muted-foreground font-mono">{symbols.length}/10 symbols. Min 2 to compare.</p>

        <Button size="sm" onClick={handleCompare} disabled={symbols.length < 2 || loading} className="font-mono text-xs uppercase gap-2" data-testid="run-multi-compare-btn">
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <TrendingUp className="w-3 h-3" />}
          {loading ? "Comparing..." : "Compare"}
        </Button>

        {/* Results */}
        {results && !results.error && (
          <>
            <p className="text-[10px] text-muted-foreground font-mono">{results.successful}/{results.total_symbols} successful · Strategy: {results.strategy_name}</p>

            {/* P&L Bar Chart */}
            {chartData.length > 0 && (
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(240,4%,16%)" />
                    <XAxis dataKey="symbol" tick={{ fill: "hsl(240,5%,65%)", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} />
                    <YAxis tick={{ fill: "hsl(240,5%,65%)", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} tickFormatter={(v) => `${v}%`} />
                    <Tooltip content={<ChartTooltip />} />
                    <Bar dataKey="pnl" radius={[2, 2, 0, 0]}>
                      {chartData.map((d, i) => (
                        <Cell key={i} fill={d.pnl >= 0 ? "hsl(156,100%,45%)" : "hsl(0,84%,60%)"} fillOpacity={0.8} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Results Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left" data-testid="multi-compare-table">
                <thead>
                  <tr className="border-b border-border bg-secondary/30">
                    {["Symbol", "P&L %", "Win Rate", "Sharpe", "Trades", "Max DD"].map((h) => (
                      <th key={h} className="py-2 px-3 mono-label text-[10px]">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {results.results.map((r, i) => {
                    const m = r.metrics || {};
                    const pnl = m.total_pnl_pct || 0;
                    return (
                      <tr key={r.symbol} className="border-b border-border/50 hover:bg-secondary/20" data-testid={`multi-row-${i}`}>
                        <td className="py-2 px-3 font-mono text-xs font-bold text-foreground">{r.symbol}</td>
                        <td className={`py-2 px-3 font-mono text-xs font-bold tabular-nums ${pnl >= 0 ? "text-primary" : "text-destructive"}`}>{pnl >= 0 ? "+" : ""}{fmt(pnl)}%</td>
                        <td className="py-2 px-3 font-mono text-xs tabular-nums">{fmt(m.win_rate)}%</td>
                        <td className="py-2 px-3 font-mono text-xs tabular-nums">{fmt(m.sharpe_ratio)}</td>
                        <td className="py-2 px-3 font-mono text-xs tabular-nums">{m.total_trades || 0}</td>
                        <td className="py-2 px-3 font-mono text-xs tabular-nums text-destructive">{fmt(m.max_drawdown_pct)}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}

        {results?.error && (
          <p className="text-sm text-destructive font-mono">{results.error}</p>
        )}
      </CardContent>
    </Card>
  );
}
