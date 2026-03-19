import { useState, useEffect } from "react";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  Database, Users, BarChart3, Activity, RefreshCw, Loader2,
  AlertTriangle, CheckCircle, Clock
} from "lucide-react";

const StatCard = ({ label, value, sub, icon: Icon, color = "text-foreground", testId }) => (
  <Card className="border-border bg-card" data-testid={testId}>
    <CardContent className="p-5">
      <div className="flex items-center justify-between mb-2">
        <span className="mono-label text-[10px]">{label}</span>
        {Icon && <Icon className={`w-4 h-4 ${color}`} />}
      </div>
      <p className={`text-2xl font-mono font-bold ${color} tabular-nums`}>{value}</p>
      {sub && <p className="text-[10px] text-muted-foreground mt-1">{sub}</p>}
    </CardContent>
  </Card>
);

export default function AdminDashboard() {
  const api = useApi();
  const [analytics, setAnalytics] = useState(null);
  const [dataStatus, setDataStatus] = useState(null);
  const [screenerStats, setScreenerStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchAll = async () => {
    const [aRes, dRes, sRes] = await Promise.all([
      api.get("/admin/analytics").catch(() => ({ data: {} })),
      api.get("/admin/data/status").catch(() => ({ data: {} })),
      api.get("/admin/screener/stats").catch(() => ({ data: {} })),
    ]);
    setAnalytics(aRes.data);
    setDataStatus(dRes.data);
    setScreenerStats(sRes.data);
    setLoading(false);
  };

  useEffect(() => {
    document.title = "Admin Dashboard | Text2trade";
    fetchAll();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await api.post("/admin/data/refresh", {});
      toast.success("Data refresh completed successfully");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Refresh failed");
    }
    await fetchAll();
    setRefreshing(false);
  };

  if (loading) return <div className="flex items-center justify-center py-32"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;

  const usage = analytics?.usage || {};
  const ds = dataStatus || {};
  const ss = screenerStats || {};
  const totalUsers = analytics?.users?.total || 0;
  const totalStrategies = analytics?.strategies?.total || 0;
  const totalCandles = analytics?.market_data?.total_candles || 0;
  const totalSymbols = analytics?.market_data?.symbols || 0;

  const staleCount = ds.stale_symbols?.length || 0;
  const isHealthy = staleCount === 0 && (totalCandles > 0 || (ds.total_candles || 0) > 0);

  return (
    <div className="space-y-8" data-testid="admin-dashboard">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Admin Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">System health and platform analytics.</p>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing} className="font-mono text-xs uppercase gap-2" data-testid="refresh-data-btn">
          {refreshing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />} {refreshing ? "Refreshing..." : "Refresh Data"}
        </Button>
      </div>

      {/* Data Health Banner */}
      <div className={`flex items-center gap-3 px-4 py-3 border ${isHealthy ? "border-primary/30 bg-primary/5" : "border-destructive/30 bg-destructive/5"}`} data-testid="data-health-banner">
        {isHealthy ? (
          <>
            <div className="w-2.5 h-2.5 rounded-full bg-signal-green animate-pulse" data-testid="health-indicator-green" />
            <span className="text-sm font-mono text-primary">Data Pipeline Healthy</span>
            <span className="text-[10px] font-mono text-muted-foreground ml-auto">{totalSymbols || ds.total_symbols || 0} symbols · {(totalCandles || ds.total_candles || 0).toLocaleString()} candles</span>
          </>
        ) : (
          <>
            <div className="w-2.5 h-2.5 rounded-full bg-signal-red animate-pulse" data-testid="health-indicator-red" />
            <span className="text-sm font-mono text-destructive">Data Pipeline Issues Detected</span>
            <span className="text-[10px] font-mono text-muted-foreground ml-auto">{staleCount} stale symbol{staleCount !== 1 ? "s" : ""}</span>
          </>
        )}
      </div>

      {/* Data Pipeline Health */}
      <div>
        <h2 className="mono-label text-[10px] mb-3">DATA PIPELINE</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard label="TOTAL SYMBOLS" value={totalSymbols || ds.total_symbols || 0} icon={Database} color="text-primary" testId="stat-symbols" />
          <StatCard label="TOTAL CANDLES" value={(totalCandles || ds.total_candles || 0).toLocaleString()} icon={BarChart3} testId="stat-candles" />
          <StatCard label="STALE SYMBOLS" value={staleCount} icon={staleCount > 0 ? AlertTriangle : CheckCircle} color={staleCount > 0 ? "text-yellow-500" : "text-primary"} testId="stat-stale" />
          <StatCard label="LAST REFRESH" value={ds.last_refresh ? new Date(ds.last_refresh).toLocaleDateString() : "Never"} icon={Clock} sub={ds.last_refresh ? new Date(ds.last_refresh).toLocaleTimeString() : ""} testId="stat-refresh" />
        </div>
        {ds.stale_symbols?.length > 0 && (
          <div className="mt-3 p-3 bg-yellow-500/10 border border-yellow-500/30">
            <p className="mono-label text-yellow-500 text-[10px] mb-1">STALE SYMBOLS</p>
            <p className="text-xs text-yellow-500/80 font-mono">{ds.stale_symbols.join(", ")}</p>
          </div>
        )}
        {ds.symbols && (
          <div className="mt-3">
            <h3 className="mono-label text-[10px] mb-2">PER-SYMBOL DATA</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
              {Object.entries(ds.symbols || {}).map(([sym, info]) => (
                <div key={sym} className="p-2 border border-border bg-secondary/20">
                  <p className="font-mono text-xs font-bold text-foreground">{sym}</p>
                  <p className="text-[10px] text-muted-foreground font-mono">{info.candle_count || info.count || 0} candles</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* User & Platform Stats */}
      <div>
        <h2 className="mono-label text-[10px] mb-3">PLATFORM STATS</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard label="TOTAL USERS" value={totalUsers} icon={Users} testId="stat-users" />
          <StatCard label="STRATEGIES" value={totalStrategies} icon={BarChart3} testId="stat-strategies" />
          <StatCard label="BACKTESTS" value={usage.backtests_run || 0} icon={Activity} testId="stat-backtests" />
          <StatCard label="AI CALLS TODAY" value={usage.ai_calls_today || 0} sub={`Week: ${usage.ai_calls_week || 0}`} testId="stat-ai-calls" />
        </div>
      </div>

      {/* Screener Analytics */}
      <div>
        <h2 className="mono-label text-[10px] mb-3">SCREENER ANALYTICS</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="border-border bg-card">
            <CardHeader className="py-3 px-4"><CardTitle className="text-xs font-mono text-muted-foreground">MOST RUN PRESETS</CardTitle></CardHeader>
            <CardContent className="px-4 pb-4">
              {ss.most_run_presets?.length > 0 ? (
                <div className="space-y-2">
                  {ss.most_run_presets.map((p) => (
                    <div key={p.preset} className="flex items-center justify-between py-1.5 border-b border-border/30">
                      <span className="text-xs font-mono text-foreground">{p.preset}</span>
                      <span className="text-xs font-mono font-bold text-primary tabular-nums">{p.count} runs</span>
                    </div>
                  ))}
                </div>
              ) : <p className="text-xs text-muted-foreground">No screener runs yet.</p>}
            </CardContent>
          </Card>
          <Card className="border-border bg-card">
            <CardHeader className="py-3 px-4"><CardTitle className="text-xs font-mono text-muted-foreground">MOST SCANNED SYMBOLS</CardTitle></CardHeader>
            <CardContent className="px-4 pb-4">
              {ss.most_scanned_symbols?.length > 0 ? (
                <div className="space-y-2">
                  {ss.most_scanned_symbols.slice(0, 10).map((s) => (
                    <div key={s.symbol} className="flex items-center justify-between py-1.5 border-b border-border/30">
                      <span className="text-xs font-mono text-foreground">{s.symbol}</span>
                      <span className="text-xs font-mono font-bold text-foreground tabular-nums">{s.match_count} matches</span>
                    </div>
                  ))}
                </div>
              ) : <p className="text-xs text-muted-foreground">No data yet.</p>}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
