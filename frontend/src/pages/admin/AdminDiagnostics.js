import React, { useState, useEffect, useCallback, useRef } from "react";
import { useApi } from "@/hooks/useApi";
import { extractApiError } from "@/utils/apiError";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import {
  AlertTriangle, Activity, Users, Clock, CheckCircle2,
  RefreshCw, Loader2, ChevronDown, ChevronUp, Zap, X,
} from "lucide-react";
import { toast } from "sonner";

// ── Severity badge ──────────────────────────────────────────────────────────
const SEV_COLORS = {
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
  high: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  medium: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  low: "bg-blue-500/20 text-blue-400 border-blue-500/30",
};

function SeverityBadge({ severity }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-mono uppercase border ${SEV_COLORS[severity] || SEV_COLORS.low}`} data-testid={`severity-badge-${severity}`}>
      {severity}
    </span>
  );
}

// ── Stat card ───────────────────────────────────────────────────────────────
function StatCard({ label, value, icon: Icon, color = "text-foreground", testId }) {
  return (
    <Card className="border-border bg-card" data-testid={testId}>
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">{label}</span>
          {Icon && <Icon className={`w-4 h-4 ${color}`} />}
        </div>
        <p className={`text-2xl font-mono font-bold ${color} tabular-nums`}>{value}</p>
      </CardContent>
    </Card>
  );
}

// ── Error detail modal ──────────────────────────────────────────────────────
function ErrorDetailModal({ error, onClose, onResolve }) {
  const [note, setNote] = useState("");
  const [resolving, setResolving] = useState(false);

  if (!error) return null;

  const handleResolve = async () => {
    setResolving(true);
    await onResolve(error.error_id, note);
    setResolving(false);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-card border border-border w-full max-w-2xl max-h-[80vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()} data-testid="error-detail-modal">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-mono font-bold text-foreground">Error Detail</h3>
          <button onClick={onClose} data-testid="close-error-modal"><X className="w-4 h-4 text-muted-foreground hover:text-foreground" /></button>
        </div>

        <div className="space-y-3 text-xs font-mono">
          <div className="flex gap-2 items-center">
            <SeverityBadge severity={error.severity} />
            <span className="text-muted-foreground">{error.source}</span>
            {error.resolved && <Badge variant="outline" className="text-[10px] text-green-400 border-green-500/30">Resolved</Badge>}
          </div>
          <div><span className="text-muted-foreground">ID:</span> <span className="text-foreground">{error.error_id}</span></div>
          <div><span className="text-muted-foreground">Time:</span> <span className="text-foreground">{new Date(error.timestamp).toLocaleString()}</span></div>
          <div><span className="text-muted-foreground">Type:</span> <span className="text-foreground">{error.error_type}</span></div>
          <div><span className="text-muted-foreground">Endpoint:</span> <span className="text-foreground">{error.method} {error.endpoint}</span></div>
          {error.user_id && <div><span className="text-muted-foreground">User:</span> <span className="text-foreground">{error.user_id}</span></div>}
          {error.request_id && <div><span className="text-muted-foreground">Request ID:</span> <span className="text-foreground">{error.request_id}</span></div>}

          <div>
            <span className="text-muted-foreground block mb-1">Message:</span>
            <div className="p-3 bg-background border border-border text-destructive break-all">{error.error_message}</div>
          </div>

          {error.request_body && (
            <div>
              <span className="text-muted-foreground block mb-1">Request Body (sanitized):</span>
              <pre className="p-3 bg-background border border-border text-foreground whitespace-pre-wrap break-all max-h-32 overflow-auto">
                {JSON.stringify(error.request_body, null, 2)}
              </pre>
            </div>
          )}

          {error.stack_trace && (
            <div>
              <span className="text-muted-foreground block mb-1">Stack Trace:</span>
              <pre className="p-3 bg-background border border-border text-muted-foreground whitespace-pre-wrap break-all max-h-48 overflow-auto text-[10px]">
                {error.stack_trace}
              </pre>
            </div>
          )}

          {error.resolve_note && (
            <div>
              <span className="text-muted-foreground block mb-1">Resolution Note:</span>
              <div className="p-3 bg-green-500/5 border border-green-500/20 text-green-400">{error.resolve_note}</div>
            </div>
          )}

          {!error.resolved && (
            <div className="pt-3 border-t border-border">
              <label className="text-[10px] text-muted-foreground block mb-1 uppercase">Resolve with note</label>
              <div className="flex gap-2">
                <Input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Resolution notes..." className="font-mono text-xs" data-testid="resolve-note-input" />
                <Button size="sm" onClick={handleResolve} disabled={resolving} className="font-mono text-xs uppercase gap-1" data-testid="resolve-error-btn">
                  {resolving ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                  Resolve
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────────────
export default function AdminDiagnostics() {
  const api = useApi();
  const [tab, setTab] = useState("errors");
  const [summary, setSummary] = useState(null);
  const [errors, setErrors] = useState([]);
  const [errorTotal, setErrorTotal] = useState(0);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedError, setSelectedError] = useState(null);

  // Filters
  const [filters, setFilters] = useState({ severity: "all", source: "all", resolved: "all", page: 1 });

  // Use refs to avoid infinite loops from useCallback dependencies
  const apiRef = useRef(api);
  apiRef.current = api;

  const fetchSummary = useCallback(async () => {
    try {
      const res = await apiRef.current.get("/admin/diagnostics/summary");
      setSummary(res.data);
    } catch (err) {
      toast.error(extractApiError(err, "Failed to load summary"));
    }
  }, []);

  const fetchErrors = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      params.set("page", filters.page);
      params.set("limit", "20");
      if (filters.severity !== "all") params.set("severity", filters.severity);
      if (filters.source !== "all") params.set("source", filters.source);
      if (filters.resolved !== "all") params.set("resolved", filters.resolved === "true" ? "true" : "false");
      const res = await apiRef.current.get(`/admin/diagnostics/errors?${params}`);
      setErrors(res.data.errors);
      setErrorTotal(res.data.total);
    } catch (err) {
      toast.error(extractApiError(err, "Failed to load errors"));
    }
  }, [filters]);

  const fetchPerformance = useCallback(async () => {
    try {
      const res = await apiRef.current.get("/admin/diagnostics/performance");
      setPerformance(res.data);
    } catch (err) {
      toast.error(extractApiError(err, "Failed to load performance data"));
    }
  }, []);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      await Promise.all([fetchSummary(), fetchErrors(), fetchPerformance()]);
    } finally {
      setLoading(false);
    }
  }, [fetchSummary, fetchErrors, fetchPerformance]);

  // Load data on mount only
  useEffect(() => { loadAll(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  
  // Refetch errors when filters change
  useEffect(() => { 
    if (!loading) fetchErrors(); 
  }, [filters]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleResolve = async (errorId, note) => {
    try {
      await api.put(`/admin/diagnostics/errors/${errorId}/resolve`, { note });
      toast.success("Error marked as resolved");
      setSelectedError(null);
      fetchErrors();
      fetchSummary();
    } catch (err) {
      toast.error(extractApiError(err, "Failed to resolve"));
    }
  };

  const handleErrorClick = async (errorId) => {
    try {
      const res = await api.get(`/admin/diagnostics/errors/${errorId}`);
      setSelectedError(res.data);
    } catch (err) {
      toast.error(extractApiError(err, "Failed to load error detail"));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  const s = summary || {};
  const s24 = s.last_24h || {};

  return (
    <div className="space-y-6" data-testid="admin-diagnostics-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-mono font-bold text-foreground">Diagnostics</h1>
          <p className="text-xs text-muted-foreground font-mono">System health, errors, and performance</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadAll} className="font-mono text-xs gap-1" data-testid="refresh-diagnostics">
          <RefreshCw className="w-3 h-3" /> Refresh
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Errors (24h)" value={s24.total || 0} icon={AlertTriangle} color="text-destructive" testId="stat-errors-24h" />
        <StatCard label="Critical" value={s24.critical || 0} icon={Zap} color="text-red-400" testId="stat-critical" />
        <StatCard label="Affected Users" value={s.affected_users_24h || 0} icon={Users} color="text-amber-400" testId="stat-affected-users" />
        <StatCard label="Avg Response" value={`${s.avg_response_time_ms || 0}ms`} icon={Clock} color="text-primary" testId="stat-avg-response" />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {["errors", "performance"].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-xs font-mono uppercase tracking-wider border-b-2 transition-colors ${
              tab === t ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
            data-testid={`tab-${t}`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Error rate chart */}
      {tab === "errors" && (
        <>
          {(s.error_rate_per_hour || []).length > 0 && (
            <Card className="border-border bg-card">
              <CardContent className="p-5">
                <h3 className="text-xs font-mono text-muted-foreground uppercase mb-3">Error Rate (Hourly, Last 24h)</h3>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={s.error_rate_per_hour}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2e" />
                      <XAxis dataKey="hour" tick={{ fontSize: 10, fill: "#666" }} />
                      <YAxis tick={{ fontSize: 10, fill: "#666" }} allowDecimals={false} />
                      <Tooltip contentStyle={{ background: "#1a1a1e", border: "1px solid #2a2a2e", fontSize: 11, fontFamily: "monospace" }} />
                      <Bar dataKey="count" fill="#ef4444" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Filters */}
          <div className="flex flex-wrap gap-2 items-center">
            <Select value={filters.severity} onValueChange={(v) => setFilters((p) => ({ ...p, severity: v, page: 1 }))}>
              <SelectTrigger className="w-32 font-mono text-xs" data-testid="filter-severity"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Severity</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filters.source} onValueChange={(v) => setFilters((p) => ({ ...p, source: v, page: 1 }))}>
              <SelectTrigger className="w-32 font-mono text-xs" data-testid="filter-source"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Sources</SelectItem>
                <SelectItem value="backend">Backend</SelectItem>
                <SelectItem value="frontend">Frontend</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filters.resolved} onValueChange={(v) => setFilters((p) => ({ ...p, resolved: v, page: 1 }))}>
              <SelectTrigger className="w-32 font-mono text-xs" data-testid="filter-resolved"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="false">Open</SelectItem>
                <SelectItem value="true">Resolved</SelectItem>
              </SelectContent>
            </Select>
            <span className="text-[10px] text-muted-foreground font-mono ml-auto">{errorTotal} error(s)</span>
          </div>

          {/* Errors table */}
          <Card className="border-border bg-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono" data-testid="errors-table">
                <thead>
                  <tr className="border-b border-border text-[10px] text-muted-foreground uppercase">
                    <th className="p-3 text-left">Time</th>
                    <th className="p-3 text-left">Severity</th>
                    <th className="p-3 text-left">Source</th>
                    <th className="p-3 text-left">Type</th>
                    <th className="p-3 text-left">Endpoint</th>
                    <th className="p-3 text-left">User</th>
                    <th className="p-3 text-left">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {errors.map((e) => (
                    <tr
                      key={e.error_id}
                      className="border-b border-border/50 hover:bg-secondary/30 cursor-pointer transition-colors"
                      onClick={() => handleErrorClick(e.error_id)}
                      data-testid={`error-row-${e.error_id}`}
                    >
                      <td className="p-3 text-muted-foreground whitespace-nowrap">{new Date(e.timestamp).toLocaleString()}</td>
                      <td className="p-3"><SeverityBadge severity={e.severity} /></td>
                      <td className="p-3 text-muted-foreground">{e.source}</td>
                      <td className="p-3 text-foreground">{e.error_type}</td>
                      <td className="p-3 text-muted-foreground truncate max-w-[200px]">{e.endpoint}</td>
                      <td className="p-3 text-muted-foreground truncate max-w-[120px]">{e.user_id || "—"}</td>
                      <td className="p-3">
                        {e.resolved
                          ? <span className="text-green-400">Resolved</span>
                          : <span className="text-amber-400">Open</span>}
                      </td>
                    </tr>
                  ))}
                  {errors.length === 0 && (
                    <tr><td colSpan={7} className="p-8 text-center text-muted-foreground">No errors found</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Pagination */}
          {errorTotal > 20 && (
            <div className="flex items-center justify-center gap-2">
              <Button variant="outline" size="sm" disabled={filters.page <= 1} onClick={() => setFilters((p) => ({ ...p, page: p.page - 1 }))} className="font-mono text-xs">
                Prev
              </Button>
              <span className="text-xs font-mono text-muted-foreground">Page {filters.page} of {Math.ceil(errorTotal / 20)}</span>
              <Button variant="outline" size="sm" disabled={filters.page >= Math.ceil(errorTotal / 20)} onClick={() => setFilters((p) => ({ ...p, page: p.page + 1 }))} className="font-mono text-xs">
                Next
              </Button>
            </div>
          )}
        </>
      )}

      {/* Performance tab */}
      {tab === "performance" && performance && (
        <div className="space-y-4">
          {/* Slowest endpoints */}
          <Card className="border-border bg-card">
            <CardContent className="p-5">
              <h3 className="text-xs font-mono text-muted-foreground uppercase mb-3">Slowest Endpoints (Avg, 24h)</h3>
              {(performance.avg_by_endpoint || []).length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-mono" data-testid="perf-endpoints-table">
                    <thead>
                      <tr className="border-b border-border text-[10px] text-muted-foreground uppercase">
                        <th className="p-2 text-left">Endpoint</th>
                        <th className="p-2 text-left">Method</th>
                        <th className="p-2 text-right">Avg (ms)</th>
                        <th className="p-2 text-right">Max (ms)</th>
                        <th className="p-2 text-right">Calls</th>
                      </tr>
                    </thead>
                    <tbody>
                      {performance.avg_by_endpoint.slice(0, 15).map((r, i) => (
                        <tr key={i} className="border-b border-border/50">
                          <td className="p-2 text-foreground truncate max-w-[250px]">{r.endpoint}</td>
                          <td className="p-2 text-muted-foreground">{r.method}</td>
                          <td className={`p-2 text-right tabular-nums ${r.avg_ms > 3000 ? "text-red-400" : r.avg_ms > 1000 ? "text-amber-400" : "text-foreground"}`}>{r.avg_ms}</td>
                          <td className="p-2 text-right tabular-nums text-muted-foreground">{r.max_ms}</td>
                          <td className="p-2 text-right tabular-nums text-muted-foreground">{r.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground font-mono text-center py-4">No slow requests recorded in the last 24h</p>
              )}
            </CardContent>
          </Card>

          {/* P95 response times */}
          {(performance.p95_by_endpoint || []).length > 0 && (
            <Card className="border-border bg-card">
              <CardContent className="p-5">
                <h3 className="text-xs font-mono text-muted-foreground uppercase mb-3">P95 Response Times</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-mono" data-testid="perf-p95-table">
                    <thead>
                      <tr className="border-b border-border text-[10px] text-muted-foreground uppercase">
                        <th className="p-2 text-left">Endpoint</th>
                        <th className="p-2 text-right">P95 (ms)</th>
                        <th className="p-2 text-right">Samples</th>
                      </tr>
                    </thead>
                    <tbody>
                      {performance.p95_by_endpoint.slice(0, 10).map((r, i) => (
                        <tr key={i} className="border-b border-border/50">
                          <td className="p-2 text-foreground truncate max-w-[300px]">{r.endpoint}</td>
                          <td className={`p-2 text-right tabular-nums ${r.p95_ms > 3000 ? "text-red-400" : "text-foreground"}`}>{r.p95_ms}</td>
                          <td className="p-2 text-right tabular-nums text-muted-foreground">{r.sample_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Recent slow requests */}
          {(performance.slowest_requests || []).length > 0 && (
            <Card className="border-border bg-card">
              <CardContent className="p-5">
                <h3 className="text-xs font-mono text-muted-foreground uppercase mb-3">Recent Slow Requests</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-mono" data-testid="perf-slow-table">
                    <thead>
                      <tr className="border-b border-border text-[10px] text-muted-foreground uppercase">
                        <th className="p-2 text-left">Time</th>
                        <th className="p-2 text-left">Method</th>
                        <th className="p-2 text-left">Endpoint</th>
                        <th className="p-2 text-right">Duration (ms)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {performance.slowest_requests.map((r, i) => (
                        <tr key={i} className="border-b border-border/50">
                          <td className="p-2 text-muted-foreground whitespace-nowrap">{r.timestamp ? new Date(r.timestamp).toLocaleString() : "—"}</td>
                          <td className="p-2 text-muted-foreground">{r.method}</td>
                          <td className="p-2 text-foreground truncate max-w-[250px]">{r.endpoint}</td>
                          <td className="p-2 text-right tabular-nums text-red-400 font-bold">{r.duration_ms}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Error detail modal */}
      <ErrorDetailModal error={selectedError} onClose={() => setSelectedError(null)} onResolve={handleResolve} />
    </div>
  );
}
