import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import {
  Search, Loader2, Hammer, TrendingUp, Zap, ChevronDown, ChevronUp,
  Plus, Trash2, Filter, Bookmark
} from "lucide-react";
import { toast } from "sonner";

const SYMBOLS = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "ITC", "HINDUNILVR"];
const INDICATORS = ["RSI", "SMA", "EMA", "MACD", "ADX", "VWAP", "Bollinger", "Supertrend", "Stochastic", "ATR"];
const OPERATORS = [">", "<", ">=", "<=", "=", "bullish_cross", "bearish_cross", "squeeze"];

export default function ScreenerPage() {
  const api = useApi();
  const navigate = useNavigate();
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState("");
  const [customConditions, setCustomConditions] = useState([]);
  const [showCustom, setShowCustom] = useState(false);
  const [results, setResults] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [loadingPresets, setLoadingPresets] = useState(true);

  useEffect(() => {
    document.title = "Screener | Text2trade";
    api.get("/screener/presets")
      .then((r) => setPresets(r.data.presets || []))
      .catch((e) => console.error("Failed to load presets", e))
      .finally(() => setLoadingPresets(false));
  }, [api]);

  const addCondition = () => {
    setCustomConditions((p) => [...p, { name: "RSI", params: { period: 14 }, operator: "<", value: 30 }]);
  };

  const updateCondition = (i, field, val) => {
    setCustomConditions((p) => {
      const next = [...p];
      if (field === "name") {
        next[i] = { ...next[i], name: val };
        if (val === "SMA" || val === "EMA") next[i].params = { short: 50, long: 200 };
        else if (val === "MACD") next[i].params = { fast: 12, slow: 26, signal: 9 };
        else if (val === "Bollinger") next[i].params = { period: 20, std_dev: 2 };
        else if (val === "ADX") next[i].params = { period: 14 };
        else if (val === "RSI") next[i].params = { period: 14 };
        else if (val === "Stochastic") next[i].params = { k_period: 14, d_period: 3 };
        else if (val === "ATR") next[i].params = { period: 14 };
        else next[i].params = {};
      } else if (field === "operator") {
        next[i] = { ...next[i], operator: val };
      } else if (field === "value") {
        next[i] = { ...next[i], value: parseFloat(val) || 0 };
      } else if (field.startsWith("params.")) {
        const pKey = field.replace("params.", "");
        next[i] = { ...next[i], params: { ...next[i].params, [pKey]: parseFloat(val) || 0 } };
      }
      return next;
    });
  };

  const removeCondition = (i) => setCustomConditions((p) => p.filter((_, idx) => idx !== i));

  const handleScan = async () => {
    setScanning(true);
    setResults(null);
    try {
      const body = showCustom && customConditions.length > 0
        ? { conditions: customConditions }
        : { preset: selectedPreset };
      const res = await api.post("/screener/scan", body);
      setResults(res.data);
    } catch (err) {
      setResults({ error: err.response?.data?.detail || "Scan failed", matches: [] });
    } finally {
      setScanning(false);
    }
  };

  const canScan = showCustom ? customConditions.length > 0 : !!selectedPreset;

  return (
    <div className="space-y-6" data-testid="screener-page">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Stock Screener</h1>
        <p className="text-sm text-muted-foreground mt-1">Scan stocks with indicator-based conditions.</p>
      </div>

      {/* Mode Toggle */}
      <div className="flex items-center gap-3">
        <Button
          variant={!showCustom ? "default" : "outline"}
          size="sm"
          className="font-mono text-xs uppercase gap-1.5"
          onClick={() => setShowCustom(false)}
          data-testid="preset-mode-btn"
        >
          <Filter className="w-3 h-3" /> Presets
        </Button>
        <Button
          variant={showCustom ? "default" : "outline"}
          size="sm"
          className="font-mono text-xs uppercase gap-1.5"
          onClick={() => setShowCustom(true)}
          data-testid="custom-mode-btn"
        >
          <Hammer className="w-3 h-3" /> Custom Scan
        </Button>
      </div>

      {/* Preset Selector */}
      {!showCustom && (
        <Card className="border-border bg-card" data-testid="preset-panel">
          <CardContent className="p-5">
            <h3 className="mono-label text-[10px] mb-3">SELECT PRESET</h3>
            {loadingPresets ? (
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {presets.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setSelectedPreset(p.id)}
                    className={`text-left p-4 border transition-colors ${selectedPreset === p.id ? "border-primary bg-primary/10" : "border-border bg-secondary/20 hover:border-primary/40"}`}
                    data-testid={`preset-${p.id}`}
                  >
                    <p className="font-mono text-sm font-bold text-foreground">{p.name}</p>
                    <p className="text-[11px] text-muted-foreground mt-1">{p.description}</p>
                    <p className="text-[10px] font-mono text-primary mt-2">{p.conditions_count} condition{p.conditions_count !== 1 ? "s" : ""}</p>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Custom Scan Builder */}
      {showCustom && (
        <Card className="border-border bg-card" data-testid="custom-scan-panel">
          <CardHeader className="py-3 px-5">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-mono">CUSTOM CONDITIONS</CardTitle>
              <Button variant="outline" size="sm" className="font-mono text-[10px] gap-1" onClick={addCondition} data-testid="add-condition-btn">
                <Plus className="w-3 h-3" /> Add
              </Button>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-5 space-y-3">
            {customConditions.length === 0 && (
              <p className="text-xs text-muted-foreground text-center py-4">No conditions added. Click "Add" to build your custom scan.</p>
            )}
            {customConditions.map((c, i) => (
              <div key={i} className="flex flex-wrap items-end gap-2 p-3 bg-secondary/20 border border-border" data-testid={`condition-${i}`}>
                <div className="flex-1 min-w-[120px]">
                  <label className="mono-label text-[10px] mb-1 block">Indicator</label>
                  <Select value={c.name} onValueChange={(v) => updateCondition(i, "name", v)}>
                    <SelectTrigger className="font-mono text-xs h-8"><SelectValue /></SelectTrigger>
                    <SelectContent>{INDICATORS.map((ind) => <SelectItem key={ind} value={ind} className="font-mono text-xs">{ind}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="w-[100px]">
                  <label className="mono-label text-[10px] mb-1 block">Operator</label>
                  <Select value={c.operator} onValueChange={(v) => updateCondition(i, "operator", v)}>
                    <SelectTrigger className="font-mono text-xs h-8"><SelectValue /></SelectTrigger>
                    <SelectContent>{OPERATORS.map((op) => <SelectItem key={op} value={op} className="font-mono text-xs">{op}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                {!["bullish_cross", "bearish_cross", "squeeze"].includes(c.operator) && (
                  <div className="w-[80px]">
                    <label className="mono-label text-[10px] mb-1 block">Value</label>
                    <Input type="number" step="0.1" className="h-8 font-mono text-xs" value={c.value || ""} onChange={(e) => updateCondition(i, "value", e.target.value)} data-testid={`condition-value-${i}`} />
                  </div>
                )}
                {c.params && Object.keys(c.params).map((pk) => (
                  <div key={pk} className="w-[80px]">
                    <label className="mono-label text-[10px] mb-1 block">{pk}</label>
                    <Input type="number" className="h-8 font-mono text-xs" value={c.params[pk] || ""} onChange={(e) => updateCondition(i, `params.${pk}`, e.target.value)} />
                  </div>
                ))}
                <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => removeCondition(i)} data-testid={`remove-condition-${i}`}>
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Scan Button */}
      <Button onClick={handleScan} disabled={!canScan || scanning} className="font-mono text-xs uppercase gap-2" data-testid="run-scan-btn">
        {scanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
        {scanning ? "Scanning..." : "Run Scan"}
      </Button>

      {/* Results */}
      {results && (
        <div data-testid="screener-results">
          {results.error && !results.matches?.length && (
            <Card className="border-destructive/30 bg-destructive/5">
              <CardContent className="p-4">
                <p className="text-sm text-destructive font-mono">{results.error}</p>
              </CardContent>
            </Card>
          )}

          {/* Scan Meta */}
          <div className="flex flex-wrap gap-4 mb-4 text-xs font-mono text-muted-foreground">
            {results.preset_name && <span>Preset: <span className="text-primary">{results.preset_name}</span></span>}
            <span>Scanned: <span className="text-foreground">{results.total_scanned || 0}</span></span>
            <span>Matches: <span className="text-primary font-bold">{results.match_count || 0}</span></span>
            <span>Time: <span className="text-foreground">{results.scan_time_ms || 0}ms</span></span>
          </div>

          {/* Results Table */}
          {results.matches?.length > 0 ? (
            <Card className="border-border bg-card">
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-left" data-testid="results-table">
                    <thead>
                      <tr className="border-b border-border bg-secondary/30">
                        <th className="py-3 px-4 mono-label text-[10px]">Symbol</th>
                        <th className="py-3 px-4 mono-label text-[10px]">Close</th>
                        <th className="py-3 px-4 mono-label text-[10px]">Indicators</th>
                        <th className="py-3 px-4 mono-label text-[10px]">Timeframe</th>
                        <th className="py-3 px-4 mono-label text-[10px]">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.matches.map((m, i) => (
                        <tr key={m.symbol} className="border-b border-border/50 hover:bg-secondary/20 transition-colors" data-testid={`result-row-${i}`}>
                          <td className="py-3 px-4">
                            <span className="font-mono text-sm font-bold text-foreground">{m.symbol}</span>
                          </td>
                          <td className="py-3 px-4 font-mono text-sm tabular-nums text-foreground">
                            {m.indicator_values?.close ? `\u20B9${m.indicator_values.close.toLocaleString("en-IN")}` : "—"}
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex flex-wrap gap-1.5">
                              {Object.entries(m.indicator_values || {}).filter(([k]) => k !== "close").map(([k, v]) => (
                                <span key={k} className="text-[10px] font-mono px-1.5 py-0.5 bg-primary/10 text-primary border border-primary/20">
                                  {k}: {typeof v === "number" ? v.toFixed(2) : v}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="py-3 px-4 font-mono text-xs text-muted-foreground">{m.timeframe}</td>
                          <td className="py-3 px-4">
                            <div className="flex gap-1">
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-7 font-mono text-[10px] gap-1"
                                onClick={() => navigate(`/build?symbol=${m.symbol}`)}
                                data-testid={`build-strategy-${m.symbol}`}
                              >
                                <Hammer className="w-3 h-3" /> Build
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 font-mono text-[10px] gap-1"
                                onClick={async () => {
                                  try {
                                    await api.post("/watchlist", {
                                      symbol: m.symbol,
                                      note: results.preset_name || "Custom scan",
                                      preset_name: results.preset_name || null,
                                      indicator_values: m.indicator_values,
                                    });
                                    toast.success(`${m.symbol} added to watchlist`);
                                  } catch (err) {
                                    const msg = err.response?.data?.detail || "Failed";
                                    toast.error(msg);
                                  }
                                }}
                                data-testid={`watch-${m.symbol}`}
                              >
                                <Bookmark className="w-3 h-3" /> Watch
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          ) : results.match_count === 0 && !results.error ? (
            <Card className="border-border border-dashed bg-card/50">
              <CardContent className="p-8 text-center">
                <Search className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                <p className="font-mono font-bold text-foreground mb-1">No matches found</p>
                <p className="text-xs text-muted-foreground">Try a different preset or adjust your conditions.</p>
              </CardContent>
            </Card>
          ) : null}
        </div>
      )}
    </div>
  );
}
